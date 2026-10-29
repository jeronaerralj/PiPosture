import cv2
import mediapipe as mp
import numpy as np
import math
import base64
from flask import Flask, render_template, Response, request, jsonify

app = Flask(__name__)

# Configuration
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.75, min_tracking_confidence=0.75)

# Global Variables
current_exercise = "None"
counter = 0
stage = None 
feedback = "Waiting for input..."
feedback_color = (255, 255, 255) 

# Math Logic
def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    if angle > 180.0: angle = 360-angle
    return angle

def analyze_posture(landmarks, exercise_name):
    global counter, stage
    
    # Get coordinates
    shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
    elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
    wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
    hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
    knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
    ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
    
    # Default status
    status = "Get Ready"
    color = (255, 255, 0)

    # Logic for exercises
    if exercise_name == "side_bend":
        angle = calculate_angle(shoulder, hip, knee)
        if angle > 170:
            status = "Bend Sideways"
            stage = "up"
        elif angle > 160:
            status = "Bend More..."
        if angle < 160 and stage == "up":
            stage = "down"
            counter += 1
            status = "Perfect!"
            color = (0, 255, 0)
        elif angle < 140:
            status = "Too Deep!"
            color = (0, 0, 255)

    elif exercise_name == "high_knees":
        hip_angle = calculate_angle(shoulder, hip, knee)
        if hip_angle > 160:
            status = "Lift Knee"
            stage = "down"
        elif hip_angle > 100:
            status = "Higher!"
        if hip_angle < 100 and stage == "down":
            stage = "up"
            counter += 1
            status = "Perfect!"
            color = (0, 255, 0)

    elif exercise_name == "cross_crunch":
        dist = math.dist(elbow, knee) 
        if dist > 0.3:
            status = "Crunch In"
            stage = "out"
        elif dist > 0.15:
            status = "Closer..."
        if dist < 0.15 and stage == "out":
            stage = "in"
            counter += 1
            status = "Perfect!"
            color = (0, 255, 0)

    elif exercise_name == "good_morning":
        angle = calculate_angle(shoulder, hip, knee)
        if angle > 160:
            status = "Hinge Forward"
            stage = "up"
        elif angle > 120:
            status = "Lower Hips..."
        if angle < 120 and angle > 90 and stage == "up":
            status = "Perfect!"
            color = (0, 255, 0)
            if angle < 100:
                stage = "down"
                counter += 1
        elif angle < 80:
            status = "Back Warning!"
            color = (0, 0, 255)

    elif exercise_name == "overhead_reach":
        angle = calculate_angle(hip, shoulder, elbow)
        if angle < 150:
            status = "Reach Up"
            stage = "down"
        elif angle < 170:
            status = "Straighten Arms..."
        if angle > 170 and stage == "down":
            stage = "up"
            counter += 1
            status = "Perfect!"
            color = (0, 255, 0)

    return status, color

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_frame', methods=['POST'])
def process_frame():
    global current_exercise, feedback, feedback_color
    
    data = request.json['image']
    header, encoded = data.split(",", 1)
    nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)
    
    draw_color = (255, 255, 255) 

    valid_detection = False
    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        left_shoulder_vis = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].visibility
        left_hip_vis = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].visibility
        
        nose_y = landmarks[mp_pose.PoseLandmark.NOSE.value].y
        ankle_y = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y
        person_height = abs(ankle_y - nose_y)
        if left_shoulder_vis > 0.6 and left_hip_vis > 0.6 and person_height > 0.2:
            valid_detection = True
        
        
    if valid_detection:
        if current_exercise != "None":
            try:
                landmarks = results.pose_landmarks.landmark
                status_text, color = analyze_posture(landmarks, current_exercise)
                
                feedback = status_text
                feedback_color = color
                draw_color = color
            except Exception as e:
                print(f"Error in analysis: {e}")
                pass

        mp_drawing.draw_landmarks(
            image, 
            results.pose_landmarks, 
            mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=4, circle_radius=3),
            mp_drawing.DrawingSpec(color=draw_color, thickness=3, circle_radius=2)
        )
    else:
        if current_exercise != "None":
            feedback = "Align Body in Frame"
            feedback_color = (200, 200, 200)
    
    _, buffer = cv2.imencode('.jpg', image)
    processed_image_b64 = base64.b64encode(buffer).decode('utf-8')
    
    css_color = f"rgb({feedback_color[2]}, {feedback_color[1]}, {feedback_color[0]})"
    
    return jsonify({
        "image": processed_image_b64,
        "feedback": feedback,
        "counter": counter,
        "color": css_color
    })

@app.route('/set_exercise/<name>')
def set_exercise(name):
    global current_exercise, counter, stage
    current_exercise = name
    counter = 0 
    stage = None
    return jsonify({"status": "success", "exercise": name})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')