"""Create one second of 440 Hz WAV, 16 kHz / 16-bit / mono; never overwrite."""
from pathlib import Path
import math
import struct
import wave

path = Path("sample-16000.wav")
with path.open("xb") as raw:
    with wave.open(raw, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * n / 16000))) for n in range(16000)))
print(path.resolve())
