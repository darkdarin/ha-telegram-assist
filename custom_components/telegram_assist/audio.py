"""Voice messages to the PCM speech-to-text takes, with Home Assistant's own ffmpeg."""

from __future__ import annotations

import asyncio
from pathlib import Path

from homeassistant.components.ffmpeg import get_ffmpeg_manager
from homeassistant.core import HomeAssistant

DECODE_TIMEOUT_S = 30.0


async def decode_to_pcm(hass: HomeAssistant, path: Path, sample_rate: int) -> bytes:
    """Mono 16-bit PCM at ``sample_rate`` from any audio ffmpeg reads (Telegram: OGG/Opus)."""
    process = await asyncio.create_subprocess_exec(
        get_ffmpeg_manager(hass).binary,
        "-nostdin",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "pipe:1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        async with asyncio.timeout(DECODE_TIMEOUT_S):
            pcm, errors = await process.communicate()
    except TimeoutError:
        process.kill()
        await process.wait()
        raise
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg could not decode the voice message: {errors.decode()[:300]}")
    return pcm
