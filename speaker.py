"""
speaker.py — Text-to-speech output using espeak directly.

Speaks captions aloud through the connected speaker.
Uses espeak via subprocess (more reliable on RPi than pyttsx3).
Runs in a background thread so it doesn't block the detection loop.

Run target: Raspberry Pi / Thonny
"""

import threading
import queue
import subprocess
import shutil

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
        self._queue = queue.Queue(maxsize=5)
        self._running = False
        self._thread = None

        # Check which TTS binary is available
        self._tts_cmd = None
        for cmd in ["espeak-ng", "espeak"]:
            if shutil.which(cmd):
                self._tts_cmd = cmd
                break

        if self._tts_cmd is None:
            print("[speaker] WARNING: espeak not found — "
                  "captions will be printed only")
            print("[speaker] Install with: sudo apt install espeak-ng")

    def start(self):
        """Start the background TTS thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._worker, daemon=True
        )
        self._thread.start()
        if self._tts_cmd:
            print(f"[speaker] TTS engine started ({self._tts_cmd})")
        else:
            print("[speaker] TTS engine started (print-only mode)")

    def _worker(self):
        """Background thread: speaks queued captions."""
        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if text is None:
                break  # Poison pill

            print(f'[speaker] Speaking: "{text}"')

            if self._tts_cmd:
                try:
                    subprocess.run(
                        [
                            self._tts_cmd,
                            "-s", str(config.TTS_RATE),
                            "-a", str(int(config.TTS_VOLUME * 200)),
                            text
                        ],
                        timeout=15,
                        stderr=subprocess.DEVNULL
                    )
                except subprocess.TimeoutExpired:
                    print("[speaker] TTS timed out")
                except Exception as e:
                    print(f"[speaker] TTS error: {e}")

            self._queue.task_done()

    def speak(self, text):
        """
        Queue a caption to be spoken. Non-blocking.
        If the queue is full, the oldest is dropped.
        """
        if not text:
            return

        if self._queue.full():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass

        try:
            self._queue.put_nowait(text)
        except queue.Full:
            pass

    def stop(self):
        """Stop the TTS thread."""
        self._running = False
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread:
            self._thread.join(timeout=3.0)
        print("[speaker] Stopped")

    def is_speaking(self):
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
