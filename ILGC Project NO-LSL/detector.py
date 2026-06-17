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
        self.net = None #The loaded neural network model will be stored here; it's a placeholder variable

    def load_model(self): #Loading the MobileNet-SSD model
        """
        Load the MobileNet-SSD model from disk.

        Raises RuntimeError if model files are missing.
        """
        prototxt = config.PROTOTXT_PATH #Getting the path for the prototxt file (blueprint/architecture of the model -> contains the structure of the NN: Contains the structure/layers of the neural network: Input layer -> Convolution layer -> ReLU -> Pooling -> ... -> Output layer)
        caffemodel = config.CAFFEMODEL_PATH #Getting the path for the caffemodel file (contains the numbers: weights and biases learned during model training (millions of values))

        #Throwing error if files not found
        if not os.path.exists(prototxt): #Checking if the prototxt file exists
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
        self.net = cv2.dnn.readNetFromCaffe(prototxt , caffemodel) #Loading the caffe NN into memory using the readNetCaffeModel function 

        # Use the default CPU backend (best for RPi)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV) #Assigning suitable backend: software engine that performs the NN calculations (OpenCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU) #Hardware that will do all the computations (in this case Raspberry Pi's CPU)

        print("[detector] Model loaded successfully")

    def detect(self, frame): #Defining a detect function that takes a frame as input
        """
        Run object detection on a single frame.

        Args:
            frame (numpy.ndarray): BGR image from the camera.

        Returns:
            list of dict: Each detection has:
                - 'label' (str): class name, e.g. "bottle"
                - 'confidence' (float): 0.0-1.0
                - 'box' (tuple): (x1, y1, x2, y2) pixel coordinates
        """
        if self.net is None:
            return []

        h, w = frame.shape[:2] #height and width of the image

        # Create a blob from the frame
        # MobileNet-SSD expects 300x300, mean subtraction (127.5), scale 1/127.5
        blob = cv2.dnn.blobFromImage( #Blob is the image converted into a format in whicht he NN expects it to be
            frame, #image captured
            scalefactor=0.007843,  #1/127.5 -> multiple of every pixel value; basically normalising
            size=(300, 300), #resizing image to 300x300 pixels because MobileNet-SSD was trained on that size
            mean=(127.5, 127.5, 127.5), #Subtracting the mean values of the pixels (averaging) -> mean as in, range is from [0,255] -> 255/2 = 127.5 -> we use this as the mean and to normalise/scale
            swapRB=False, #Keeping the BGR order
            crop=False #After resizing, don't crop any part of the image => keep the image as it is
        )

        self.net.setInput(blob) #Feeding the preprocessed image into the NN input
        detections = self.net.forward() #Running the NN forward, it has the raw output of the NN
        #detections store a weird 4-D array that has batch size, unused dimension, number of detected objects, values per detection
        results = [] #Creating empty list to store valid detections

        for i in range(detections.shape[2]): #Iterating over all detected objects in the frame/image
            confidence = float(detections[0, 0, i, 2]) #Getting the confidence score of the detected object from the 4-D array
            #0th image, 0th group, i number of objects detected, 2nd value is the confidence score
            if confidence < self.confidence_threshold: #If the confidence score is less than the threshold, skip
                continue

            class_id = int(detections[0, 0, i, 1])
            #Getting the class ID from the 4-D array

            #Skip out-of-range IDs
            if class_id <= 0 or class_id >= len(self.class_labels):
                continue
            
            label = self.class_labels[class_id] #Converting class ID to the class name

            # Skip classes not relevant to navigation
            # (reduces false cat/dog/bird detections)
            if hasattr(config, 'NAVIGATION_CLASSES'):
                if label not in config.NAVIGATION_CLASSES:
                    continue

            #Scale bounding box to frame dimensions -> multiplying with the height and width of the image
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h]) #box has the bounding box coordinates given by the network
            x1, y1, x2, y2 = box.astype(int) #converting the bounding box coordinates to integers

            #Prevent coordinates from going outside the frame
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            results.append({ #Storing the detection in the results list
                'label': label,
                'confidence': confidence,
                'box': (x1, y1, x2, y2)
            }) 

        #Sort by confidence (highest first)
        results.sort(key=lambda d: d['confidence'], reverse=True)

        return results #Returning the list of detected objects ranked from highest to lowest confidence

    def annotate_frame(self, frame, detections, distance=None): #Defining a function to draw the bounding box and label on the frame for debugging purposes
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

            #Draw bounding box
            color = (0, 255, 0)  # Green
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2) #Frame, coordinates, color and 2 pixel thick border

            #Drawing label with confidence
            text = f"{label}: {conf:.0%}" #Label and confidence rounded to the nearest integer
            if distance is not None:
                text += f" | {distance:.0f}cm" #Adding the distance in the label rounded to the nearest integer

            #Background for text (beautify stuff) for the bounding box
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, text, (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        #Draw distance bar at the top of the frame
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
