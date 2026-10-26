"""Real aiohttp requests through the view, HA imports pinned by requirements.

Tests do not start a production HA instance. Lifecycle/config-flow tests are separate.
"""
import asyncio
from types import SimpleNamespace
from aiohttp import web
import pytest
from custom_components.voice_inbox.http import Runtime, UploadView
from custom_components.voice_inbox.storage import Store, key_digest
from custom_components.voice_inbox.storage import Rejected

KEY = "a" * 64
HEADERS = {"X-Voice-Source":"dvere","X-Voice-Key":KEY,
           "X-Audio-Rate":"16000","X-Audio-Bits":"16","X-Audio-Channels":"1",
           "Content-Type":"application/octet-stream"}

@pytest.fixture
async def setup_view(aiohttp_client,tmp_path):
    events=[]
    hass=SimpleNamespace(config=SimpleNamespace(components=set()),
        bus=SimpleNamespace(async_fire=lambda name,data:events.append((name,data))),
        async_add_executor_job=lambda f,*args:asyncio.get_running_loop().run_in_executor(None,f,*args))
    runtime=Runtime()
    runtime.store=Store(tmp_path/"vzkazy")
    # Loopback allowed only in this test fixture; config flow rejects it.
    runtime.sources["dvere"]={"network":"127.0.0.0/8","key_digest":key_digest(KEY)}
    view=UploadView(hass,runtime)
    app=web.Application(client_max_size=16*1024*1024)
    app.router.add_post(view.url,view.post)
    return await aiohttp_client(app),runtime,events

async def test_success(setup_view):
    client,runtime,events=setup_view
    response=await client.post(UploadView.url,headers=HEADERS,data=b"\0\0"*16000)
    assert response.status==201
    saved=await response.json()
    assert saved["duration"]==1
    assert len(events)==1 and events[0][0]=="voice_inbox_saved"
    assert (runtime.store.root/"dvere"/saved["file"]).is_file()
    assert (await client.get(UploadView.url)).status==405

@pytest.mark.parametrize("changes,status",[
    ({"X-Voice-Key":"b"*64},401),({"X-Voice-Source":"../outside"},401),
    ({"X-Audio-Rate":"bad"},400),({"X-Audio-Rate":"44100"},415),
    ({"X-Forwarded-For":"127.0.0.1"},401),({"Content-Encoding":"identity","Content-Type":"text/plain"},415),
])
async def test_rejections(setup_view,changes,status,caplog):
    client,runtime,events=setup_view
    response=await client.post(UploadView.url,headers={**HEADERS,**changes},data=b"\0\0")
    assert response.status==status
    assert not events
    assert KEY not in caplog.text

async def test_cloud_blocked(setup_view,monkeypatch):
    client,_,events=setup_view
    monkeypatch.setattr("custom_components.voice_inbox.http.is_cloud_connection",lambda _:True)
    response=await client.post(UploadView.url,headers=HEADERS,data=b"\0\0")
    assert response.status==401 and not events

async def test_busy_and_failed_keys(setup_view):
    client,runtime,_=setup_view
    runtime.active.add("dvere")
    assert (await client.post(UploadView.url,headers=HEADERS,data=b"\0\0")).status==503
    runtime.active.clear()
    for _ in range(5):
        assert (await client.post(UploadView.url,headers={**HEADERS,"X-Voice-Key":"b"*64},data=b"\0\0")).status==401
    assert (await client.post(UploadView.url,headers=HEADERS,data=b"\0\0")).status==503

async def test_large_body(setup_view):
    client,_,events=setup_view
    response=await client.post(UploadView.url,headers=HEADERS,data=b"\0"*(8*1024*1024+1))
    assert response.status==413 and not events

@pytest.mark.parametrize("status",[503,507])
async def test_storage_failure(setup_view,monkeypatch,status):
    client,runtime,events=setup_view
    def fail(*args):
        raise Rejected(status,"storage_test_failure")
    monkeypatch.setattr(runtime.store,"save",fail)
    response=await client.post(UploadView.url,headers=HEADERS,data=b"\0\0")
    assert response.status==status and not events
    assert not runtime.active

async def test_source_key_binding(setup_view):
    client,runtime,events=setup_view
    runtime.sources["obyvak"]={"network":"127.0.0.0/8","key_digest":key_digest("b"*64)}
    response=await client.post(UploadView.url,headers={**HEADERS,"X-Voice-Source":"obyvak"},data=b"\0\0")
    assert response.status==401 and not events

async def test_wav_success_and_mismatch(setup_view):
    import io
    import wave
    client,_,events=setup_view
    raw=io.BytesIO()
    with wave.open(raw,"wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0"*160)
    headers={**HEADERS,"Content-Type":"audio/wav"}
    response=await client.post(UploadView.url,headers=headers,data=raw.getvalue())
    assert response.status==201 and len(events)==1
    response=await client.post(UploadView.url,headers={**headers,"X-Audio-Rate":"48000"},data=raw.getvalue())
    assert response.status==415 and len(events)==1
