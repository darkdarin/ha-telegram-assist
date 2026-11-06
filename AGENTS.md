# AGENTS.md

**Telegram Assist** is a Home Assistant custom integration: messages of a Telegram bot (the
built-in `telegram_bot` integration) are answered by an Assist assistant. It belongs to the
FlowPilot family (`~/Projects/ha-flow-pilot`) but works with any Assist agent.

## Language

Everything in this repository is in **English**: code, comments, docs, commit messages. Research
and planning live in Notion (FlowPilot pages), in Russian.

## Design

- Build on public Home Assistant interfaces only: `telegram_bot` events (`telegram_text`,
  `telegram_attachment`, `telegram_command`) and actions (`send_message`, `send_chat_action`,
  `download_file`), `conversation.async_converse`, `assist_pipeline.async_pipeline_from_audio_stream`
  and the `ffmpeg` manager. Never poll Telegram ourselves: one bot has one reader.
- Answers are background tasks of the config entry; every failure is told in the chat.
- A Telegram user mapped to a Home Assistant user is asked as that user (`Context.user_id`).

## Environment

- Python 3.14, `uv`. The test environment is pinned to one Home Assistant release through
  `pytest-homeassistant-custom-component` (0.13.375 == 2026.10.4, the same as FlowPilot).
- Checks: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest -q -p no:logging` (ffmpeg must be installed). CI runs the same plus hassfest and
  HACS validation.

## Repository

- GitHub: `darkdarin/ha-telegram-assist` (to be created by the owner's decision), default branch
  `main`. Use the personal account per command: `GH_TOKEN="$(gh auth token --user darkdarin)" gh ...`;
  never run `gh auth switch`, never print tokens.
- Conventional Commits; the git author is configured locally.
- License: Apache-2.0.

## Rules

- Never commit secrets, bot tokens or voice recordings.
- Changes to the owner's live Home Assistant only with the owner's consent.
- Do not mark the integration done without a real end-to-end test with a Telegram bot.
