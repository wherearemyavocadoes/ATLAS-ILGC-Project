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

    #Defining a helper method, that sets up the pins in the GPIO (Broadcom GPIO Numbering)
    def _setup_gpio(self):
        """Configure GPIO pins for the sensor."""
        GPIO.setmode(GPIO.BCM) #setting up the mode to BCM
        GPIO.setwarnings(False) #Hide GPIO warning messages
        GPIO.setup(self.trig_pin, GPIO.OUT) #Setting up the Trigger Pin as Output
        GPIO.setup(self.echo_pin, GPIO.IN) #Setting up the Echo Pin as Input
        GPIO.output(self.trig_pin, GPIO.LOW) #Setting the Trigger Pin to Low
        # Let the sensor settle
        time.sleep(0.1) #Wait for 0.1 seconds after power up to stabilize

    def _read_once(self): #Method defined to get one single reading
        """
        Take a single distance measurement. 

        Returns distance in cm, or None if the reading timed out.
        """
        
        # Send 10µs trigger pulse
        GPIO.output(self.trig_pin, GPIO.HIGH) #Sending signal -> High
        time.sleep(0.00001)  # 10 microseconds trigger pulse
        GPIO.output(self.trig_pin, GPIO.LOW) #Sending signal -> Low

        # Wait for echo to go HIGH (pulse sent)
        pulse_start = time.time()
        deadline = pulse_start + self.timeout

        #Keep looping while ECHO stays LOW
        while GPIO.input(self.echo_pin) == GPIO.LOW: #Waiting for the echo pin to go HIGH (means pulse was sent)
            pulse_start = time.time() #Setting up the current time
            if pulse_start > deadline: #If current time exceeded the deadline (means no echo was received)
                return None

        # Wait for echo to go LOW (pulse returned)
        pulse_end = time.time() #Setting up the end time
        deadline = pulse_end + self.timeout

        #Keep looping while ECHO stays HIGH
        while GPIO.input(self.echo_pin) == GPIO.HIGH:  #Waiting for the echo pin to go LOW (means pulse was returned)
            pulse_end = time.time() #Setting up the end time
            if pulse_end > deadline: #If echo received after longer than deadline, object is too far
                return None  # Timeout — object too far

        # Calculate distance
        # Speed of sound = 34300 cm/s, divide by 2 for round-trip
        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300.0) / 2.0

        #Rejecting outlier readings
        if distance < 2.0 or distance > self.max_distance:
            return None

        return round(distance, 1)

    def _background_loop(self): #Starting an infinite loop that runs in the background
        """Continuously read distance in the background."""
        while self._running: #Running this loop after start method has been executed that set _running to True
            reading = self._read_once() #Taking one single reading
            if reading is not None:
                with self._lock: #using thread lock to make sure self._distanc eis being used only once at a time
                    self._distance = reading #Assigning the distance attribute the reading value
            time.sleep(self.read_interval) #Pausing for defined interval 0.05 seconds

    def start(self): #Defining the start function
        """Start the background reading thread."""
        if self._running: #Checking if the thread is already running
            return #Stop the thread from starting again
        self._running = True #Setting the running attribute to True
        self._thread = threading.Thread(target=self._background_loop, daemon=True) #Creating a new thread
        self._thread.start() #Starting the thread; So here while the start method is being executed, the _background_loop method is also beginning to execute simultaneously
        print(f"[ultrasonic] Started — TRIG={self.trig_pin}, ECHO={self.echo_pin}") #Printing the trigger and echo pin numbers

    def stop(self): #Defining the stop function
        """Stop the background reading thread."""
        self._running = False #Setting the running attribute to False
        if self._thread: #Checking if the thread is not None
            self._thread.join(timeout=2.0) #Joining the thread -> waiting for the thread to finish but max 2 seconds
        print("[ultrasonic] Stopped") #Printing the stop message

    def get_distance(self):
        """
        Get the latest distance reading in cm.

        Returns:
            float: Distance in cm (2.0 – 400.0).
        """
        with self._lock: #Getting the distance but with thread lock to avoid spill
            return self._distance

    def cleanup(self): #Defining a cleanup function to stop the background thread and clean up GPIO
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
