"""Telegram messages answered by Assist, in a real Home Assistant."""

from __future__ import annotations

import shutil
from unittest.mock import AsyncMock, patch

from .conftest import BOT, HEARD, FakeStt, Setup


async def test_a_text_message_is_answered_as_its_user(setup: Setup) -> None:
    await setup.message("привет")
    assert setup.telegram.texts == [f"{setup.user}|telegram-100|привет"]
    sent = setup.telegram.sent[0]
    assert sent["chat_id"] == 100 and sent["config_entry_id"] == BOT
    assert "typing" in setup.telegram.actions  # "typing…" while the agent thinks


async def test_each_chat_is_its_own_dialogue_until_new(setup: Setup) -> None:
    await setup.message("раз", chat=100)
    await setup.message("два", chat=200)
    await setup.command("/new", chat=100)
    await setup.message("три", chat=100)
    texts = setup.telegram.texts
    assert texts[0].endswith("|telegram-100|раз") and texts[1].endswith("|telegram-200|два")
    assert texts[2] == "🆕 A new dialogue."  # the test instance speaks English
    assert texts[3].endswith("|telegram-100-1|три")


async def test_unmapped_users_ask_as_nobody_or_are_ignored(setup: Setup) -> None:
    await setup.message("кто я", user=7)
    assert setup.telegram.texts == ["nobody|telegram-100|кто я"]
    options = dict(setup.entry.options) | {"only_known_users": True}
    setup.hass.config_entries.async_update_entry(setup.entry, options=options)
    await setup.message("а теперь", user=7)
    assert len(setup.telegram.sent) == 1  # ignored


async def test_other_bots_are_left_alone(setup: Setup) -> None:
    await setup.message("привет", bot="another-bot")
    assert setup.telegram.sent == []


async def test_a_voice_message_goes_through_speech_to_text(setup: Setup, fake_stt: FakeStt) -> None:
    """With ffmpeg installed (locally) the decoding is real; without it (CI) it is stood in for."""
    if shutil.which("ffmpeg"):
        await setup.voice()
    else:
        with patch(
            "custom_components.telegram_assist.bridge.decode_to_pcm",
            AsyncMock(return_value=bytes(2 * 16000)),
        ):
            await setup.voice()
    assert fake_stt.received == 2 * 16000  # one second of 16 kHz mono
    assert setup.telegram.texts == [f"🎤 {HEARD}\n\n{setup.user}|telegram-100|{HEARD}"]
    assert not setup.telegram.downloaded[0].exists()  # the downloaded file is removed


async def test_a_failure_is_told_in_the_chat(setup: Setup) -> None:
    setup.agent.fail = True
    await setup.message("привет")
    (reply,) = setup.telegram.texts
    assert reply.startswith("⚠️ The assistant could not answer:")
