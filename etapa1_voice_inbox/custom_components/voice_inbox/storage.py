"""Bounded PCM/WAV validation and disk operations; execute outside HA's loop."""
from __future__ import annotations
import hashlib
import hmac
import io
import os
from pathlib import Path
import re
import shutil
import struct
import threading
import uuid
import wave
from urllib.parse import quote
from datetime import datetime, timezone

from .const import MAX_BYTES, MAX_SECONDS, MAX_FILES, RESERVE_BYTES

class Rejected(Exception):
    def __init__(self, status: int, code: str):
        self.status, self.code = status, code
        super().__init__(code)

def select_media_directory(media_dirs):
    """Prefer /media regardless of its HA identifier; never invent a mapping."""
    candidates = {str(key): Path(value) for key, value in media_dirs.items()
                  if value and Path(value).is_absolute()}
    for key, path in candidates.items():
        if path == Path("/media"):
            return key, path
    if "local" in candidates:
        return "local", candidates["local"]
    if len(candidates) == 1:
        return next(iter(candidates.items()))
    raise ValueError("No unambiguous media directory; configure /media or a local media directory")

def valid_source(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", value))

def key_digest(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

def authenticate(key: str, digest: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", key)) and hmac.compare_digest(key_digest(key), digest)

def metadata(headers):
    try:
        rate = int(headers.get("X-Audio-Rate", ""))
        bits = int(headers.get("X-Audio-Bits", ""))
        channels = int(headers.get("X-Audio-Channels", ""))
    except (ValueError, TypeError):
        raise Rejected(400, "invalid_metadata") from None
    if rate not in (16000, 48000) or bits != 16 or channels != 1:
        raise Rejected(415, "unsupported_audio")
    if headers.get("Content-Encoding", "identity").lower() != "identity":
        raise Rejected(415, "content_encoding_not_supported")
    mime = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if mime not in ("application/octet-stream", "audio/wav", "audio/x-wav"):
        raise Rejected(415, "unsupported_content_type")
    return rate, mime

def decode(body: bytes, rate: int, mime: str) -> bytes:
    if len(body) > MAX_BYTES:
        raise Rejected(413, "body_too_large")
    if mime == "application/octet-stream":
        pcm = body
    else:
        if len(body) < 12 or body[:4] != b"RIFF" or body[8:12] != b"WAVE" or int.from_bytes(body[4:8], "little") + 8 != len(body):
            raise Rejected(400, "invalid_wav")
        try:
            with wave.open(io.BytesIO(body), "rb") as wav:
                if (wav.getframerate(), wav.getsampwidth(), wav.getnchannels(), wav.getcomptype()) != (rate, 2, 1, "NONE"):
                    raise Rejected(415, "wav_metadata_mismatch")
                if wav.getnframes() > rate * MAX_SECONDS:
                    raise Rejected(413, "duration_too_long")
                pcm = wav.readframes(wav.getnframes())
                if len(pcm) != wav.getnframes() * 2:
                    raise Rejected(400, "truncated_wav")
        except (wave.Error, EOFError, ValueError, struct.error):
            raise Rejected(400, "invalid_wav") from None
    if not pcm or len(pcm) % 2:
        raise Rejected(400, "invalid_pcm_length")
    if len(pcm) > rate * 2 * MAX_SECONDS:
        raise Rejected(413, "duration_too_long")
    return pcm

class Store:
    def __init__(self, root=Path("/media/vzkazy"), media_id="local"):
        self.root = Path(root)
        self.media_id = media_id
        self.lock = threading.Lock()

    def snapshot(self):
        """Read persisted state under the same lock as uploads; executor only."""
        with self.lock:
            if self.root.is_symlink():
                raise OSError("Unsafe storage")
            if not self.root.exists():
                return {"count": 0, "latest": {}}
            count, latest = 0, {}
            for directory in self.root.iterdir():
                if directory.is_symlink() or not directory.is_dir():
                    continue
                newest = None
                for file in directory.iterdir():
                    if file.suffix != ".wav" or file.is_symlink() or not file.is_file():
                        continue
                    count += 1
                    stat = file.stat()
                    candidate = (stat.st_mtime_ns, file.name, file)
                    if newest is None or candidate[:2] > newest[:2]:
                        newest = candidate
                if newest and valid_source(directory.name):
                    _, name, file = newest
                    info = {"time": datetime.fromtimestamp(file.stat().st_mtime, timezone.utc),
                            "file": name, "source": directory.name,
                            "media_content_id": f"media-source://media_source/{quote(self.media_id, safe='')}/vzkazy/{directory.name}/{quote(name, safe='')}"}
                    latest[directory.name] = info
            return {"count": count, "latest": latest}

    def read_audio(self, source, filename):
        """Bounded read of an inbox-generated filename, for authenticated admins."""
        if not valid_source(source) or not re.fullmatch(r"[0-9]{8}T[0-9]{6}_[0-9]{6}Z_[0-9a-f]{32}\.wav", filename):
            raise Rejected(400, "invalid_filename")
        with self.lock:
            try:
                directory = self.root / source
                file = directory / filename
                if self.root.is_symlink() or directory.is_symlink() or file.is_symlink():
                    raise Rejected(503, "unsafe_storage")
                if file.resolve().parent != directory.resolve() or directory.resolve().parent != self.root.resolve():
                    raise Rejected(503, "unsafe_storage")
                with file.open("rb") as stream:
                    body = stream.read(MAX_BYTES + 45)
                if len(body) > MAX_BYTES + 44:
                    raise Rejected(413, "body_too_large")
                return body
            except OSError:
                raise Rejected(503, "audio_unavailable") from None

    def save(self, source: str, body: bytes, rate: int, mime: str):
        if not valid_source(source):
            raise Rejected(400, "invalid_source")
        pcm = decode(body, rate, mime)
        # Serialize global quota checks and commits across all sources.
        with self.lock:
            temporary = None
            try:
                if self.root.is_symlink():
                    raise Rejected(503, "unsafe_storage")
                self.root.mkdir(parents=True, exist_ok=True)
                # Do not follow source-directory symlinks, including those created externally.
                directory = self.root / source
                if directory.is_symlink():
                    raise Rejected(503, "unsafe_storage")
                directory.mkdir(exist_ok=True)
                if directory.resolve().parent != self.root.resolve():
                    raise Rejected(503, "unsafe_storage")
                count = 0
                for child in self.root.iterdir():
                    if child.is_dir() and not child.is_symlink():
                        count += sum(1 for f in child.iterdir() if f.suffix == ".wav" and not f.is_symlink() and f.is_file())
                if count >= MAX_FILES:
                    raise Rejected(507, "file_quota_reached")
                if shutil.disk_usage(directory).free < len(pcm) + 44 + RESERVE_BYTES:
                    raise Rejected(507, "insufficient_disk_space")
                now = datetime.now(timezone.utc)
                name = now.strftime("%Y%m%dT%H%M%S_%fZ_") + uuid.uuid4().hex + ".wav"
                temporary = directory / ("." + name + ".part")
                with temporary.open("xb") as raw:
                    with wave.open(raw, "wb") as wav:
                        wav.setnchannels(1)
                        wav.setsampwidth(2)
                        wav.setframerate(rate)
                        wav.writeframes(pcm)
                    raw.flush()
                    os.fsync(raw.fileno())
                os.replace(temporary, directory / name)
                temporary = None
                return {"source": source, "file": name, "relative_path": f"vzkazy/{source}/{name}",
                        "duration": len(pcm) / (rate * 2), "sample_rate": rate,
                        "time": now.isoformat(), "bytes": len(pcm) + 44,
                        "media_content_id": f"media-source://media_source/{quote(self.media_id, safe='')}/vzkazy/{source}/{name}"}
            except OSError as err:
                raise Rejected(507 if err.errno in (28, 122) else 503, "storage_unavailable") from None
            finally:
                if temporary is not None:
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError:
                        pass
