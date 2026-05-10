"""
main.py — ILGC Assistive Navigation System (Iteration 1)

Main orchestration loop for the assistive navigation system.
Ties together all pipeline stages:

    Camera -> Detection -> Ultrasonic -> Kalman Filter
           -> Caption -> TTS Speaker
           -> Buzzer (proximity alerts)

Run this in Thonny on the Raspberry Pi.

Prerequisites:
    1. Run 'python3 download_model.py' first to get model files
    2. Install deps: pip install opencv-python pyttsx3 numpy
    3. Connect hardware: webcam, HC-SR04 (TRIG=23, ECHO=24),
       buzzer (GPIO 13), speaker (3.5mm or USB)

Usage:
    Press the Run button in Thonny, or:
    python3 main.py

    Press 'q' in the display window or Ctrl+C to quit.

Run target: Raspberry Pi / Thonny
"""

import os
import sys
import time

# Fix Qt/Wayland display errors on RPi
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"

import cv2

# Import pipeline modules
import config
from camera import Camera
from ultrasonic import UltrasonicSensor
from detector import ObjectDetector
from kalman_filter import KalmanFilter1D
from caption import CaptionGenerator
from speaker import Speaker
from buzzer import Buzzer

# For GPIO cleanup
try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False


def print_banner():
    """Print startup banner."""
    print()
    print("=" * 55)
    print("  ILGC Assistive Navigation System")
    print("  Intelligent Indoor/Outdoor Navigation for BLV")
    print("=" * 55)
    print()
    print("  Hardware:")
    print(f"    Camera:     index {config.CAMERA_INDEX}")
    print(f"    Ultrasonic: TRIG={config.US_TRIG_PIN}, "
          f"ECHO={config.US_ECHO_PIN}")
    print(f"    Buzzer:     GPIO {config.BUZZER_PIN}")
    print(f"    Display:    {'ON' if config.SHOW_DISPLAY else 'OFF'}")
    print()


def main():
    """Main pipeline loop."""
    print_banner()

    # ── Initialize all components ──
    print("[main] Initializing components...")

    cam = Camera()
    us = UltrasonicSensor()
    det = ObjectDetector()
    kf = KalmanFilter1D()
    cap = CaptionGenerator()
    spk = Speaker()
    bz = Buzzer()

    try:
        # Load the detection model (takes a few seconds)
        det.load_model()

        # Start hardware interfaces
        cam.start()
        us.start()
        spk.start()
        bz.start()

        print()
        print("[main] All systems ready!")
        print("[main] Press 'q' in display window or "
              "Ctrl+C to stop")
        print("-" * 55)
        print()

        # Announce system ready
        spk.speak("Navigation system ready")

        # ── Main loop ──
        frame_count = 0
        loop_start = time.time()

        while True:
            iter_start = time.time()

            # 1. Read ultrasonic distance and filter it
            raw_dist = us.get_distance()
            filtered_dist = kf.update(raw_dist)
            velocity = kf.get_velocity()

            # 2. Update buzzer with filtered distance
            bz.update(filtered_dist)

            # 3. Capture a camera frame
            frame = cam.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            # 4. Run object detection
            detections = det.detect(frame)

            # 5. Generate caption
            caption_text = cap.generate(detections, filtered_dist)

            # 5b. If no detection but something is close,
            #     generate proximity-only warning
            if caption_text is None and not detections:
                caption_text = cap.generate_proximity_warning(
                    filtered_dist
                )

            # 6. Print caption to console
            if caption_text:
                spk.speak(caption_text)

            # 7. Display (optional, for debugging)
            if config.SHOW_DISPLAY:
                annotated = det.annotate_frame(
                    frame.copy(), detections, filtered_dist
                )

                # Add status bar
                fps = frame_count / max(
                    0.001, time.time() - loop_start
                )
                vel_str = f"vel={velocity:+.0f}cm/s"
                status = (f"FPS:{fps:.1f} | "
                         f"Raw:{raw_dist:.0f}cm | "
                         f"Filt:{filtered_dist:.0f}cm | "
                         f"{vel_str}")
                cv2.putText(
                    annotated, status,
                    (10, annotated.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (200, 200, 200), 1
                )

                cv2.imshow("ILGC Navigation", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n[main] Quit requested")
                    break

            frame_count += 1

            # Small delay to control loop rate
            elapsed = time.time() - iter_start
            remaining = config.MAIN_LOOP_DELAY - elapsed
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("\n[main] Interrupted by user")

    except Exception as e:
        print(f"\n[main] ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # ── Cleanup ──
        print()
        print("[main] Shutting down...")
        spk.speak("Navigation system stopping")
        time.sleep(1)

        bz.cleanup()
        us.cleanup()
        cam.stop()
        spk.stop()

        if config.SHOW_DISPLAY:
            cv2.destroyAllWindows()

        if RPI_AVAILABLE:
            GPIO.cleanup()

        print("[main] Goodbye!")


if __name__ == "__main__":
    main()
