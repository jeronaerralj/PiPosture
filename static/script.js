const exerciseData = {
    "side_bend": {
        title: "Standing Side Bend",
        img: "/static/images/side_bend.jpg",
        bot: "Keep shoulders aligned! Stand upright with feet shoulder-width apart. Slide hand down leg."
    },
    "high_knees": {
        title: "High Knees",
        img: "/static/images/high_knees.jpg",
        bot: "Drive that knee up! March in place, lifting knees to hip level."
    },
    "cross_crunch": {
        title: "Cross Body Crunch",
        img: "/static/images/cross_crunch.jpg",
        bot: "Twist your torso! Lift knee and touch with opposite elbow."
    },
    "good_morning": {
        title: "Good Morning",
        img: "/static/images/good_morning.jpg",
        bot: "Keep back straight! Hinge at hips, keep back flat."
    },
    "overhead_reach": {
        title: "Overhead Reach",
        img: "/static/images/overhead_reach.jpg",
        bot: "Reach for the sky! Reach arms directly overhead."
    },
    "None": {
        title: "System Idle",
        img: "",
        bot: "Select an exercise to begin."
    }
};

let cameraActive = false;
let animationId = null;
let isProcessing = false;

// Voice Feedback Variables
let voiceActive = true;
let lastSpokenText = "";
let lastSpokenTime = 0;
const SPEECH_COOLDOWN = 10000;

// Elements
const video = document.getElementById('webcam-video');
const canvas = document.getElementById('webcam-canvas');
const context = canvas.getContext('2d');
const processedImg = document.getElementById('processed-feed');

// Toggle Camera
function toggleCamera() {
    const toggle = document.getElementById('cam-toggle');
    const statusText = document.getElementById('sys-status');

    if (toggle.checked) {
        startCamera();
        statusText.innerText = "ONLINE";
        statusText.style.color = "#00ff88";
    } else {
        stopCamera();
        statusText.innerText = "OFFLINE";
        statusText.style.color = "#555";
    }
}

// Start Webcam
function startCamera() {
    const constraints = {
        video: { width: { ideal: 640 }, height: { ideal: 480 } }
    };

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia(constraints)
            .then(function (stream) {
                video.srcObject = stream;
                video.play();
                cameraActive = true;
                isProcessing = false;

                // Start Loop
                requestAnimationFrame(sendFrame);
            })
            .catch(function (error) {
                console.error("Camera Error:", error);
                alert("Could not access camera. Please allow permissions.");
            });
    }
}

// Stop Webcam
function stopCamera() {
    cameraActive = false;
    if (animationId) cancelAnimationFrame(animationId);

    const stream = video.srcObject;
    if (stream) {
        const tracks = stream.getTracks();
        tracks.forEach(track => track.stop());
    }
    video.srcObject = null;
    processedImg.removeAttribute("src");

    document.getElementById('feedback-message').innerText = "System Paused";
    document.getElementById('feedback-message').style.color = "white";

    window.speechSynthesis.cancel();
}

// Send Frame
function sendFrame() {
    if (!cameraActive) return;
    if (isProcessing) {
        animationId = requestAnimationFrame(sendFrame);
        return;
    }

    isProcessing = true;
    canvas.width = 640;
    canvas.height = 480;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataURL = canvas.toDataURL('image/jpeg', 0.5);

    fetch('/process_frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: dataURL })
    })
        .then(response => response.json())
        .then(data => {
            if (!cameraActive) return;

            processedImg.src = "data:image/jpeg;base64," + data.image;
            document.getElementById('rep-count').innerText = data.counter;

            const feedbackBox = document.getElementById('feedback-message');
            feedbackBox.innerText = data.feedback;
            feedbackBox.style.color = data.color;
            feedbackBox.style.borderColor = data.color;

            speakFeedback(data.feedback);
            isProcessing = false;
            animationId = requestAnimationFrame(sendFrame);
        })
        .catch(err => {
            console.error("Error:", err);
            isProcessing = false;
            if (cameraActive) {
                setTimeout(() => { animationId = requestAnimationFrame(sendFrame); }, 500);
            }
        });
}

// Intelligent Voice Feedback Function
function speakFeedback(text) {
    // Safety checks
    if (!voiceActive || !text || text.trim() === "") return;

    const now = Date.now();
    if (text !== lastSpokenText || (now - lastSpokenTime > SPEECH_COOLDOWN)) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
        lastSpokenText = text;
        lastSpokenTime = now;
    }
}

// Select Exercise
function selectExercise(exerciseName) {
    if (exerciseName === 'None') {

        // Force Camera Off
        const camToggle = document.getElementById('cam-toggle');
        if (camToggle.checked) {
            camToggle.checked = false;
            stopCamera();

            const statusText = document.getElementById('sys-status');
            statusText.innerText = "OFFLINE";
            statusText.style.color = "#555";
        }

        // Force Voice Off
        const voiceToggle = document.getElementById('voice-toggle');
        if (voiceToggle.checked) {
            voiceToggle.checked = false;
            toggleVoice();
        }
    }

    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => btn.classList.remove('active'));

    buttons.forEach(btn => {
        if (btn.getAttribute('onclick').includes(exerciseName)) {
            btn.classList.add('active');
        }
    });

    const data = exerciseData[exerciseName] || exerciseData["None"];
    document.getElementById('guide-title').innerText = data.title;
    document.getElementById('bot-speech').innerText = data.bot;

    const imgElement = document.getElementById('guide-image');
    if (data.img) {
        imgElement.src = data.img;
        imgElement.style.display = "block";
    } else {
        imgElement.style.display = "none";
    }

    // Reset Voice History when switching exercises
    lastSpokenText = "";

    fetch(`/set_exercise/${exerciseName}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('rep-count').innerText = "0";
        });
}

function toggleVoice() {
    const toggle = document.getElementById('voice-toggle');
    const statusText = document.getElementById('voice-status');

    // Update global variable
    voiceActive = toggle.checked;

    if (voiceActive) {
        statusText.innerText = "Voice ON";
    } else {
        statusText.innerText = "Voice Muted";
        window.speechSynthesis.cancel();
    }
}