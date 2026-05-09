"""
buzzer.py — PWM speaker alerts on GPIO 13.

Uses GPIO.PWM to drive the SmartFlex piezo speaker for:
  1. Proximity alerts — beep speed increases as objects get closer
  2. Object notification tones — distinct tone patterns per object type

Run target: Raspberry Pi / Thonny
"""

import time
import threading

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    print("[buzzer] WARNING: RPi.GPIO not available")

import config

# Tone patterns for different object types
# (frequency_hz, duration_s, pause_s) repeated
OBJECT_TONES = {
    "person":      [(1200, 0.1, 0.05), (1200, 0.1, 0.05), (1200, 0.1, 0)],
    "chair":       [(800, 0.2, 0.1), (600, 0.2, 0)],
    "bottle":      [(1000, 0.15, 0)],
    "car":         [(400, 0.4, 0.1), (400, 0.4, 0)],
    "bus":         [(400, 0.4, 0.1), (400, 0.4, 0)],
    "bicycle":     [(900, 0.1, 0.05), (1100, 0.1, 0)],
    "motorbike":   [(500, 0.3, 0.1), (500, 0.3, 0)],
    "diningtable": [(700, 0.2, 0.1), (500, 0.2, 0)],
    "sofa":        [(600, 0.3, 0)],
    "tvmonitor":   [(1000, 0.1, 0.05), (800, 0.1, 0)],
    "pottedplant": [(900, 0.15, 0.05), (700, 0.15, 0)],
    "train":       [(300, 0.5, 0.1), (300, 0.5, 0)],
    "boat":        [(500, 0.2, 0.1), (700, 0.2, 0)],
}

# Default tone for unknown objects
DEFAULT_TONE = [(1000, 0.15, 0)]


class Buzzer:
    """
    PWM speaker controller for proximity and object alerts.

    Uses GPIO.PWM on pin 13, matching the SmartFlex speaker
    wiring (GPIO.PWM(13, freq), duty cycle 90).
    """

    def __init__(self, pin=None):
        self.pin = pin or config.BUZZER_PIN
        self._distance = 999.0
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._pwm = None
        self._notify_queue = []  # Object tones to play
        self._notify_lock = threading.Lock()

        if RPI_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.pin, GPIO.OUT)
            self._pwm = GPIO.PWM(self.pin, 1000)

    def _tone(self, frequency, duration):
        """Play a single tone at given frequency for duration seconds."""
        if not RPI_AVAILABLE or self._pwm is None:
            time.sleep(duration)
            return

        try:
            self._pwm.ChangeFrequency(frequency)
            self._pwm.start(90)  # 90% duty cycle (matches your test)
            time.sleep(duration)
            self._pwm.stop()
        except Exception:
            pass

    def _play_pattern(self, pattern):
        """Play a sequence of (freq, duration, pause) tuples."""
        for freq, dur, pause in pattern:
            if not self._running:
                break
            self._tone(freq, dur)
            if pause > 0:
                time.sleep(pause)

    def _get_proximity_params(self, distance):
        """
        Get beep frequency and timing for distance.

        Returns (frequency, on_time, off_time).
        (0, 0, 0) = silent. off_time=0 = continuous.
        """
        if distance > config.BUZZER_TIER_OFF:
            return (0, 0, 0)
        elif distance > config.BUZZER_TIER_SLOW:
            return (800, 0.05, 0.95)
        elif distance > config.BUZZER_TIER_MEDIUM:
            return (1000, 0.05, 0.28)
        elif distance > config.BUZZER_TIER_FAST:
            return (1200, 0.05, 0.15)
        else:
            return (1500, 0.3, 0)

    def _background_loop(self):
        """Background loop: handles proximity beeps and object tones."""
        while self._running:
            # Check for queued object notification tones
            pattern = None
            with self._notify_lock:
                if self._notify_queue:
                    pattern = self._notify_queue.pop(0)

            if pattern:
                self._play_pattern(pattern)
                time.sleep(0.3)
                continue

            # Otherwise do proximity beeping
            with self._lock:
                distance = self._distance

            freq, on_t, off_t = self._get_proximity_params(distance)

            if freq == 0:
                time.sleep(0.2)
            elif off_t == 0:
                self._tone(freq, on_t)
                time.sleep(0.02)
            else:
                self._tone(freq, on_t)
                time.sleep(off_t)

    def start(self):
        """Start the alert background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._background_loop, daemon=True
        )
        self._thread.start()
        print(f"[buzzer] PWM speaker started on GPIO {self.pin}")

    def stop(self):
        """Stop and silence."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._pwm:
            try:
                self._pwm.stop()
            except Exception:
                pass
        print("[buzzer] Stopped")

    def update(self, distance_cm):
        """Update current distance for proximity alerts."""
        with self._lock:
            self._distance = distance_cm

    def notify_object(self, label):
        """
        Queue a distinct tone pattern for a detected object.

        Different objects play different tone signatures so the
        user can learn to distinguish them by sound.
        """
        pattern = OBJECT_TONES.get(label, DEFAULT_TONE)
        with self._notify_lock:
            # Only queue if not already queued (avoid spam)
            if len(self._notify_queue) < 2:
                self._notify_queue.append(pattern)

    def cleanup(self):
        self.stop()


# ── Quick test ──
if __name__ == "__main__":
    bz = Buzzer()
    bz.start()

    print("Testing object tones...")
    for obj in ["person", "chair", "bottle", "car"]:
        print(f"  Tone for: {obj}")
        bz.notify_object(obj)
        time.sleep(2)

    print("\nTesting proximity alerts...")
    for dist in [200, 130, 80, 35, 10, 80, 200]:
        print(f"  Distance: {dist} cm")
        bz.update(dist)
        time.sleep(3)

    bz.cleanup()
    if RPI_AVAILABLE:
        GPIO.cleanup()
    print("Done.")
