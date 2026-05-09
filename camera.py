"""
camera.py — USB webcam capture via OpenCV.

Opens the webcam and provides frames for object detection.
Optimized for low resolution to maintain reasonable FPS on RPi.

Run target: Raspberry Pi / Thonny
"""

import cv2
import config


class Camera:
    """
    Simple OpenCV webcam wrapper.

    Usage:
        cam = Camera()
        cam.start()
        frame = cam.get_frame()
        cam.stop()
    """

    def __init__(self, index=None, width=None, height=None):
        self.index = index if index is not None else config.CAMERA_INDEX
        self.width = width or config.CAMERA_WIDTH
        self.height = height or config.CAMERA_HEIGHT
        self.fps = config.CAMERA_FPS
        self.cap = None

    def start(self):
        """Open the webcam."""
        self.cap = cv2.VideoCapture(self.index)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"[camera] Cannot open camera at index {self.index}. "
                "Check that the webcam is connected and /dev/video0 exists."
            )

        # Set resolution and FPS
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Read actual values (camera may not support requested)
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"[camera] Opened camera {self.index}: "
              f"{actual_w}x{actual_h} @ {actual_fps:.0f} FPS")

    def get_frame(self):
        """
        Capture a single frame from the webcam.

        Returns:
            numpy.ndarray: BGR image, or None if capture failed.
        """
        if self.cap is None or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret:
            return None

        return frame

    def stop(self):
        """Release the webcam."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            print("[camera] Released")

    def is_opened(self):
        """Check if the camera is currently open."""
        return self.cap is not None and self.cap.isOpened()


# ──────────────────────────────────────────────
#  Quick test (run this file directly in Thonny)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    cam = Camera()
    cam.start()

    print("Showing webcam feed... Press 'q' to quit.")
    try:
        while True:
            frame = cam.get_frame()
            if frame is None:
                print("[camera] Failed to capture frame")
                break

            cv2.imshow("Camera Test", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        cam.stop()
        cv2.destroyAllWindows()
