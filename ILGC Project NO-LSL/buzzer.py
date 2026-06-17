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
        self.pin = pin or config.BUZZER_PIN #Buzzer pin
        self._distance = 999.0 #Initial distance    
        self._lock = threading.Lock() #Lock to prevent any other process from using the buzzer at the same time
        self._running = False #Flag for indicating thread should continue running
        self._thread = None #Reference to background thread
        self._pwm = None #Reference to PWM object

        if RPI_AVAILABLE: #If the rpi is available, then setup in BCM mode
            GPIO.setmode(GPIO.BCM) #BCM mode = using the Broadcom GPIO numbering scheme
            GPIO.setwarnings(False) #Disables any warning messages from RPi.GPIO
            GPIO.setup(self.pin, GPIO.OUT) #Setup the pin as an output
            self._pwm = GPIO.PWM(self.pin, 1000) #Setup PWM on the pin with a frequency of 1000Hz

    def _tone(self, frequency, duration): #Play a tone at given frequency for duration seconds  
        """Play a tone at given frequency for duration seconds."""
        if not RPI_AVAILABLE or self._pwm is None: #If rpi not available, then sleep for duration and return
            time.sleep(duration) #Waiting for the duration
            return
        try: #Try to play the tone
            self._pwm.ChangeFrequency(frequency) #Changing the frequency of the PWM
            self._pwm.start(90) #Starting the PWM with 90% duty cycle   
            time.sleep(duration) #Waiting for the duration
            self._pwm.stop() #Stopping the PWM
        except Exception: #Catching any exception
            pass

    def _get_params(self, distance): #Get beep parameters based on distance
        """
        Get beep parameters based on distance.
        Returns (frequency, on_time, off_time).
        (0,0,0) = silent. off_time=0 = continuous.
        """
        if distance > config.BUZZER_TIER_OFF: #If distance is greater than tier off
            return (0, 0, 0) #Return silent
        elif distance > config.BUZZER_TIER_SLOW: #If distance is greater than tier slow
            return (600, 0.08, 0.92) #Returning frequency, on_time, off_time for slow beep
        elif distance > config.BUZZER_TIER_MEDIUM: #If distance is greater than tier medium
            return (900, 0.08, 0.25) #Returning frequency, on_time, off_time for medium beep
        elif distance > config.BUZZER_TIER_FAST: #If distance is greater than tier fast
            return (1200, 0.06, 0.14) #Returning frequency, on_time, off_time for fast beep
        else: #If distance is less than tier fast
            return (1500, 0.3, 0) #Returning frequency, on_time, off_time for continuous beep

    def _background_loop(self): #Background loop to play tones
        while self._running: #While the buzzer is running
            with self._lock: #Lock to prevent any other process from using the buzzer at the same time
                distance = self._distance

            freq, on_t, off_t = self._get_params(distance) #Get beep parameters based on distance

            if freq == 0: #If frequency is 0, then sleep for 0.2 seconds
                time.sleep(0.2) #Waiting for the duration   
            elif off_t == 0: #If off_time is 0, then play continuous beep
                self._tone(freq, on_t) #Playing the tone
                time.sleep(0.02) #Waiting for the duration
            else: #If off_time is not 0, then play beep
                self._tone(freq, on_t) #Playing the tone
                time.sleep(off_t)

    def start(self): #Start the buzzer  
        if self._running: #If the buzzer is already running
            return
        self._running = True #Set the buzzer to running
        self._thread = threading.Thread(
            target=self._background_loop, daemon=True
        )
        self._thread.start()
        print(f"[buzzer] PWM speaker started on GPIO {self.pin}") #Printing that the buzzer has started

    def stop(self): #Stop the buzzer
        self._running = False #Set the buzzer to not running
        if self._thread: #If the thread is running
            self._thread.join(timeout=2.0) #Wait for the thread to finish
        if self._pwm:
            try:
                self._pwm.stop() #Stopping the PWM
            except Exception:
                pass
        print("[buzzer] Stopped")

    def update(self, distance_cm): #Update the buzzer with new distance
        with self._lock: #Lock to prevent any other process from using the buzzer at the same time
            self._distance = distance_cm #Setting the distance

    def cleanup(self): #Cleanup the buzzer
        self.stop() #Stopping the buzzer


# ── Quick test ──
if __name__ == "__main__":
    bz = Buzzer() #Creating a buzzer object
    bz.start() #Starting the buzzer
    print("Testing distance-based beeps...") #Printing the message
    try: #Try to play the tones
        for dist in [200, 130, 80, 35, 10, 35, 80, 200]: #Looping through the distances
            print(f"  Distance: {dist} cm") #Printing the distance
            bz.update(dist)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        bz.cleanup()
        if RPI_AVAILABLE:
            GPIO.cleanup()
    print("Done.")
