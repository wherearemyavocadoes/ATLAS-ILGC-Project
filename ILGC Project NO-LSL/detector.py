"""
detector.py — Object detection using MobileNet-SSD via OpenCV DNN.

Loads a pre-trained MobileNet-SSD Caffe model and runs inference
on camera frames. Returns detected objects with class names,
confidence scores, and bounding boxes.

The model detects 20 PASCAL VOC classes including: person, car,
bicycle, chair, bottle, sofa, tvmonitor — sufficient for
indoor/outdoor navigation.

Run target: Raspberry Pi / Thonny
"""

import os
import cv2
import numpy as np
import config


class ObjectDetector:
    """
    MobileNet-SSD object detector using OpenCV's DNN module.

    Optimized for RPi: uses the lightweight Caffe model (~23 MB)
    and runs inference at ~2-3 FPS on 320x240 frames.
    """

    def __init__(self):
        self.confidence_threshold = config.DETECTION_CONFIDENCE
        self.class_labels = config.CLASS_LABELS
        self.net = None

    def load_model(self):
        """
        Load the MobileNet-SSD model from disk.

        Raises RuntimeError if model files are missing.
        """
        prototxt = config.PROTOTXT_PATH
        caffemodel = config.CAFFEMODEL_PATH

        if not os.path.exists(prototxt):
            raise RuntimeError(
                f"[detector] Model file not found: {prototxt}\n"
                "Run 'python3 download_model.py' first to download the model."
            )

        if not os.path.exists(caffemodel):
            raise RuntimeError(
                f"[detector] Model file not found: {caffemodel}\n"
                "Run 'python3 download_model.py' first to download the model."
            )

        print("[detector] Loading MobileNet-SSD model...")
        self.net = cv2.dnn.readNetFromCaffe(prototxt, caffemodel)

        # Use the default CPU backend (best for RPi)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        print("[detector] Model loaded successfully")

    def detect(self, frame):
        """
        Run object detection on a single frame.

        Args:
            frame (numpy.ndarray): BGR image from the camera.

        Returns:
            list of dict: Each detection has:
                - 'label' (str): class name, e.g. "bottle"
                - 'confidence' (float): 0.0–1.0
                - 'box' (tuple): (x1, y1, x2, y2) pixel coordinates
        """
        if self.net is None:
            return []

        h, w = frame.shape[:2]

        # Create a blob from the frame
        # MobileNet-SSD expects 300x300, mean subtraction (127.5), scale 1/127.5
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=0.007843,       # 1/127.5
            size=(300, 300),
            mean=(127.5, 127.5, 127.5),
            swapRB=False,
            crop=False
        )

        self.net.setInput(blob)
        detections = self.net.forward()

        results = []

        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])

            if confidence < self.confidence_threshold:
                continue

            class_id = int(detections[0, 0, i, 1])

            # Skip background class and out-of-range IDs
            if class_id <= 0 or class_id >= len(self.class_labels):
                continue

            label = self.class_labels[class_id]

            # Skip classes not relevant to navigation
            # (reduces false cat/dog/bird detections)
            if hasattr(config, 'NAVIGATION_CLASSES'):
                if label not in config.NAVIGATION_CLASSES:
                    continue

            # Scale bounding box to frame dimensions
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            x1, y1, x2, y2 = box.astype(int)

            # Clamp to frame bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            results.append({
                'label': label,
                'confidence': confidence,
                'box': (x1, y1, x2, y2)
            })

        # Sort by confidence (highest first)
        results.sort(key=lambda d: d['confidence'], reverse=True)

        return results

    def annotate_frame(self, frame, detections, distance=None):
        """
        Draw detection boxes and labels on the frame (for debugging).

        Args:
            frame: BGR image (will be modified in-place).
            detections: List of detection dicts from detect().
            distance: Optional filtered distance to display.

        Returns:
            The annotated frame.
        """
        for det in detections:
            x1, y1, x2, y2 = det['box']
            label = det['label']
            conf = det['confidence']

            # Draw bounding box
            color = (0, 255, 0)  # Green
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw label with confidence
            text = f"{label}: {conf:.0%}"
            if distance is not None:
                text += f" | {distance:.0f}cm"

            # Background for text
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, text, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # Draw distance bar at the top
        if distance is not None:
            dist_text = f"Distance: {distance:.0f} cm"
            cv2.putText(frame, dist_text, (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        return frame


# ──────────────────────────────────────────────
#  Quick test (run this file directly in Thonny)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("Object Detector Test")
    print("-" * 40)

    det = ObjectDetector()
    det.load_model()

    # Try to capture one frame from the webcam
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        print("[test] Cannot open camera — exiting")
    else:
        ret, frame = cap.read()
        if ret:
            results = det.detect(frame)
            print(f"Detected {len(results)} object(s):")
            for r in results:
                print(f"  {r['label']}: {r['confidence']:.0%} at {r['box']}")

            annotated = det.annotate_frame(frame.copy(), results)
            cv2.imshow("Detection Test", annotated)
            print("\nPress any key to close...")
            cv2.waitKey(0)
        else:
            print("[test] Failed to capture frame")

        cap.release()
        cv2.destroyAllWindows()
