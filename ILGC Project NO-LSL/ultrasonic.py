"""
ultrasonic.py — HC-SR04 ultrasonic distance sensor reader.

Reads distance from the HC-SR04 sensor connected to the RPi GPIO.
Runs measurements in a background thread for non-blocking operation.

Wiring (BCM numbering):
    TRIG → GPIO 23
    ECHO → GPIO 24 (use a voltage divider: 5V → 3.3V)
    VCC  → 5V
    GND  → GND

Run target: Raspberry Pi / Thonny
"""

import time
import threading

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    print("[ultrasonic] WARNING: RPi.GPIO not available — using simulated distances")

import config


class UltrasonicSensor:
    """
    Threaded HC-SR04 ultrasonic distance sensor.

    Continuously reads distance in the background.
    Call get_distance() to get the latest reading.
    """

    def __init__(self, trig_pin=None, echo_pin=None):
        self.trig_pin = trig_pin or config.US_TRIG_PIN
        self.echo_pin = echo_pin or config.US_ECHO_PIN
        self.max_distance = config.US_MAX_DISTANCE
        self.timeout = config.US_TIMEOUT
        self.read_interval = config.US_READ_INTERVAL

        self._distance = self.max_distance  # Latest reading (cm)
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

        if RPI_AVAILABLE:
            self._setup_gpio()

    def _setup_gpio(self):
        """Configure GPIO pins for the sensor."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trig_pin, GPIO.LOW)
        # Let the sensor settle
        time.sleep(0.1)

    def _read_once(self):
        """
        Take a single distance measurement.

        Returns distance in cm, or None if the reading timed out.
        """
        if not RPI_AVAILABLE:
            # Simulate a distance for testing on non-RPi machines
            import random
            return random.uniform(30, 200)

        # Send 10µs trigger pulse
        GPIO.output(self.trig_pin, GPIO.HIGH)
        time.sleep(0.00001)  # 10 microseconds
        GPIO.output(self.trig_pin, GPIO.LOW)

        # Wait for echo to go HIGH (pulse sent)
        pulse_start = time.time()
        deadline = pulse_start + self.timeout

        while GPIO.input(self.echo_pin) == GPIO.LOW:
            pulse_start = time.time()
            if pulse_start > deadline:
                return None  # Timeout — no echo received

        # Wait for echo to go LOW (pulse returned)
        pulse_end = time.time()
        deadline = pulse_end + self.timeout

        while GPIO.input(self.echo_pin) == GPIO.HIGH:
            pulse_end = time.time()
            if pulse_end > deadline:
                return None  # Timeout — object too far

        # Calculate distance
        # Speed of sound = 34300 cm/s, divide by 2 for round-trip
        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300.0) / 2.0

        # Clamp to sensor range
        if distance < 2.0 or distance > self.max_distance:
            return None

        return round(distance, 1)

    def _background_loop(self):
        """Continuously read distance in the background."""
        while self._running:
            reading = self._read_once()
            if reading is not None:
                with self._lock:
                    self._distance = reading
            time.sleep(self.read_interval)

    def start(self):
        """Start the background reading thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._background_loop, daemon=True)
        self._thread.start()
        print(f"[ultrasonic] Started — TRIG={self.trig_pin}, ECHO={self.echo_pin}")

    def stop(self):
        """Stop the background reading thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("[ultrasonic] Stopped")

    def get_distance(self):
        """
        Get the latest distance reading in cm.

        Returns:
            float: Distance in cm (2.0 – 400.0).
        """
        with self._lock:
            return self._distance

    def cleanup(self):
        """Stop reading and clean up GPIO."""
        self.stop()
        # Note: GPIO.cleanup() is called once in main.py to avoid conflicts


# ──────────────────────────────────────────────
#  Quick test (run this file directly in Thonny)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    sensor = UltrasonicSensor()
    sensor.start()

    print("Reading distance... (Ctrl+C to stop)")
    try:
        while True:
            dist = sensor.get_distance()
            print(f"  Distance: {dist:.1f} cm")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        sensor.cleanup()
        if RPI_AVAILABLE:
            GPIO.cleanup()
