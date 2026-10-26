import http.client
import importlib.util
from pathlib import Path
import socket
import tempfile
import threading
import unittest
import wave

spec = importlib.util.spec_from_file_location("receiver", Path(__file__).with_name("server.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.test_root = Path(__file__).resolve().parents[2] / "investigation" / "voice-message"
        self.test_root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="receiver-test-", dir=self.test_root)
        self.server = module.Receiver(("127.0.0.1", 0), self.tmp.name, "a" * 64, 2)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        assert Path(self.tmp.name).resolve().is_relative_to(self.test_root.resolve())
        self.tmp.cleanup()

    def post(self, data, token="a" * 64, extra=None):
        headers = {"Authorization": "Bearer " + token, "Content-Type": "application/octet-stream"}
        headers.update(extra or {})
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request("POST", "/recordings", data, headers)
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_complete_pcm_preserved_as_valid_wav(self):
        pcm = b"\x34\x12\xcc\xed" * (module.PCM_BYTES // 4)
        self.assertEqual(self.post(pcm)[0], 201)
        files = list(Path(self.tmp.name).glob("*.wav"))
        self.assertEqual(len(files), 1)
        with wave.open(str(files[0]), "rb") as recording:
            self.assertEqual((recording.getnchannels(), recording.getsampwidth(), recording.getframerate()), (1, 2, 48000))
            self.assertEqual(recording.getnframes(), 480000)
            self.assertEqual(recording.readframes(480000), pcm)

    def test_reject_auth_size_and_format(self):
        self.assertEqual(self.post(b"x", token="bad")[0], 401)
        self.assertEqual(self.post(b"x")[0], 400)
        self.assertEqual(self.post(b"", extra={"Content-Length": str(module.PCM_BYTES), "Content-Type": "audio/wav"})[0], 415)
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_truncated_upload_leaves_no_file(self):
        connection = socket.create_connection(("127.0.0.1", self.port))
        request = ("POST /recordings HTTP/1.0\r\nAuthorization: Bearer " + "a" * 64 +
                   "\r\nContent-Type: application/octet-stream\r\nContent-Length: 960000\r\n\r\n").encode()
        connection.sendall(request + b"\x00" * 10)
        connection.shutdown(socket.SHUT_WR)
        while connection.recv(4096):
            pass
        connection.close()
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_quota_preserves_existing_recordings(self):
        directory = Path(self.tmp.name)
        (directory / "one.wav").write_bytes(b"existing")
        (directory / "two.wav").write_bytes(b"existing")
        self.assertEqual(self.post(b"", extra={"Content-Length": str(module.PCM_BYTES)})[0], 507)
        self.assertEqual((directory / "one.wav").read_bytes(), b"existing")

    def test_parallel_upload_rejected(self):
        self.server.upload_lock.acquire()
        try:
            self.assertEqual(self.post(b"", extra={"Content-Length": str(module.PCM_BYTES)})[0], 503)
        finally:
            self.server.upload_lock.release()


if __name__ == "__main__":
    unittest.main()
