"""These tests use only Python's standard library; no HA installation required."""
import importlib
import io
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import wave
from concurrent.futures import ThreadPoolExecutor

PACKAGE = pathlib.Path(__file__).resolve().parents[1] / "custom_components/voice_inbox"
module = types.ModuleType("voice_inbox_core")
module.__path__ = [str(PACKAGE)]
sys.modules.setdefault("voice_inbox_core", module)
s = importlib.import_module("voice_inbox_core.storage")
a = importlib.import_module("voice_inbox_core.access")

def wav_bytes(rate=16000, frames=160, channels=1):
    raw = io.BytesIO()
    with wave.open(raw, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\0\0" * frames * channels)
    return raw.getvalue()

class StorageTests(unittest.TestCase):
    def test_media_directory_mapping(self):
        # HA's default identifier need not be "local".
        path = str(pathlib.Path(self.tmp.name).resolve())
        self.assertEqual(s.select_media_directory({"media": path}), ("media", pathlib.Path(path)))
        with self.assertRaises(ValueError):
            s.select_media_directory({})
        with self.assertRaises(ValueError):
            s.select_media_directory({"a": path, "b": path + "-other"})
        custom = s.Store(pathlib.Path(path)/"custom", "media")
        saved = custom.save("dvere",b"\0\0",16000,"application/octet-stream")
        self.assertTrue(saved["media_content_id"].startswith("media-source://media_source/media/"))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = s.Store(pathlib.Path(self.tmp.name) / "vzkazy")

    def reject(self, status, function, *args):
        with self.assertRaises(s.Rejected) as caught:
            function(*args)
        self.assertEqual(caught.exception.status, status)

    def test_pcm_and_wav_both_rates(self):
        for rate in (16000, 48000):
            for mime in ("application/octet-stream", "audio/wav"):
                body = b"\0\0" * rate if mime.startswith("application") else wav_bytes(rate, rate)
                result = self.store.save("dvere", body, rate, mime)
                self.assertEqual(result["duration"], 1)
                path = self.store.root / "dvere" / result["file"]
                with wave.open(str(path)) as w:
                    self.assertEqual(w.getparams()[:3], (1, 2, rate))
                    self.assertEqual(w.getnframes(), rate)
                self.assertFalse(list(path.parent.glob("*.part")))

    def test_duration_boundary(self):
        self.assertEqual(len(s.decode(b"\0" * (16000*2*60),16000,"application/octet-stream")),1920000)
        self.reject(413,s.decode,b"\0"*(16000*2*60+2),16000,"application/octet-stream")

    def test_size_empty_and_alignment(self):
        self.reject(400,s.decode,b"",16000,"application/octet-stream")
        self.reject(400,s.decode,b"a",16000,"application/octet-stream")
        self.reject(413,s.decode,b"\0"*(s.MAX_BYTES+1),16000,"application/octet-stream")

    def test_bad_wav(self):
        self.reject(400,s.decode,b"not wav",16000,"audio/wav")
        self.reject(400,s.decode,wav_bytes()[:-1],16000,"audio/wav")
        self.reject(415,s.decode,wav_bytes(48000),16000,"audio/wav")
        self.reject(415,s.decode,wav_bytes(channels=2),16000,"audio/wav")

    def test_metadata(self):
        headers={"X-Audio-Rate":"16000","X-Audio-Bits":"16","X-Audio-Channels":"1","Content-Type":"audio/wav"}
        self.assertEqual(s.metadata(headers),(16000,"audio/wav"))
        for key,value,status in [("X-Audio-Rate","bogus",400),("X-Audio-Bits","24",415),("Content-Encoding","gzip",415)]:
            self.reject(status,s.metadata,{**headers,key:value})

    def test_no_path_traversal(self):
        for source in ("../x","dvere/x","C:\\x",".","a"*33):
            self.reject(400,self.store.save,source,b"\0\0",16000,"application/octet-stream")

    def test_disk_quota(self):
        with patch.object(s.shutil,"disk_usage",return_value=types.SimpleNamespace(free=0)):
            self.reject(507,self.store.save,"dvere",b"\0\0",16000,"application/octet-stream")
        with patch.object(s,"MAX_FILES",1):
            self.store.save("dvere",b"\0\0",16000,"application/octet-stream")
            self.reject(507,self.store.save,"obyvak",b"\0\0",16000,"application/octet-stream")

    def test_atomic_failure_cleanup(self):
        with patch.object(s.os,"replace",side_effect=OSError(28,"disk full")):
            self.reject(507,self.store.save,"dvere",b"\0\0",16000,"application/octet-stream")
        self.assertEqual(list((self.store.root/"dvere").iterdir()),[])

    def test_permission_failure(self):
        with patch.object(s.os,"replace",side_effect=PermissionError(13,"denied")):
            self.reject(503,self.store.save,"dvere",b"\0\0",16000,"application/octet-stream")

    def test_keys(self):
        key="a"*64
        self.assertTrue(s.authenticate(key,s.key_digest(key)))
        self.assertFalse(s.authenticate("b"*64,s.key_digest(key)))
        self.assertFalse(s.authenticate("a",s.key_digest(key)))

    def test_concurrent_global_quota(self):
        def save(source):
            try:
                self.store.save(source,b"\0\0",16000,"application/octet-stream")
                return 201
            except s.Rejected as exc:
                return exc.status
        with patch.object(s,"MAX_FILES",1), ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(save,["dvere","obyvak"])),[201,507])

    def test_network(self):
        self.assertTrue(a.valid_network("192.168.0.0/24"))
        self.assertFalse(a.valid_network("0.0.0.0/0"))
        self.assertFalse(a.valid_network("192.168.0.7/24"))
        args=("192.168.0.5","192.168.0.5","192.168.0.0/24")
        self.assertTrue(a.direct_lan(*args,False,False))
        self.assertFalse(a.direct_lan(*args,True,False))
        self.assertFalse(a.direct_lan(*args,False,True))
        self.assertFalse(a.direct_lan(args[0],"127.0.0.1",args[2],False,False))

    def test_rate_limit_expiry_and_global_cap(self):
        now=[0]
        limiter=a.Attempts(lambda:now[0])
        for _ in range(5): limiter.failure("a")
        self.assertTrue(limiter.blocked("a"))
        self.assertFalse(limiter.blocked("b"))
        now[0]=61
        self.assertFalse(limiter.blocked("a"))
        for i in range(50): limiter.failure(str(i))
        self.assertTrue(limiter.blocked("new"))
        for i in range(300): limiter.failure(str(i))
        self.assertLessEqual(len(limiter.by_ip),256)

if __name__ == "__main__":
    unittest.main()
