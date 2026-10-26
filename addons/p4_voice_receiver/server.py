"""LAN-only, token-authenticated PCM receiver. No audio retrieval endpoint."""
import hmac
import json
import logging
import os
from pathlib import Path
import re
import shutil
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import uuid
import wave

PCM_BYTES = 48000 * 2 * 10
LOG = logging.getLogger("p4_voice_receiver")


class Receiver(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 4

    def __init__(self, address, directory, token, max_recordings=100):
        if not re.fullmatch(r"[0-9a-f]{64}", token):
            raise ValueError("Token must be 64 random lowercase hexadecimal characters")
        if not 1 <= max_recordings <= 10000:
            raise ValueError("max_recordings must be 1..10000")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.token = token
        self.max_recordings = max_recordings
        self.upload_lock = threading.Lock()
        # Bound connection threads as well as concurrent disk writes.
        self.slots = threading.BoundedSemaphore(4)
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "P4Voice/0.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *_args):
        # Do not log headers, authentication tokens or user-controlled URLs.
        pass

    def reply(self, code, message):
        body = json.dumps({"message": message}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_POST(self):
        if self.path != "/recordings":
            self.reply(404, "Not found")
            return
        supplied = self.headers.get("Authorization", "").encode("utf-8")
        expected = ("Bearer " + self.server.token).encode("ascii")
        if not hmac.compare_digest(supplied, expected):
            self.reply(401, "Unauthorized")
            return
        if self.headers.get("Transfer-Encoding") or self.headers.get_all("Content-Length") != [str(PCM_BYTES)]:
            self.reply(400, "Exactly 960000 PCM bytes required; chunked transfer is unsupported")
            return
        if self.headers.get("Content-Type") != "application/octet-stream":
            self.reply(415, "Expected application/octet-stream")
            return
        if not self.server.upload_lock.acquire(blocking=False):
            self.reply(503, "Another upload is active")
            return
        temporary = None
        saved = None
        try:
            directory = self.server.directory
            if len(list(directory.glob("*.wav"))) >= self.server.max_recordings:
                self.reply(507, "Recording limit reached; remove or archive old recordings")
                return
            if shutil.disk_usage(directory).free < PCM_BYTES + 10 * 1024 * 1024:
                self.reply(507, "Insufficient free disk space")
                return
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_UTC")
            name = f"vzkaz_{stamp}_{uuid.uuid4().hex[:8]}.wav"
            saved = directory / name
            temporary = directory / ("." + name + ".part")
            with temporary.open("xb") as raw:
                with wave.open(raw, "wb") as output:
                    output.setnchannels(1)
                    output.setsampwidth(2)
                    output.setframerate(48000)
                    remaining = PCM_BYTES
                    while remaining:
                        chunk = self.rfile.read(min(16384, remaining))
                        if not chunk:
                            raise EOFError("Incomplete upload")
                        output.writeframesraw(chunk)
                        remaining -= len(chunk)
                raw.flush()
                os.fsync(raw.fileno())
            os.replace(temporary, saved)
            temporary = None
            LOG.info("Saved %s: mono 48000 Hz, 16 bit, 10 seconds", name)
        except (OSError, EOFError):
            LOG.warning("Upload failed; incomplete recording was discarded")
            try:
                self.reply(400, "Incomplete upload or storage error")
            except OSError:
                pass
            return
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            self.server.upload_lock.release()
        try:
            self.reply(201, saved.name)
        except OSError:
            LOG.warning("File saved but client disconnected before acknowledgement")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    options = json.loads(Path("/data/options.json").read_text())
    server = Receiver(("0.0.0.0", 8099), "/media/vzkazy", options["token"], options.get("max_recordings", 100))
    LOG.info("Receiver ready on port 8099; destination /media/vzkazy")
    server.serve_forever()


if __name__ == "__main__":
    main()
