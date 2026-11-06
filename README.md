# Telegram Assist

Talk to your Home Assistant **Assist** from Telegram: text and voice messages to your bot are
answered by an Assist assistant of your choice, its conversation agent and speech-to-text, the same
way a voice satellite is.

- **No external address needed.** The bot is the built-in
  [Telegram bot](https://www.home-assistant.io/integrations/telegram_bot/) integration in
  **Polling** mode; its allowed chats decide who may write.
- **Voice messages** are decoded by Home Assistant's ffmpeg and go through the assistant's
  speech-to-text and agent; the reply quotes what was heard.
- **One dialogue per chat**, so follow-up questions keep their context; `/new` starts a new one.
- **Who is who.** Map Telegram users to Home Assistant users: their messages are asked as that
  user, so agents (for example [FlowPilot](https://github.com/darkdarin/flowpilot)) know who is
  asking. Optionally answer mapped users only.
- **"typing…"** shows while the assistant thinks.

Works with any Assist conversation agent: the built-in one, an LLM integration or FlowPilot.

## Install

1. Set up the **Telegram bot** integration: **Settings → Devices & services → Add integration →
   Telegram bot**, platform **Polling**, your bot's token. Send `/start` to the bot and add your
   chat under **⋮ → Add allowed chat ID**.
2. Add this repository to HACS (**HACS → ⋮ → Custom repositories**,
   `https://github.com/darkdarin/ha-telegram-assist`, type **Integration**), install
   **Telegram Assist** and restart Home Assistant.
3. **Add integration → Telegram Assist**: pick the bot and the assistant that answers it.
4. In its options, map Telegram users to Home Assistant users (ask @userinfobot for your
   Telegram id).

Only one consumer may read a bot's messages: answer the bot with Telegram Assist and do not also
answer it with your own automations.

## Notes

- Voice messages are downloaded into Home Assistant's `telegram_bot` folder only for decoding
  and deleted right after.
- Answers come as text; replying with voice is planned.

## License

Apache-2.0.
