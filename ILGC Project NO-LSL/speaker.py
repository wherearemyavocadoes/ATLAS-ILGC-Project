"""
speaker.py — Text-to-speech output using espeak directly.

Speaks captions aloud through the connected speaker.
Uses espeak via subprocess (more reliable on RPi than pyttsx3).
Runs in a background thread so it doesn't block the detection loop.

Run target: Raspberry Pi / Thonny
"""

import threading
import queue
import subprocess #Used to run system/terminal commands from python
import shutil #Used to find the path to executables on your system

import config


class Speaker:
    """
    Non-blocking TTS speaker using espeak subprocess.

    Usage:
        spk = Speaker()
        spk.start()
        spk.speak("bottle detected, 45 centimeters ahead")
        spk.stop()
    """

    def __init__(self):
        self._queue = queue.Queue(maxsize=5) #Queue for speech requests
        self._running = False #Flag for indicating thread should continue running
        self._thread = None #Reference to background thread

        # Check which TTS binary is available
        self._tts_cmd = None #Command to run TTS
        for cmd in ["espeak-ng", "espeak"]: #Check for espeak-ng or espeak
            if shutil.which(cmd): #Check if the command exists and whether it's installed
                self._tts_cmd = cmd #Storing whichever speech engine is available
                break

        if self._tts_cmd is None: #Warning if uninstalled
            print("[speaker] WARNING: espeak not found — "
                  "captions will be printed only")
            print("[speaker] Install with: sudo apt install espeak-ng")

    def start(self):# To start the text to speech system
        """Start the background TTS thread."""
        self._running = True #Set running to true
        self._thread = threading.Thread( #Running the worker thread in background
            target=self._worker, daemon=True #Daemon = runs in background, independent of main program
        )
        self._thread.start() #Starting the thread
        if self._tts_cmd: #Checking if the speech engine is available
            print(f"[speaker] TTS engine started ({self._tts_cmd})")
        else: #If not available
            print("[speaker] TTS engine started (print-only mode)")

    def _worker(self):
        """Background thread: speaks queued captions."""
        while self._running: #While the system is running
            try: #Try to get the text from the queue
                text = self._queue.get(timeout=0.5)
            except queue.Empty: #If queue is empty, continue
                continue

            if text is None: #If no text found, then break the loop
                break

            print(f'[speaker] Speaking: "{text}"') #Printing the text to be spoken

            if self._tts_cmd: #Checking if the speech engine is available
                try: #Try to run the command
                    subprocess.run(
                        [
                            self._tts_cmd, #Using the speech engine
                            "-s", str(config.TTS_RATE), #Setting the rate
                            "-a", str(int(config.TTS_VOLUME * 200)), #Setting the volume
                            text #The text to be spoken
                        ], #runs a terminal command of type: espeak-ng -s 160 -a 200 "Person ahead"
                        timeout=15, #Waits 15 seconds for the command to finish
                        stderr=subprocess.DEVNULL #Hides any error messages
                    )
                except subprocess.TimeoutExpired: #If the command takes longer than 15 seconds
                    print("[speaker] TTS timed out")
                except Exception as e: #Any other error
                    print(f"[speaker] TTS error: {e}")

            self._queue.task_done() #Marks the task as done

    def speak(self, text): 
        """
        Queue a caption to be spoken. Non-blocking.
        If the queue is full, the oldest is dropped.
        """
        if not text: #If no text then return nothing
            return

        if self._queue.full(): #IF the queue is full, then remove the oldest message
            try:
                self._queue.get_nowait() #get_nowait = gets the message without waiting for it
            except queue.Empty: #If queue is empty, continue
                pass

        try:
            self._queue.put_nowait(text) #put_nowait = puts the message without waiting for it
        except queue.Full:
            pass

    def stop(self): #Stop the TTS thread
        """Stop the TTS thread."""
        self._running = False
        try: #Try to stop the TTS thread
            self._queue.put_nowait(None) #Put None to stop the worker thread
        except queue.Full: #If queue is full, continue
            pass
        if self._thread: #If thread exists
            self._thread.join(timeout=3.0) #Wait for the thread to finish
        print("[speaker] Stopped")

    def is_speaking(self): #Check if TTS is speaking
        return not self._queue.empty()


# ── Quick test ──
if __name__ == "__main__":
    import time
    spk = Speaker()
    spk.start()

    for phrase in [
        "Navigation system ready",
        "bottle detected, approximately 45 centimeters ahead",
        "Warning, chair nearby",
        "Path is clear",
    ]:
        spk.speak(phrase)
        time.sleep(4)

    spk.stop()
    print("Done.")
