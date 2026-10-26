"""Flow unit tests using HA's real class; not a full HA lifecycle/UI test."""
from unittest.mock import AsyncMock, Mock
from custom_components.voice_inbox.config_flow import VoiceInboxConfigFlow
from custom_components.voice_inbox.storage import key_digest

async def test_entry_stores_digest_only():
    flow=VoiceInboxConfigFlow()
    flow._async_current_entries=Mock(return_value=[])
    flow.async_set_unique_id=AsyncMock()
    flow._abort_if_unique_id_configured=Mock()
    flow.async_create_entry=Mock(side_effect=lambda **kw:kw)
    result=await flow.async_step_user({"source":"dvere","network":"192.168.0.0/24","key":"a"*64})
    assert "key" not in result["data"]
    assert result["data"]["key_digest"]==key_digest("a"*64)
    flow._abort_if_unique_id_configured.assert_called_once()

async def test_invalid_input():
    flow=VoiceInboxConfigFlow()
    flow.async_show_form=Mock(side_effect=lambda **kw:kw)
    result=await flow.async_step_user({"source":"../bad","network":"0.0.0.0/0","key":"short"})
    assert set(result["errors"])=={"source","network","key"}
