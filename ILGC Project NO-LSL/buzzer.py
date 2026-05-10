"""
buzzer.py — PWM speaker proximity alerts on GPIO 13.

Uses GPIO.PWM to drive the SmartFlex speaker with
distance-threshold based beeps only.

Distance tiers:
    > 150 cm  -> Silent
    100-150   -> Slow beep   (low freq)
    50-100    -> Medium beep (mid freq)
    20-50     -> Fast beep   (high freq)
    < 20 cm   -> Continuous  (highest freq)

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


class Buzzer:
    def __init__(self, pin=None):
        self.pin = pin or config.BUZZER_PIN
        self._distance = 999.0
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._pwm = None

        if RPI_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.pin, GPIO.OUT)
            self._pwm = GPIO.PWM(self.pin, 1000)

    def _tone(self, frequency, duration):
        """Play a tone at given frequency for duration seconds."""
        if not RPI_AVAILABLE or self._pwm is None:
            time.sleep(duration)
            return
        try:
            self._pwm.ChangeFrequency(frequency)
            self._pwm.start(90)
            time.sleep(duration)
            self._pwm.stop()
        except Exception:
            pass

    def _get_params(self, distance):
        """
        Get beep parameters based on distance.
        Returns (frequency, on_time, off_time).
        (0,0,0) = silent. off_time=0 = continuous.
        """
        if distance > config.BUZZER_TIER_OFF:
            return (0, 0, 0)
        elif distance > config.BUZZER_TIER_SLOW:
            return (600, 0.08, 0.92)
        elif distance > config.BUZZER_TIER_MEDIUM:
            return (900, 0.08, 0.25)
        elif distance > config.BUZZER_TIER_FAST:
            return (1200, 0.06, 0.14)
        else:
            return (1500, 0.3, 0)

    def _background_loop(self):
        while self._running:
            with self._lock:
                distance = self._distance

            freq, on_t, off_t = self._get_params(distance)

            if freq == 0:
                time.sleep(0.2)
            elif off_t == 0:
                self._tone(freq, on_t)
                time.sleep(0.02)
            else:
                self._tone(freq, on_t)
                time.sleep(off_t)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._background_loop, daemon=True
        )
        self._thread.start()
        print(f"[buzzer] PWM speaker started on GPIO {self.pin}")

    def stop(self):
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
        with self._lock:
            self._distance = distance_cm

    def cleanup(self):
        self.stop()


# ── Quick test ──
if __name__ == "__main__":
    bz = Buzzer()
    bz.start()
    print("Testing distance-based beeps...")
    try:
        for dist in [200, 130, 80, 35, 10, 35, 80, 200]:
            print(f"  Distance: {dist} cm")
            bz.update(dist)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        bz.cleanup()
        if RPI_AVAILABLE:
            GPIO.cleanup()
    print("Done.")
