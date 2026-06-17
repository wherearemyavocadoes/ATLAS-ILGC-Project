"""
caption.py — Natural-language caption generator for detected objects.

Takes object detections + filtered ultrasonic distance and produces
human-readable spoken captions like:
    "bottle, approximately 45 centimeters ahead"
    "Warning! Chair very close, about 20 centimeters"

Includes cooldown logic to avoid repeating the same caption
too frequently (annoying for the user).

Run target: Raspberry Pi / Thonny
"""

import time
import config


class CaptionGenerator:
    """
    Generates spoken captions from detection results and distance.

    Prioritizes the closest / most confident detection and adds
    urgency prefixes based on distance.
    """

    def __init__(self):
        self.cooldown = config.CAPTION_COOLDOWN
        self.close_threshold = config.CAPTION_CLOSE_THRESHOLD
        self.very_close = config.CAPTION_VERY_CLOSE

        # Track last spoken caption to enforce cooldown
        self._last_caption = ""
        self._last_time = 0.0

    def _format_distance(self, distance_cm): #Converting distance into a speak-able phrase
        """
        Convert distance in cm to a natural spoken phrase.

        Examples:
            25.0  → "25 centimeters"
            120.0 → "1.2 meters"
            300.0 → "3 meters"
        """
        if distance_cm < 100:
            return f"{int(distance_cm)} centimeters"
        else:
            meters = distance_cm / 100.0
            if meters == int(meters):
                return f"{int(meters)} meters"
            else:
                return f"{meters:.1f} meters"

    def _build_caption(self, label, confidence, distance_cm): #Using the speak-able terms from previous method, we add fully formed captions with urgency terms
        """
        Build a single caption string for one detection.

        Args:
            label (str): Object class name (e.g. "bottle").
            confidence (float): Detection confidence 0.0–1.0.
            distance_cm (float): Filtered distance in cm.

        Returns:
            str: Human-readable caption.
        """
        dist_phrase = self._format_distance(distance_cm)

        # Urgency tiers
        if distance_cm < self.very_close:
            # URGENT — very close object
            caption = f"Caution! {label} very close, about {dist_phrase} ahead"
        elif distance_cm < self.close_threshold:
            # WARNING — object is close
            caption = f"Warning, {label} nearby, approximately {dist_phrase} ahead"
        else:
            # NORMAL — informational
            caption = f"{label} detected, approximately {dist_phrase} ahead"

        return caption

    def generate(self, detections, distance_cm):
        """
        Generate a caption from the list of detections and the
        current filtered distance.

        Picks the best (most confident) detection and generates
        a spoken caption. Returns None if the same caption was
        spoken recently (cooldown).

        Args:
            detections (list of dict): From detector.detect().
                Each has 'label', 'confidence', 'box'.
            distance_cm (float): Kalman-filtered ultrasonic distance.

        Returns:
            str or None: Caption to speak, or None if suppressed.
        """
        if not detections:
            # No objects detected
            # Only announce "path clear" if we were previously warning
            if self._last_caption and self._last_caption.startswith(("Caution", "Warning")):
                now = time.time()
                if now - self._last_time > self.cooldown:
                    self._last_caption = "Path is clear"
                    self._last_time = now
                    return "Path is clear"
            return None

        # Pick the best detection (already sorted by confidence in detector.py)
        best = detections[0] #Taking the first detection (since it is already sorted by confidence in detector.py)
        label = best['label']  #Labelling the detection
        confidence = best['confidence'] #Checking confidence (0 to 1)

        # Build the caption
        caption = self._build_caption(label, confidence, distance_cm)

        # Check cooldown — don't repeat the same object+tier too quickly
        # We use a simplified key: object label + distance tier
        tier = self._get_tier(distance_cm)
        caption_key = f"{label}_{tier}"

        now = time.time()
        if caption_key == self._last_caption and (now - self._last_time) < self.cooldown:
            # Same caption recently spoken — suppress
            return None

        # New or different caption — allow it
        self._last_caption = caption_key
        self._last_time = now

        return caption

    def _get_tier(self, distance_cm): #Checking the distance and grouping it into different tiers (close, medium, far)
        """Classify distance into a tier for cooldown grouping."""
        if distance_cm < self.very_close:
            return "very_close"
        elif distance_cm < self.close_threshold:
            return "close"
        elif distance_cm < config.BUZZER_TIER_OFF:
            return "medium"
        else:
            return "far"

    def generate_proximity_warning(self, distance_cm): #Generating a distance based caption without the class/object name if it's unidentified
        """ 
        Generate a distance-only warning when no specific object
        is detected but something is very close.

        Useful as a fallback when the ultrasonic sensor detects
        an obstacle that the camera can't identify.

        Args:
            distance_cm (float): Filtered distance.

        Returns:
            str or None: Warning caption or None.
        """
        if distance_cm >= self.close_threshold:
            return None

        now = time.time()
        caption_key = f"obstacle_{self._get_tier(distance_cm)}"

        if caption_key == self._last_caption and (now - self._last_time) < self.cooldown:
            return None

        dist_phrase = self._format_distance(distance_cm)

        if distance_cm < self.very_close:
            caption = f"Caution! Obstacle very close, about {dist_phrase}"
        else:
            caption = f"Obstacle detected, approximately {dist_phrase} ahead"

        self._last_caption = caption_key
        self._last_time = now

        return caption


# ──────────────────────────────────────────────
#  Quick test (run this file directly in Thonny)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    gen = CaptionGenerator()

    # Simulate detections at various distances
    test_cases = [
        ([{'label': 'bottle', 'confidence': 0.85, 'box': (10, 10, 50, 80)}], 150.0),
        ([{'label': 'bottle', 'confidence': 0.85, 'box': (10, 10, 50, 80)}], 80.0),
        ([{'label': 'chair', 'confidence': 0.72, 'box': (20, 20, 100, 150)}], 35.0),
        ([{'label': 'person', 'confidence': 0.91, 'box': (50, 10, 200, 230)}], 15.0),
        ([], 200.0),  # No detection
    ]

    print("Caption Generator Test")
    print("-" * 60)

    for detections, dist in test_cases:
        # Reset cooldown for testing
        gen._last_caption = ""
        gen._last_time = 0.0

        caption = gen.generate(detections, dist)
        obj = detections[0]['label'] if detections else "none"
        print(f"  Object: {obj:>8s} | Distance: {dist:>6.0f} cm | Caption: {caption}")

    print("-" * 60)
    print("Done.")
