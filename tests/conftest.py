"""A real Home Assistant with Assist, a fake agent and fake telegram_bot actions."""

from __future__ import annotations

import io
import wave
from collections.abc import AsyncIterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

import pytest
from homeassistant.components import conversation, stt
from homeassistant.components.assist_pipeline.pipeline import PipelineData
from homeassistant.components.conversation.models import AbstractConversationAgent
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import intent
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components

# The test harness puts its own ``custom_components`` package first on sys.path; add ours to it.
_OURS = str(Path(__file__).resolve().parents[1] / "custom_components")
if _OURS not in custom_components.__path__:
    custom_components.__path__.insert(0, _OURS)

BOT = "bot-entry"
HEARD = "включи свет"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> Iterator[None]:
    yield


class EchoAgent(AbstractConversationAgent):
    """Answers with who asked, in which dialogue, and what."""

    fail = False

    @property
    def supported_languages(self) -> Literal["*"]:
        return "*"

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        if self.fail:
            raise RuntimeError("the model is down")
        response = intent.IntentResponse(language=user_input.language)
        who = user_input.context.user_id or "nobody"
        response.async_set_speech(f"{who}|{user_input.conversation_id}|{user_input.text}")
        return conversation.ConversationResult(
            response=response, conversation_id=user_input.conversation_id
        )


class FakeStt(stt.SpeechToTextEntity):
    """Recognizes a fixed phrase; counts the audio it got."""

    entity_id = "stt.fake"

    def __init__(self) -> None:
        self.received = 0

    @property
    def supported_languages(self) -> list[str]:
        return ["ru", "en"]

    @property
    def supported_formats(self) -> list[stt.AudioFormats]:
        return [stt.AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[stt.AudioCodecs]:
        return [stt.AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[stt.AudioBitRates]:
        return [stt.AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[stt.AudioSampleRates]:
        return [stt.AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[stt.AudioChannels]:
        return [stt.AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: stt.SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> stt.SpeechResult:
        self.received = sum([len(chunk) async for chunk in stream])
        return stt.SpeechResult(HEARD, stt.SpeechResultState.SUCCESS)

    async def internal_async_process_audio_stream(  # type: ignore[misc]
        self, metadata: stt.SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> stt.SpeechResult:
        return await self.async_process_audio_stream(metadata, stream)  # no state to write


@dataclass
class Telegram:
    """Records what the integration asks telegram_bot to do."""

    tmp: Path
    sent: list[dict[str, Any]] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    downloaded: list[Path] = field(default_factory=list)

    async def send_message(self, call: ServiceCall) -> ServiceResponse:
        self.sent.append(dict(call.data))
        return None

    async def send_chat_action(self, call: ServiceCall) -> ServiceResponse:
        self.actions.append(str(call.data["chat_action"]))
        return None

    async def download_file(self, call: ServiceCall) -> ServiceResponse:
        path = self.tmp / f"{call.data['file_id']}.oga"
        out = io.BytesIO()
        with wave.open(out, "wb") as w:  # ffmpeg reads it whatever the extension says
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(bytes(2 * 48000))  # one second
        path.write_bytes(out.getvalue())
        self.downloaded.append(path)
        return {"file_path": str(path)}

    @property
    def texts(self) -> list[str]:
        return [str(m["message"]) for m in self.sent]


@dataclass
class Setup:
    hass: HomeAssistant
    entry: MockConfigEntry
    telegram: Telegram
    agent: EchoAgent
    stt: FakeStt
    user: str

    async def message(self, text: str, user: int = 42, chat: int = 100, bot: str = BOT) -> None:
        data = {"chat_id": chat, "user_id": user, "text": text, "bot": {"config_entry_id": bot}}
        self.hass.bus.async_fire("telegram_text", data)
        await self.hass.async_block_till_done(wait_background_tasks=True)

    async def voice(self, user: int = 42, chat: int = 100) -> None:
        data = {
            "chat_id": chat,
            "user_id": user,
            "file_id": "voice1",
            "file_mime_type": "audio/ogg",
            "file_size": 4000,
            "bot": {"config_entry_id": BOT},
        }
        self.hass.bus.async_fire("telegram_attachment", data)
        await self.hass.async_block_till_done(wait_background_tasks=True)

    async def command(self, command: str, chat: int = 100) -> None:
        data = {
            "chat_id": chat,
            "user_id": 42,
            "command": command,
            "args": [],
            "bot": {"config_entry_id": BOT},
        }
        self.hass.bus.async_fire("telegram_command", data)
        await self.hass.async_block_till_done(wait_background_tasks=True)


@pytest.fixture
async def setup(hass: HomeAssistant, tmp_path: Path) -> Setup:
    for component in ("homeassistant", "conversation", "assist_pipeline", "ffmpeg"):
        assert await async_setup_component(hass, component, {})
    telegram = Telegram(tmp_path)
    for name in ("send_message", "send_chat_action", "download_file"):
        hass.services.async_register(
            "telegram_bot",
            name,
            getattr(telegram, name),
            supports_response=SupportsResponse.OPTIONAL,
        )
    agent_entry = MockConfigEntry(domain="test_agent")
    agent_entry.add_to_hass(hass)
    agent = EchoAgent()
    conversation.async_set_agent(hass, agent_entry, agent)
    data: PipelineData = hass.data["assist_pipeline"]
    pipeline = await data.pipeline_store.async_create_item(
        {
            "name": "Telegram",
            "language": "ru",
            "conversation_engine": agent_entry.entry_id,
            "conversation_language": "ru",
            "stt_engine": "stt.fake",
            "stt_language": "ru",
            "tts_engine": None,
            "tts_language": None,
            "tts_voice": None,
            "wake_word_entity": None,
            "wake_word_id": None,
        }
    )
    user = await hass.auth.async_create_user("Pavel")
    entry = MockConfigEntry(
        domain="telegram_assist",
        data={"bot_entry_id": BOT},
        options={"pipeline": pipeline.id, "users": {"42": user.id}},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return Setup(hass, entry, telegram, agent, FakeStt(), user.id)


@pytest.fixture
def fake_stt(setup: Setup) -> Iterator[FakeStt]:
    original = stt.async_get_speech_to_text_entity

    def get(hass: HomeAssistant, entity_id: str) -> Any:
        return setup.stt if entity_id == "stt.fake" else original(hass, entity_id)

    with patch.object(stt, "async_get_speech_to_text_entity", side_effect=get):
        yield setup.stt
