# Changelog

## 0.1.2

- The assistant's Markdown is shown formatted in Telegram (bold, italic, code, links, quotes,
  headings and lists) instead of raw; if Telegram rejects the formatting, the answer is sent as
  plain text.

## 0.1.1

- Mapping a Telegram user to a Home Assistant user offers the people of the bot's allowed chats
  by name; any other Telegram user id can still be typed in. Removing mappings shows the names.

## 0.1.0

- First release: messages of a Telegram bot (the built-in Telegram bot integration) answered by an
  Assist assistant. Text goes to its conversation agent; voice messages are decoded by Home
  Assistant's ffmpeg and run through its speech-to-text and agent, and the reply quotes what was
  heard.
- One dialogue per chat; `/new` starts a new one.
- Telegram users can be mapped to Home Assistant users: they are asked as that user, so agents
  (such as FlowPilot) know who is asking; optionally only mapped users are answered.
- "typing…" while the assistant thinks; failures are told in the chat. English and Russian.
