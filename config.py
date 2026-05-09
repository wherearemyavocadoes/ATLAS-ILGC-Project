"""
config.py — Central configuration for the ILGC Assistive Navigation System.

All hardware pins, model paths, thresholds, and tuning parameters
are defined here. Edit this file to match your specific hardware setup.

Run target: Raspberry Pi / Thonny
"""

# ──────────────────────────────────────────────
#  GPIO Pin Assignments (BCM numbering)
# ──────────────────────────────────────────────
BUZZER_PIN = 13          # PWM-capable pin for the active buzzer
US_TRIG_PIN = 23         # HC-SR04 trigger
US_ECHO_PIN = 24         # HC-SR04 echo

# ──────────────────────────────────────────────
#  Camera Settings
# ──────────────────────────────────────────────
CAMERA_INDEX = 0         # /dev/video0 — USB webcam
CAMERA_WIDTH = 320       # Low res for faster processing on RPi
CAMERA_HEIGHT = 240
CAMERA_FPS = 15          # Requested FPS (actual will depend on CPU load)

# ──────────────────────────────────────────────
#  Object Detection — MobileNet-SSD (Caffe)
# ──────────────────────────────────────────────
MODEL_DIR = "models"
PROTOTXT_PATH = MODEL_DIR + "/deploy.prototxt"
CAFFEMODEL_PATH = MODEL_DIR + "/mobilenet_iter_73000.caffemodel"

# Minimum confidence to report a detection (0.0–1.0)
DETECTION_CONFIDENCE = 0.55

# PASCAL VOC class labels in order (index 0 = background)
CLASS_LABELS = [
    "background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair",
    "cow", "diningtable", "dog", "horse", "motorbike",
    "person", "pottedplant", "sheep", "sofa", "train",
    "tvmonitor"
]

# Only announce these classes (relevant to navigation).
# This filters out false positives like cat/dog/bird/sheep
# when the model misclassifies unknown objects.
NAVIGATION_CLASSES = {
    "person", "bicycle", "car", "bus", "motorbike",
    "bottle", "chair", "diningtable", "sofa",
    "tvmonitor", "pottedplant", "train", "boat"
}

# ──────────────────────────────────────────────
#  Kalman Filter Parameters
# ──────────────────────────────────────────────
KALMAN_PROCESS_NOISE = 0.05      # Q — how much we expect distance to change
KALMAN_MEASUREMENT_NOISE = 5.0   # R — HC-SR04 measurement variance (cm²)
KALMAN_INITIAL_ESTIMATE = 100.0  # Starting distance estimate (cm)
KALMAN_INITIAL_ERROR = 50.0      # Starting error covariance
KALMAN_OUTLIER_THRESHOLD = 80.0  # Reject readings that jump more than this (cm)

# ──────────────────────────────────────────────
#  Ultrasonic Sensor Settings
# ──────────────────────────────────────────────
US_MAX_DISTANCE = 400.0    # Max range in cm (HC-SR04 spec)
US_TIMEOUT = 0.04          # Timeout for echo (seconds) — ~4m round-trip at 343m/s
US_READ_INTERVAL = 0.05    # Seconds between readings (20 Hz)

# ──────────────────────────────────────────────
#  Buzzer Alert Distance Tiers (cm)
# ──────────────────────────────────────────────
BUZZER_TIER_OFF = 150       # > 150 cm: no buzzing
BUZZER_TIER_SLOW = 100      # 100–150 cm: slow pulse (1 Hz)
BUZZER_TIER_MEDIUM = 50     # 50–100 cm: medium pulse (3 Hz)
BUZZER_TIER_FAST = 20       # 20–50 cm: fast pulse (5 Hz)
                            # < 20 cm: continuous buzz

# ──────────────────────────────────────────────
#  TTS / Speaker Settings
# ──────────────────────────────────────────────
TTS_RATE = 160              # Words per minute
TTS_VOLUME = 1.0            # 0.0 – 1.0

# ──────────────────────────────────────────────
#  Caption Settings
# ──────────────────────────────────────────────
CAPTION_COOLDOWN = 3.0      # Seconds before repeating the same caption
CAPTION_CLOSE_THRESHOLD = 50    # cm — triggers "Warning!" prefix
CAPTION_VERY_CLOSE = 20         # cm — triggers urgent alert

# ──────────────────────────────────────────────
#  Display (set False for headless / production)
# ──────────────────────────────────────────────
SHOW_DISPLAY = True         # Show OpenCV window (useful for debugging in Thonny)

# ──────────────────────────────────────────────
#  Main Loop
# ──────────────────────────────────────────────
MAIN_LOOP_DELAY = 0.1       # Seconds between main loop iterations
