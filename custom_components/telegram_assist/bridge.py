"""Messages of a Telegram bot answered by an Assist assistant.

The ``telegram_bot`` integration receives the messages (long polling works without an external
address) and keeps the allowed chats; this integration listens to its events, answers through the
chosen Assist assistant and replies with ``telegram_bot`` actions:

- text messages go to the assistant's conversation agent;
- voice messages are downloaded, decoded by Home Assistant's ffmpeg and run through the
  assistant's speech-to-text and agent, like a satellite's command;
- each chat is one dialogue (``conversation_id``) until someone sends ``/new``;
- a Telegram user mapped to a Home Assistant user asks as that user, so agents (and FlowPilot)
  know who is asking;
- while the assistant thinks, the chat shows "typing…".
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Callable, Mapping
from pathlib import Path
from typing import Any

from homeassistant.components import assist_pipeline, conversation, stt
from homeassistant.components.assist_pipeline.models import PipelineStage
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, Event, HomeAssistant, callback

from .audio import decode_to_pcm
from .const import (
    COMMAND_NEW,
    CONF_BOT,
    CONF_ONLY_KNOWN,
    CONF_PIPELINE,
    CONF_SHOW_HEARD,
    CONF_USERS,
    EVENT_ATTACHMENT,
    EVENT_COMMAND,
    EVENT_TEXT,
    MAX_VOICE_BYTES,
    TELEGRAM,
    TYPING_EVERY_S,
    VOICE_MIME_TYPES,
)
from .texts import text as say

_LOGGER = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHUNK_BYTES = SAMPLE_RATE * 2 // 50  # 20 ms, as satellites stream


class AssistBridge:
    """Answers one bot's messages with one assistant."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._unsubscribe: list[Callable[[], None]] = []
        self._tasks: set[asyncio.Task[None]] = set()
        self._dialogues: dict[int, int] = {}  # chat id -> how many times /new was sent

    @property
    def options(self) -> Mapping[str, Any]:
        return {**self.entry.data, **self.entry.options}

    @property
    def bot(self) -> str:
        return str(self.options[CONF_BOT])

    def start(self) -> None:
        for event_type, handler in (
            (EVENT_TEXT, self._on_text),
            (EVENT_ATTACHMENT, self._on_attachment),
            (EVENT_COMMAND, self._on_command),
        ):
            self._unsubscribe.append(self.hass.bus.async_listen(event_type, handler))

    async def stop(self) -> None:
        for unsubscribe in self._unsubscribe:
            unsubscribe()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    # --- events ---------------------------------------------------------------------------------

    def _ours(self, event: Event) -> bool:
        bot = event.data.get("bot") or {}
        return bot.get("config_entry_id") == self.bot

    def _asker(self, event: Event) -> Context | None:
        """The context to ask in: as the mapped Home Assistant user; ``None``: do not answer."""
        users: Mapping[str, str] = self.options.get(CONF_USERS) or {}
        user = users.get(str(event.data.get("user_id")))
        if user is None and self.options.get(CONF_ONLY_KNOWN):
            return None
        return Context(user_id=user)

    @callback
    def _on_text(self, event: Event) -> None:
        text = str(event.data.get("text") or "").strip()
        if self._ours(event) and text:
            self._spawn(int(event.data["chat_id"]), self._answer_text(event, text))

    @callback
    def _on_attachment(self, event: Event) -> None:
        mime = str(event.data.get("file_mime_type") or "")
        if self._ours(event) and mime in VOICE_MIME_TYPES:
            self._spawn(int(event.data["chat_id"]), self._answer_voice(event))

    @callback
    def _on_command(self, event: Event) -> None:
        if self._ours(event) and event.data.get("command") == COMMAND_NEW:
            chat = int(event.data["chat_id"])
            self._dialogues[chat] = self._dialogues.get(chat, 0) + 1
            self._spawn(chat, self._send(chat, say("new", self.hass.config.language), Context()))

    def _spawn(self, chat: int, coro: Any) -> None:
        task = self.entry.async_create_background_task(
            self.hass, self._reporting(chat, coro), "telegram assist turn"
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _reporting(self, chat: int, coro: Any) -> None:
        """Run an answer; if it fails, say so in the chat instead of keeping silent."""
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001 - every failure is reported to the chat
            _LOGGER.warning("Telegram Assist could not answer: %s", err, exc_info=True)
            error = str(err) or type(err).__name__
            with contextlib.suppress(Exception):
                await self._send(
                    chat, say("failed", self.hass.config.language, error=error), Context()
                )

    # --- answering ------------------------------------------------------------------------------

    def _conversation_id(self, chat: int) -> str:
        # Home Assistant keeps ids that are not ULIDs as they are: one dialogue per chat
        generation = self._dialogues.get(chat, 0)
        return f"telegram-{chat}" + (f"-{generation}" if generation else "")

    def _pipeline(self) -> assist_pipeline.Pipeline:
        wanted = self.options.get(CONF_PIPELINE)
        pipelines = assist_pipeline.async_get_pipelines(self.hass)
        return next((p for p in pipelines if p.id == wanted), None) or next(iter(pipelines))

    async def _answer_text(self, event: Event, text: str) -> None:
        chat = int(event.data["chat_id"])
        if (context := self._asker(event)) is None:
            return
        pipeline = self._pipeline()
        async with self._typing(chat, context):
            result = await conversation.async_converse(
                self.hass,
                text,
                self._conversation_id(chat),
                context,
                language=pipeline.conversation_language,
                agent_id=pipeline.conversation_engine,
            )
        await self._send(chat, _speech(result.response.as_dict()), context)

    async def _answer_voice(self, event: Event) -> None:
        chat = int(event.data["chat_id"])
        if (context := self._asker(event)) is None:
            return
        if int(event.data.get("file_size") or 0) > MAX_VOICE_BYTES:
            await self._send(chat, say("too_long", self.hass.config.language), context)
            return
        async with self._typing(chat, context):
            path = await self._download(str(event.data["file_id"]), context)
            try:
                pcm = await decode_to_pcm(self.hass, path, SAMPLE_RATE)
            finally:
                await self.hass.async_add_executor_job(path.unlink, True)
            heard, answer = await self._run_pipeline(pcm, chat, context)
        if not heard:
            await self._send(chat, say("not_heard", self.hass.config.language), context)
            return
        quote = f"🎤 {heard}\n\n" if self.options.get(CONF_SHOW_HEARD, True) else ""
        await self._send(chat, quote + answer, context)

    async def _run_pipeline(self, pcm: bytes, chat: int, context: Context) -> tuple[str, str]:
        """Speech-to-text and agent of the assistant, like a satellite's command."""
        events: list[assist_pipeline.PipelineEvent] = []

        async def audio() -> AsyncIterator[bytes]:
            for start in range(0, len(pcm), CHUNK_BYTES):
                yield pcm[start : start + CHUNK_BYTES]

        await assist_pipeline.async_pipeline_from_audio_stream(
            self.hass,
            context=context,
            event_callback=events.append,
            stt_metadata=stt.SpeechMetadata(
                language=self._pipeline().stt_language or self.hass.config.language,
                format=stt.AudioFormats.WAV,
                codec=stt.AudioCodecs.PCM,
                bit_rate=stt.AudioBitRates.BITRATE_16,
                sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
                channel=stt.AudioChannels.CHANNEL_MONO,
            ),
            stt_stream=audio(),
            pipeline_id=self._pipeline().id,
            conversation_id=self._conversation_id(chat),
            start_stage=PipelineStage.STT,
            end_stage=PipelineStage.INTENT,
        )
        heard = answer = ""
        for event in events:
            data = event.data or {}
            if event.type == assist_pipeline.PipelineEventType.STT_END:
                heard = str(data.get("stt_output", {}).get("text") or "")
            elif event.type == assist_pipeline.PipelineEventType.INTENT_END:
                answer = _speech(data.get("intent_output", {}).get("response") or {})
            elif event.type == assist_pipeline.PipelineEventType.ERROR:
                _LOGGER.warning("Assist could not answer a voice message: %s", data)
                answer = answer or f"⚠️ {data.get('message') or data.get('code')}"
        return heard, answer

    async def _download(self, file_id: str, context: Context) -> Path:
        """The voice message, in telegram_bot's own folder (no allowlist needed)."""
        response = await self.hass.services.async_call(
            TELEGRAM,
            "download_file",
            {"config_entry_id": self.bot, "file_id": file_id},
            blocking=True,
            return_response=True,
            context=context,
        )
        path = (response or {}).get("file_path")
        if not path:
            raise RuntimeError(f"telegram_bot did not download {file_id}: {response}")
        return Path(str(path))

    async def _send(self, chat: int, text: str, context: Context) -> None:
        await self.hass.services.async_call(
            TELEGRAM,
            "send_message",
            {
                "config_entry_id": self.bot,
                "chat_id": chat,
                "message": text,
                "parse_mode": "plain_text",
            },
            blocking=True,
            context=context,
        )

    @contextlib.asynccontextmanager
    async def _typing(self, chat: int, context: Context) -> AsyncIterator[None]:
        """Show "typing…" right away and keep it while the assistant works."""

        async def show() -> None:
            with contextlib.suppress(Exception):  # cosmetic: never fail an answer over it
                await self.hass.services.async_call(
                    TELEGRAM,
                    "send_chat_action",
                    {"config_entry_id": self.bot, "chat_id": chat, "chat_action": "typing"},
                    blocking=True,
                    context=context,
                )

        async def keep() -> None:
            while True:
                await asyncio.sleep(TYPING_EVERY_S)
                await show()

        await show()
        task = asyncio.create_task(keep())
        try:
            yield
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def _speech(response: Mapping[str, Any]) -> str:
    """What the assistant said: the plain speech of an intent response."""
    speech = response.get("speech") or {}
    text = (speech.get("plain") or {}).get("speech") or ""
    return str(text).strip() or "…"
