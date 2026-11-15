<div align="center">

<img src="../img/brand/logo.svg" width="72" alt="Mnemai">

# Mnemai guide

How Mnemai works, screen by screen and setting by setting. Mnemai answers questions about itself from this same text.

<sub><b>English</b> · <a href="ru.md">Русский</a> · <a href="zh.md">中文</a> · <a href="es.md">Español</a> · <a href="hi.md">हिन्दी</a> · <a href="pt.md">Português</a> · <a href="fr.md">Français</a> · <a href="de.md">Deutsch</a> · <a href="ja.md">日本語</a></sub>

<sub><a href="../../README.md">README</a></sub>

</div>

## Contents

- [What is Mnemai](#what-is-mnemai)
- [Memory On or Off](#memory-on-or-off)
- [Memory folder](#memory-folder)
- [Additional memory folders](#additional-memory-folders)
- [How a fact is recorded](#how-a-fact-is-recorded)
- [Memory tab](#memory-tab)
- [Portrait](#portrait)
- [Summary of 10 Now and the table of contents](#summary-of-10-now-and-the-table-of-contents)
- [How Mnemai learns](#how-mnemai-learns)
- [Learning sources](#learning-sources)
- [Learning modes](#learning-modes)
- [How Mnemai understands text](#how-mnemai-understands-text)
- [How Mnemai decides: save or ask](#how-mnemai-decides-save-or-ask)
- [Learning Feed and Questions in Conversation](#learning-feed-and-questions-in-conversation)
- [Chat and Models](#chat-and-models)
- [Sessions](#sessions)
- [How she replies](#how-she-replies)
- [What the model knows in every message](#what-the-model-knows-in-every-message)
- [Files and documents, including PDF](#files-and-documents-including-pdf)
- [Internet](#internet)
- [More accurate or more economical](#more-accurate-or-more-economical)
- [Questions as buttons, second pass, quoting](#questions-as-buttons-second-pass-quoting)
- [Recurring tasks](#recurring-tasks)
- [Term Hints](#term-hints)
- [Consortium](#consortium)
- [Computer Actions](#computer-actions)
- [Administrator Password](#administrator-password)
- [Conversation without learning](#conversation-without-learning)
- [Voice and meetings](#voice-and-meetings)
- [Built-in model on your computer](#built-in-model-on-your-computer)
- [Engine: tokens and load](#engine-tokens-and-load)
- [Who Sees What](#who-sees-what)
- [What leaves your computer](#what-leaves-your-computer)
- [Encrypt your memory with a password](#encrypt-your-memory-with-a-password)
- [History and rollback](#history-and-rollback)
- [Connecting Other AIs](#connecting-other-ais)
- [Proxy and VPN](#proxy-and-vpn)
- [Window, tray, installation](#window-tray-installation)
- [The gear, theme, language, achievements](#the-gear-theme-language-achievements)
- [Multiple memories](#multiple-memories)
- [Telegram](#telegram)
- [The "Memory" card at the bottom left](#the-memory-card-at-the-bottom-left)
- [What Mnemai can't do](#what-mnemai-cant-do)

## What is Mnemai

Mnemai is a memory app for any AI. It remembers who you are, what you're working on, what decisions you've made and how to talk to you, and brings that into your conversations with any model: Claude, ChatGPT, Gemini, the built-in model on your computer, Cursor and agents. Your memory is a folder of plain Markdown files on your computer, and you can open it in any editor (including Obsidian) even without Mnemai. Mnemai has no cloud and no account. The app is a single window (chat, memory, settings) and an icon in the system tray (in the menu bar on macOS). It runs on Windows 10 and 11, macOS 11 and later (Apple Silicon and Intel), and Linux (64-bit, Ubuntu 22.04 and later and similar distributions). The personal version is free and open source (AGPL-3.0 license); the company version is separate.

## Memory On or Off

Memory is Mnemai's main switch: a toggle in the "Memory" panel at the bottom left of the chat (the same one is in Settings → Learning → "Memory"). While memory is off, the dot on the gear icon at the top right is yellow. A new memory created on the first screen starts out turned off: the tutorial has a "Turn on memory?" step (the default is "No memory"), and if the tutorial wasn't shown, the same question appears in a separate window. Memory that existed before the switch was introduced stays on.

When it's off, it's a regular chat with any AI: the model knows nothing about you, Mnemai doesn't remember anything (learning doesn't run, "remember" doesn't save anything, the "save to memory" action is refused), and Claude Code, Claude Desktop and Cursor can't get memory or write to it. Everything else works: any models, the consortium, documents and the token savings on them, the internet, meetings, local models, file actions in working folders (the memory folder is closed to actions). The "Memory" tab shows a "Memory is off" screen with the buttons "Turn on memory" and "View saved entries". The learning settings and "Who sees what" are dimmed with a "Memory is off" label and a "Turn on" button, the "No learning" button in the chat is inactive, and the status bar reads "Memory is off · regular chat, nothing is remembered".

## Memory folder

Your memory lives in the folder you chose on first launch. Inside:

| Folder or file | What's in it |
|---|---|
| 00 Inbox/Inbox.md | unsorted facts |
| 10 Now.md | summary for today: who you are, active projects, recent events, fresh facts from the last 14 days, statuses older than 30 days to review. Built automatically, don't edit by hand |
| 20 Projects/<name>/_Project.md | project hub: status (active, paused, closed), goal, start date, keywords, log. Project documents sit next to it |
| 30 People/<name>.md | a person's card |
| 60 Events/YYYY-MM.md | decisions and status changes by month, newest on top |
| 70 Memory/Profile.md | who you are |
| 70 Memory/Rules.md | how to work with you, one rule per line with a date |
| 70 Memory/Thoughts.md | your thoughts and ideas |
| 70 Memory/Cards/<topic>.md | topic card: one fact per line, keywords and hidden tags in the header |
| 70 Memory/Fact archive/ | facts replaced by newer ones. This is history, models don't receive it |
| 70 Memory/Index.md | table of contents: projects, cards and people with keywords. Built automatically |
| 80 Meetings/ | meeting recordings, transcripts and summaries |
| 90 System/Journal/<day>.md | journal: what was recorded and by whom, in plain language |
| 90 System/Recipes/ | recipes for recurring tasks |
| 95 Saves/ | a copy of a file before its first edit of the day, the last two are kept |
| 99 Archive/ | closed projects along with their documents |
| .mnema/ | internal: AI access, edit log, rollback snapshots, tokens, learning settings, conversations |

You can edit the memory files by hand. Mnemai only reads this structure.

## Additional memory folders

Settings → App → "Additional memory folders": other folders that AI can see along with the main memory. Any folder works: notes, an Obsidian vault, documents, a shared team folder, or another Mnemai memory. The "Connect Obsidian" button finds Obsidian vaults on your computer by itself (from Obsidian's own settings) and shows them with the number of notes: the ones you check become additional memory, and you can also specify a folder manually. Any other folder is added with the "Add" button (or "Choose…"), and removed with "Remove" next to it. A vault is read in full once in the background, and after that only changed notes are re-read, so even thousands of notes don't slow down answers. Markdown and text files are read on your computer, and only the relevant passages are sent along with your question, within the same size limit as the memory (the "More precise ↔ More economical" slider). Topics hidden from that AI (#money, #health, #private and their Russian forms) are cut out of these files too. Mnemai doesn't write anything to these folders and doesn't learn from them.

## How a fact is recorded

One fact is one line with a date: "- 21.09.2026 · We decided to launch the pilot in November". A status is written with the note "(status DD.MM.YYYY)". A new status for the same subject replaces the old one in place, the old one moves to the facts archive, and the change goes into the event feed. Anything Mnemai has learned on her own is marked with the word "learned", so you can see what came from training.

The date on a learned fact is the day you said or wrote it, not the day Mnemai read it. If Mnemai reads a month-old conversation today, the fact gets the date of that conversation, and the decision lands in that month's events. This way old information isn't passed off as news.

Mnemai doesn't put statuses older than 30 days into a separate list. The model knows the date of each status: if a conversation touches on a status older than a month, it says what date it's from and checks whether it's still valid.

## Memory tab

Memory → Portrait: at the top is your portrait with fact counters, and below it is the "Memory map" — topics as bubbles around you. Bubble size reflects the number of facts, a lock marks topics that not every AI can see, and anything updated in the last three days pulses. The label of a small bubble appears when you hover over it. Below the map are topic tiles: "Rules for AI", "Projects", "People around you", the portrait sections, topic cards (largest first) and "Events and decisions". Each tile shows the number of facts and the two most recent lines (for projects and people, the first names). Click a tile or a bubble to open the topic in an overlay window: all facts, one line per fact, newest at the top, date on the right, search, and a click expands a fact in full; for learned facts there's also "Where from?" in the same place, and the pencil opens the file. Identical portrait sections (for example, the open and hidden "Who I am") are shown as one topic.

## Portrait

The portrait is 2–3 sentences at the start of 70 Memory/Profile.md: who you are, what you do, and what matters most to you right now. Every AI gets it first. Mnemai builds the portrait on her own once she knows at least three facts about you: from the open sections of your profile, active projects, and cards without hidden tags (money, health, and personal details never make it into the portrait). It's written by the model you chose for learning, and if there's no model, it's just the facts as short sentences. The portrait is rebuilt after learning: right away if your profile changed, and no more than once every 6 hours if only cards and projects changed. If you rewrite the portrait yourself, Mnemai won't touch it anymore. The build shows up in the log as "built the portrait" and can be rolled back in the history.

## Summary of 10 Now and the table of contents

Mnemai rebuilds 10 Now.md and 70 Memory/Index.md on her own after every write. 10 Now covers who you are, your active projects, recent events, fresh facts from the last 14 days (no more than 12) and outdated statuses. The table of contents lists every project, card and person along with the words you can use to search for them. Editing these files by hand is pointless: your changes will be lost the next time they're rebuilt.

## How Mnemai learns

Mnemai learns on her own as you go about your life. There are no questionnaires or forms to fill out. It picks up facts from the sources you've allowed and decides whether to save them right away or ask you first. Learning runs in the background on a timer (how often depends on the engine mode: from every 10 minutes to every 2 hours) and instantly on every message you send in the Mnemai chat. On first launch, it looks through your history for the last 90 days.

On first launch, Mnemai asks: "Allow Mnemai to look at other programs?". "No, only Mnemai" — it learns only from your conversations with it and your corrections in them, and works only with its own memory folder: it doesn't read Claude Code chats, notes, documents, Telegram, the browser or the extension. "Yes, I'll choose what" — a list of what was found on your computer opens (Claude Code chats, a notes folder, Documents, a Telegram export, browser history, the extension) with paths, with nothing checked, and Mnemai reads only what you check. It never turns on email or calendar by itself: those need an address and password or a secret link.

All of this can be changed in Settings → Learning. "What Mnemai can look at" is the main switch, "Other programs and browser": when it's off, the tiles for external sources are locked and can't be turned on. Below that, under "Where to learn", each source is turned on separately, and for some you can set a path and exclusions.

Mnemai never reads its own memory folder or its own internal model calls.

## Learning sources

| Source | What it reads |
|---|---|
| Conversations in Mnemai | your messages in the Mnemai chat, instantly, as you type |
| Conversations in Claude Code | your messages from the Claude Code history (the ~/.claude/projects folder), new lines only. Service requests from scripts with a label like "[SERVICE-NAME]" at the beginning are skipped |
| ChatGPT export | the conversations.json file from your ChatGPT data export |
| Your corrections | "no, not like that", "I told you before", "never…" in conversations with AI become rules for all AIs |
| Notes folder | new lines in your notes, for example in an Obsidian vault. System folders (.obsidian, .trash, .git) are excluded |
| Email | your sent emails via IMAP, with quoted text trimmed |
| Telegram (conversations via API) | the full conversation — your messages and those of the people you chat with — only in the chats you've selected. Read-only, see the "Telegram" section for details |
| Telegram (export) | your own messages from a Telegram Desktop export |
| Calendar | an .ics file or a secret iCal link |
| Documents | new and changed Word documents, texts and notes in the selected folder (.docx, .txt, .md) |
| Browser history | titles of pages you've read, by day (Chrome, Edge, Yandex Browser). Observe-only by default |

## Learning modes

The mode is set per source:

| Mode | What happens |
|---|---|
| Observe only | shows what it would learn, writes nothing |
| Ask for everything | writes nothing on its own: in a Mnemai conversation it asks, from other places it only shows |
| Mixed (default) | writes confident facts on its own. Personal facts and ones that contradict memory, when they come from a Mnemai conversation, it checks with a question right in the conversation; from other places it decides on its own. Weak guesses wait for a repeat |
| Do everything | writes everything; the safety net is the log and rollback |

If a fact shows up in several sources, the most cautious of their modes applies.

## How Mnemai understands text

Mnemai can parse ordinary speech in different ways ("Settings" → "Learning" → "How to understand text"):

| Option | How it works |
|---|---|
| Mnemai herself (default) | uses the model you talk to by default — any connected one, cloud-based or on your computer; if none is connected, only explicit signals are picked up |
| No model | explicit cues only: "remember …", corrections, decisions ("decided …"), status dates |
| Claude via subscription | through an installed Claude Code, without tools, hooks or MCP; the session is not saved |
| Your own key | Anthropic or OpenAI-compatible; the key is kept in your system's secure storage (Windows — DPAPI, macOS — Keychain, Linux — password store, if there is one), not in the memory folder |
| Model on your computer | built-in or Ollama, nothing leaves your computer |

Before text is sent to a cloud model, secrets are replaced with placeholders (see "What leaves your computer").

## How Mnemai decides: save or ask

- The default confidence threshold is 80%. At 80% or above, and if the fact isn't personal, Mnemai saves it on her own. Between 60% and 80%, it asks you. Below 60%, it waits until it comes across the fact again.
- Repetition raises confidence: two sightings at 60% each add up to 84%, and the fact is saved.
- Money, health, and personal matters go into a card tagged #money, #health, or #private: you can hide it from any AI in the "Who sees what" table. If it comes up in a conversation inside Mnemai, it will first ask right there: "This is personal — remember it?".
- Memory contradiction ("lives in Kazan" vs. "from Yekaterinburg"): in a conversation inside Mnemai, the question appears right there ("It's different now", "It was correct", "Both are true"); from other places, the new fact replaces the old one, and if the old line said more, Mnemai rewrites it while keeping the rest. The previous version goes to the fact archive.
- "Never learn things like this" adds a stop phrase. Rolling back a learned entry in the history means "no": it won't come back.
- There is no "waiting for you" queue: Mnemai doesn't pile up questions. No more than one question about memory is shown under a conversation at a time; the next one appears after you answer.

## Learning Feed and Questions in Conversation

The "I'm learning from you" feed (gear icon → "Feed") shows what Mnemai has read, what it understood and why it decided what it did, for example "confidence 90% at a threshold of 80%, not personal — saved on its own" or "this is about money — saved to the hidden part". If the memory needs your input, a "Quick question for memory" card with buttons appears below the conversation; your answer is saved right away. Every learned line has a "How do I know this?" option: the source, your own words, how many times it came up, and why it was saved.

## Chat and Models

Mnemai is a chat with any model, all models are equal. Model selection is in the upper left of the chat, the menu has two groups:

- Cloud — work over the internet: by key (Anthropic, OpenAI, Gemini, OpenRouter, DeepSeek, YandexGPT; Mnemai gets the model list from the provider, for YandexGPT — from the Yandex Cloud AI Studio catalog) or by subscription (Claude Code);
- On computer — free, no internet, nothing leaves your machine: built-in model (llama.cpp), Ollama and Strata.

When connecting and on "Check" Mnemai asks each model from the ChatGPT, Gemini, DeepSeek and YandexGPT lists with one short request and keeps only those that respond in chat: deprecated models (e.g. o4-mini, gpt-4, o1), models for audio, images and voice, and models for a different API only in the standard OpenAI catalog (pro, codex) don't make the list. If a provider deprecates a model later, it's removed from the list on the first rejection, and the chat shows a message to select another. DeepSeek connects with a key from platform.deepseek.com. YandexGPT — with a Yandex Cloud AI Studio service account API key (ai.languageModels.user role) and the folder ID where it was created: the connection window has two fields. YandexGPT models: Alice AI LLM, YandexGPT Pro 5.1, YandexGPT Pro 5, Alice AI LLM Flash, as well as DeepSeek V4.1 Flash and Qwen3.6 35B from the same catalog. Strata is a separate free program for large models (Qwen, DeepSeek) on your GPU (github.com/Niko1221/Strata): install it, launch a model with the strata launch command — Mnemai automatically finds running Strata at 127.0.0.1:8080 on startup; a different address can be set in the Strata connection window.

The same two groups are in Settings → AI and Models. The response length limit (Settings → Engine) is the same for all models, including Claude by subscription.

Memory and your rules are applied to each message, each model receives only what it's allowed to see. Each conversation has a 1–3 word title. You can change it with the pencil next to the title, double-clicking the title, or in the conversation menu in the list (Enter to save, Escape to cancel). In a new conversation you can set the title before the first message, it will be saved with it. Once manually renamed, Mnemai no longer changes the title, last modified time, or tokens spent. The list sorts by date or tokens, the "AI" filter shows conversations with one model.

The "Let Mnemai start" button in an empty conversation: the model greets you and suggests what to start with, based on memory. It calls events recent only if their date says so, and suggests checking decisions older than a month.

## Sessions

The "New session" button sits in the header of the list, below "New chat". A session is all the chats you started after the last time you pressed it: "New chat" opens a chat in the current session, while "New session" starts a new group. In the list, chats from the same session are joined by a line on the left, and each group has a label with the number of chats on the right: the top one is "Current session", past ones are "Session · Oct 24" (the day of the last chat). Click the label to collapse the group; the collapsed state is remembered. Right after "New session" there is no empty row: the top group stays "Current session" until the first chat appears in the new one. Next to the label there is a ⋮ menu: "Rename" (give the group your own name) and "Delete" (the session along with its chats; pinned ones stay, and what was learned stays in memory). Chats started before sessions existed form a separate session at the end of the list, and pinned chats sit at the top, outside the groups. When you search, sort by tokens or group by days, the list is plain, without sessions.

Next to the buttons there is a "?": an animation shows why staying in one chat for a long time is expensive, and how a new chat differs from a new session.

Each chat sends the model only its own history. That's why a chat in a new session starts with a clean context: the model gets the memory and the rules, but not the conversation from previous chats. A long chat sends more and more history with every reply, so it's cheaper to start a new topic in a new chat or a new session — Mnemai has already saved what you need from the past to memory.

When a single reply costs three times as much as the first reply from the same model in that chat (input tokens including cache, plus the reply), a "This chat has become expensive" card appears below it (it doesn't appear for a free model running on your computer): two bars — the first and the last reply — and how many times more expensive it is. The "Update memory and start a new session" button first learns from the whole chat in one pass, then starts a new session with a clean context. A message that was already learned earlier isn't counted as a repeat. In a chat without learning, the button simply starts a new session. "Don't show again" turns the tip off completely; to bring it back, use the gear ("Expensive chat tip"). The X on the card hides it only in that chat.

## How she replies

Go to Settings → "How it replies": name, form of address (informal or formal), reply length (short, to the point, detailed), gender — for word endings (прав or права), and personality. All the choices are tiles, and on the right is a "Sample reply": the same question about the pilot, and the reply changes instantly as you change the settings, with the name updating as you type. The personalities — Gentle, Businesslike, Strict with checks — are medals with a scale of checks from one to three. Below are the presets and detailed rules by group.

## What the model knows in every message

Before answering, the model receives:
- how to work with you: the rules from the "How it replies" section (personality, how it addresses you, your own words);
- the memory this model is allowed to see (the head of the memory and the lines relevant to your question);
- details about how Mnemai is currently set up: where it learns, in which mode, what she uses to understand texts, how many entries are in the memory;
- today's date;
- for questions about Mnemai itself: the relevant sections of this knowledge base.

The model answers as Mnemai and says only what Mnemai can do when it talks about its capabilities. The capabilities of the engine it runs on (for example, Claude Code's tools) don't belong to Mnemai.

## Files and documents, including PDF

Attach a file with the paperclip below the input field, or drag it into the window. One file can be up to 25 MB. Mnemai saves it alongside the conversation and extracts the text herself, on your computer and for free.

| Format | What Mnemai does |
|---|---|
| PDF with a text layer | extracts the text page by page (with page numbers) |
| Scanned PDF without text | recognizes the text on your computer (RapidOCR), up to 40 pages, and hands it to any model as text. The alphabet depends on the interface language: Cyrillic (and English) for Russian, Latin with diacritics for European languages, Chinese and English for Chinese and Japanese. If nothing could be recognized, the file goes to the model as is: only Anthropic can read such a file, and only with your own key |
| Password-protected PDF | Mnemai tells you the file is password-protected and suggests removing the password ("Print → Save as PDF") |
| Excel (xlsx, xls), CSV, TSV | a table by sheet, up to 2,000 rows per sheet |
| Word (docx), PowerPoint (pptx), OpenDocument, RTF, HTML | text; Word tables as rows, with cells separated by " \| " |
| Text files and code (txt, md, json, xml, py and others) | text as is |
| Images (png, jpg, gif, webp) | passed to the model as an image (Anthropic, models from OpenAI-compatible providers, and Ollama models with image support can see it) and, in addition, the text in the image is recognized on your computer — any model receives it |
| Other formats | the model receives only the file name |

The full text of the document is stored alongside the conversation. Except at the most precise step of "More precise ↔ More economical", the model receives the beginning of the document and the chunks that answer the current question, not the whole file. At the most precise step, the text is inserted in full, but no more than 60,000 characters. This lets you work with a PDF to: summarize it, find an answer in the text, pull out details and figures, compare two attached documents, and go through tables.

Creating and editing files, making PDF, Word, and Excel files, editing existing Word and Excel files, merging, cutting, rotating, and splitting PDFs, and reading files by path are file actions (see the section below). What Mnemai doesn't do with files: it doesn't fill in PDF forms and doesn't run programs or scripts.

## Internet

The "Internet" toggle below the input field allows searching, but doesn't turn it on for every message. Mnemai searches only when a question can't be answered without fresh external data: prices, exchange rates, news, latest versions, schedules, "now" and "today", and also when you directly ask her to "find" or "look up" something. For questions about Mnemai itself, about you, general knowledge ("what is …"), and tasks on a text you've provided, it doesn't go online. A link in a message is always read, even with the toggle off. Pages from links and VPN subscriptions open only at addresses on the internet: this computer, your home or office network, and internal addresses for Mnemai are blocked.

Search is free and needs no keys: Bing and Yahoo through the ddgs library, then DuckDuckGo, Bing, Yandex and Wikipedia directly. Results that don't match most of the keywords in the question are discarded. Pages are read and cleaned on your computer, the model receives numbered excerpts and cites them as [1], [2], and the sources are shown under the answer. If the internet is off and the question clearly requires fresh data, Mnemai answers with what it knows and suggests turning on search.

## More accurate or more economical

Settings → Engine → Fine-tuning → "More accurate ↔ More economical" is a single slider with five steps, set to the middle by default. More accurate means more memory and more document chunks are checked against your question, the model asks follow-up questions more often, and the answer costs more. More economical means less of both, and the model asks for clarification only when it can't do without it.

| Step | Memory in the request | Document checked | Conversation | Asks for clarification |
|---|---|---|---|---|
| Most economical | 2,000 characters | up to 3,500 | up to 8,000 | only when it can't do without it |
| More economical | 3,000 | up to 5,000 | up to 11,000 | only when it can't do without it |
| Balanced (default) | 4,200 | up to 7,000 | up to 14,000 | when needed |
| More accurate | 8,000 | up to 12,000 | up to 20,000 | more often |
| Most accurate | 16,000 | in full | in full | whenever anything is unclear |

Except at the most accurate step, Mnemai takes the beginning of the memory plus the lines relevant to your question. The last 6 messages of the conversation are kept in full, and older ones are shortened to 400 characters. Documents and web pages are included as relevant chunks. Below the answer you can see how many tokens were saved (an estimate: about 3.5 characters per token). Measured on a 153,000-character contract: 29,643 input tokens without savings versus 6,159 with them, and only the version with savings gave the correct answer.

## Questions as buttons, second pass, quoting

When the model needs a clarification, it asks one question as a card: the question itself, a one-line reason why it's asking, and 2–4 options in a column, in order, each with a short note on what happens if you pick it. You choose an option by clicking it or pressing its number on the keyboard, and at the bottom of the card you can answer in your own words. After you answer, the option you chose is marked with a checkmark. The gear icon on the card controls whether to ask questions as options, whether to explain the options, and whether to ask only when it really matters. "Second pass" (in settings) makes the model check its draft against your rules and memory before you see it. You can quote a selected piece of a reply in your next message. The "Helpful" button under a reply is a signal of which reply format works for you: the model treats the replies you've marked as examples of the right format.

## Recurring tasks

On the second similar task (or every time, or never — it's up to you in the settings), Mnemai offers to save a recipe, so next time you don't have to explain again or spend tokens on clarifying questions. A recipe — the goal, inputs, steps, result format, checks, and what not to do — is stored in 90 System/Recipes. The next similar request is then carried out by following it automatically, and under the answer you'll see "by recipe «…»". Mnemai determines similarity on your computer, by matching word stems.

## Term Hints

With "Hints" turned on (in the "+" menu below the input field), the model adds a short glossary to its reply: unfamiliar terms and all names in the reply — people, companies, products, services, communities (for example, Show HN), except you and the people you've told it about yourself. Mnemai strips the glossary off, underlines those words in the reply and shows the explanation when you hover over them.

## Consortium

"Debate with different AIs" under any answer: first a "Who to debate with?" window opens — all connected models except the author, with the best ones pre-selected, up to three opponents, and the first one selected sums things up. The author of the answer defends it, the opponents look for where it's wrong, incomplete, or where a better option exists, and at the end comes a verdict: whether the answer holds up and what to do. If only one AI is connected, its models debate each other (for example, Sonnet with Opus). This is a regular consortium in debate format, and you can continue it, stop it, or wrap it up.

The "Consortium" button under the input field starts a discussion between 2–4 AIs (any connected models, including the built-in one) for 1 to 20 rounds. They speak in turn, see each other and address each other by name, and the last one sums up: what they agree on, what they don't, and what they recommend. Above the messages is a round table: who is speaking, who is next, plus the buttons "Pause", "Resume", "Finish", "Discuss again". "Stop" (the send button while a reply is in progress) cuts off the current speaker immediately: what was said stays with an "interrupted" mark, and the others wait for "Resume". You can change the lineup and the number of rounds on the fly. Each participant gets the whole conversation: the last 16 messages in full, earlier ones in abridged form, attached documents in relevant passages for the question, text from images, the images themselves, and PDFs. Formats: advice, debate, brainstorm, red team, and roast (they tear apart an idea, résumé, or text harshly, and the summary starts with a "N/10" score). Under the summary there's "Share": a card image with the result. If you write during the discussion, the current speaker stops and the conversation continues from your message; a speaker who hasn't said anything yet (the service is stuck) is removed immediately. A participant whose key doesn't work or who has run out of funds says so once and doesn't take part in the discussion after that; another participant then sums up. Each participant gets memory according to their own access rights. You can connect the consortium to a conversation that's already in progress.


The consortium window is simple at first: who to invite to the council (2–4 AIs, the number on the card is the turn order), the discussion format, and a live table of the selected participants with the speaking order. The "Advanced settings" button opens everything else — rounds, roles, who sums up, reply length, fact-checking, and the round plan, each section with its own "?" explanation. "Simpler" returns to the simple view.

Fact-checking (on by default): if a participant relies on a fact, figure, date, or recent information, they search the internet themselves — up to two queries per turn — and reply with links [1], [2]. The sources are visible under their reply. They don't search for opinions and advice. A turn with a search is longer: the model answers twice, before the search and after. You can turn it off in advanced settings: "Search the web".

The gear on the "Consortium" button opens the same settings:

| Setting | Options |
|---|---|
| Format | Advice: own answer → review → improvement → disputed points → joint answer. Debate: participants alternate for and against, positions → objections → verdict. Brainstorm: ideas without criticism → building on others' ideas → three best (why, first step, risk). Red team: attack on your plan → how to close the gaps → list of risks and what to do |
| Roles | for each participant: no role, skeptic, practitioner, financier, lawyer, creative, analyst, customer |
| Summary by | the last in turn or a chosen participant: in the last round they speak last |
| Replies | short (up to 80 words, summary up to 120), normal (150 and 180), detailed (300 and 350) |

At the bottom of the window is a diagram: a table with participants in speaking order, the side in a debate, a trophy next to whoever sums up, and the round plan for the selected format. The format, length, and roles are remembered for the next council.

## Computer Actions

The model in chat can work with files: read a file (including PDF, Word, Excel, PowerPoint; scans and images are recognized on the computer), browse a folder, search files by words, create or rewrite a text file (.md, .txt, .csv, .json, .html), modify part of a file, generate a PDF, Word or Excel document from text with headings, lists and tables, save a string to memory. Works with any model, cloud or local.

Ready-made documents:

| What | How |
|---|---|
| Word (.docx) | text replacement preserving formatting: the phrase is found even if it contains a bold word or is split into chunks inside the file; new text inherits the formatting of the location where the old phrase started. Headers, footers and footnotes too |
| Excel (.xlsx, .xlsm) | values and formulas in cells ("Sheet1!B3 = 1500", "C7 = =SUM(C1:C6)"), text replacement in cells; other sheets, formats and formulas remain. Mnemai won't edit workbooks with charts, images or pivot tables — they would be lost on save |
| PDF | merge multiple files, keep needed pages in the desired order (same for cutting, deleting, reordering), rotate pages 90, 180 or 270, split into parts. Source file unchanged, new one doesn't overwrite existing |

### Quick Commands, Without Model

Unambiguous commands execute immediately, without calling the AI, same on any model: "open terminal/chrome/firefox/link", "open wikipedia with word …", "open on youtube …", "open google", "open yandex", "open habr", "open file …", "read file …", "what's in folder …" (including "what's in downloads"), "find … in files", "find … in memory", "show memory", "run …" (or `!command`), "remember …", "create file … with text: …", "make pdf/word/excel … from: …", "what time is it", "how much memory/cores/disk space". Known sites (Wikipedia, Google, Yandex, YouTube, GitHub, Habr, Stack Overflow, Kinopoisk) open immediately, searching for the query you spoke. Installation is also immediate: "install aircrack" — no window, password in chat. Everything else goes through the selected model.

### Mnemai Tools Only

Models have no tools of their own: Claude Code, DeepSeek Harness and cloud models don't run anything themselves. Any action — reading and writing files, documents, terminal, opening programs, memory — goes through Mnemai's MCP layer (the same one visible to Claude Desktop, Claude Code and Cursor via MCP). So all models have the same permissions, same log and same limitations.

### Terminal and Computer Control

If computer access is enabled (default — yes), the model can execute a command in the terminal: check processes, hardware, network and disk, launch a program, install a package, work with git, read or modify a file outside memory folders — everything the terminal can do. One command at a time, with a timeout (default 120 seconds, maximum 900 — for installation and scripts). Terminal window doesn't open: the command runs inside chat, its output appears in the response as it executes, and the return code and full output remain in the action line; execution is logged in "Memory" → "History". Multiple actions in a row are executed by Mnemai in one response, each as a short line in chat, and any can be stopped with a button. Opening a program or link takes one action `open_app name="chrome"` (or `name="https://…"`): Mnemai finds the installed program itself and reports if it's missing. The model knows about this access and uses it when the task can't be solved with files. Passwords, keys and tokens aren't shown in the response; destructive commands aren't executed without explicit request. sudo is allowed: Mnemai will ask for the administrator password right in chat, once, and it won't go into the conversation or to the model.

By default Mnemai performs the action immediately. If in Settings → Program → "Computer Actions" you enable "Ask permission for each action", a card appears below the response "Mnemai wants to" — what exactly and with which file or command, buttons "Yes", "Yes for this conversation" (such actions in this conversation won't be asked again) and "No". After the action, a line remains in the conversation "Created file …" with a "Show in Folder" button, and the model continues its response. Nothing goes to the internet.

Where allowed: files — memory folder and working folders you've added in Settings → Program → "Computer Actions"; terminal — across the entire computer. Same place to disable actions entirely, and the "Terminal and Computer Control" toggle disables only commands. Service folder .mnema is closed. The model reads a note from memory according to its permissions: hidden topics stay hidden. A document never overwrites an existing one — the new one gets the name "report (2).pdf". Any save can be rolled back: "Memory" → "History" — both in memory and in working folders. PDF is assembled through Edge, Chrome or Chromium browser without its window: Edge is present in any Windows 10 and 11, on macOS and Linux one of them is needed.

## Administrator Password

When a command or package installation requires administrator privileges, Mnemai asks for the password right in the chat — as a card showing the command and a masked input field, once. The password is verified by sudo itself; it never enters the conversation, the log, or the model, and is remembered for subsequent commands. For sudo and package installations, no terminal window opens: the command runs without a window, and the progress and result are visible in the chat; installations are given 300 seconds by default. A visible terminal window is only used for interactive programs that need a screen. On Windows there is no sudo — the card does not appear.

## Conversation without learning

The "No learning" toggle below the input field means this conversation teaches the memory nothing, starting from the very first message. The model still sees your memory, but nothing new from the conversation is saved, and a "Helpful" mark in it doesn't teach anything either.

## Voice and meetings

The microphone under the input field lets you speak a command or record a meeting. A command is recorded from the microphone, recognized on your computer and sent as a message, and the audio is deleted. A meeting recording captures the microphone and the computer's sound on two separate channels, so the transcript shows who is speaking. You can also just drag an audio or video file into the chat (including .mov from iPhone, .mp4, .avi, .3gp, .m4v). If the recognition model isn't there yet, you need to download it once (about 0.5 GB, internet required), and Mnemai will tell you so. Recognition is done by faster-whisper on your computer (the small or medium model, if downloaded). You can also use cloud Whisper with an OpenAI key: it costs $0.006 per minute, about $0.36 per hour. The "Decide automatically" mode (the default) measures your computer's speed during the first minute and, if it can't finish within the length of the meeting or 10 minutes, asks about using the cloud. The audio and Расшифровка.md stay in 80 Meetings; the transcript and a short summary go to the chat, and your words go into learning. In the meeting recording window, there is a "Configure" button in the top right that leads to Settings → Meeting recordings. There, the meeting's path is shown as four steps: Recording (whether to keep the audio), Transcription (where and at what accuracy), Summary (which model writes the summary), Memory (learns from your words). Click a step and its description and settings appear below. At the top are ready-made presets: "Private" (everything on your computer, audio is deleted), "Balanced" (decides automatically), "Fast" (cloud Whisper). You can also choose the summary model right in the recording window.

## Built-in model on your computer

Mnemai has a built-in llama.cpp server. You can choose from 13 GGUF models from Hugging Face, split into five groups: lightweight (Gemma 3 1B, Qwen2.5 1.5B, Llama 3.2 3B), balanced (Gemma 3 4B — recommended, Qwen3 4B, Phi-4 mini), smart (Qwen2.5 7B, Llama 3.1 8B, YandexGPT 5 Lite 8B), special (Qwen3 4B Thinking, Qwen2.5 Coder 7B), and large (Gemma 3 12B, Mistral Small 3.2 24B). For each one you'll see what it's for, its size, the memory it needs, and how long it will take to download on your connection. Downloads can be paused and resumed. Models are stored in ~/.mnema/models. It works offline and for free, but it's weaker than cloud models.

While a model on your computer is selected, the chat header shows a gauge: CPU load, the model's share of it, memory, and temperature, if your system provides it (Windows — not always, Linux — usually, macOS — no). If the model keeps your computer hot for a minute, Mnemai lowers its priority on its own and tells you about it. There are "Reduce load" and "Stop model" buttons.

## Engine: tokens and load

Settings → Engine, three modes:

| Mode | More accurate ↔ More economical | Response length | Cores | Context | Learning |
|---|---|---|---|---|---|
| Economy | more economical (3,000 characters of memory) | up to 1,000 tokens | a quarter | 4,096 | every 2 hours |
| Balanced (default) | balanced (4,200) | 3,000 | half | 8,192 | every 30 minutes |
| Maximum | maximum accuracy (16,000, no trimming) | 8,000 | all but one | 16,384 | every 10 minutes |

Fine-tuning is a single column: "More accurate ↔ More economical", longest response, monthly limit, CPU cores, how much she keeps in mind. Any slider you move manually switches the mode to "Custom". The monthly limit counts cloud tokens; when it runs out, cloud requests stop with a clear message, while the model on your computer keeps working. You can't limit the length of Claude's responses on a subscription.

Below is a separate "In the background" block: "Don't interrupt my work" lowers the priority of the model on your computer, and "Background learning" sets how often Mnemai checks the learning sources.

## Who Sees What

Settings → Security → "Who Sees What" — a table: AI models as columns, memory sections as rows, plus a block of private topics (Money, Health, Personal — stripped out even from permitted sections). Changes save instantly; the toggle under a column disables that AI entirely. By default nothing is hidden, and any AI can add new items to the inbox:

| AI | Can read | Can write to |
|---|---|---|
| Local model (built-in, Ollama, Strata) | everything | inbox |
| Claude, Claude Code | everything | inbox, decisions, projects, cards, people, rules |
| ChatGPT | profile, rules, projects, cards, decisions | inbox |
| OpenRouter, DeepSeek, YandexGPT | profile, rules, projects, cards, decisions | inbox |
| Gemini | profile, rules, cards | inbox |
| Cursor | rules, projects | inbox |

Local models can read everything because nothing leaves your computer. Money, Health, and Personal are visible by default to any AI that has access to Cards: to hide a topic from a specific AI, click "visible" in its column — it will switch to "hidden". Over MCP, a long-running command does not block the response: the client receives progress updates and can cancel it; a sudo command from MCP only executes after the password is entered in the Mnemai chat, and MCP never opens a terminal window.

A hidden tag on a heading (e.g. `## Money #money`) hides that heading and everything under it. A tag on a file title (`# Money #money`) or in the file's front matter (`tags`) hides the entire file. Russian tags also work — #деньги, #здоровье, #личное — in any case, as do properties in the format Obsidian writes them (tags as a list). A status change on a hidden card appears in the activity feed with the same tag, so it is hidden there too.

## What leaves your computer

Before any request to a cloud AI (chat, consortium, second pass, conversation titles, the learning brain, the portrait) and before any request to search engines, card numbers (Luhn-checked), passwords, PINs and CVVs, API keys, VPN tokens and keys, phone numbers, passport numbers, SNILS, INN and account numbers are replaced with placeholders like [PHONE-1]. The response comes back with the real values restored, on your computer. Turn this on in "Settings" → "Security". When the learning brain runs on someone else's cloud, it gets your memory under the same rules as the AI in chat: hidden topics are never sent to it. Every outgoing request is a line in the log: when, to whom, why (chat reply, learning, portrait, conversation title, web search), how many characters, how much of the available memory was sent, and what was hidden (only the count, never the values). A request that didn't go out (no program, no key, no connection) isn't written to the log. "Sent out this week" in the "Memory" card at the bottom left shows a report for the last 7 days.

## Encrypt your memory with a password

Settings → Security → "Encrypt memory with a password", on Windows, macOS and Linux. The same option is offered on first launch, in the "Protect your memory with a password?" step: no password by default, and you can enter your own or click "Generate a strong one". With an encrypted memory, sync with Google Drive, Dropbox, your own folder or a station sends only encrypted files; a copy with a different password is not accepted and does not overwrite yours. Mnemai encrypts your notes and the internal files that hold what you said and did: conversations, attachment text, the journal and its snapshots for rollback, learning traces, the report on what has gone outside, the portrait. Without the password they can't be read, even if someone copies the folder.

| | |
|---|---|
| How it works | a random memory key (AES-256-GCM) encrypts the files, and the password encrypts that key via scrypt; both are stored in .mnema/crypto.json |
| Password | at least 8 characters, and it can't be recovered: if you forget it, the memory can't be restored. You can change it at any time, and the files aren't rewritten when you do |
| Remember on this computer | the key is kept in the system's secure storage (Windows — DPAPI, macOS — Keychain, Linux — the password store if there is one, otherwise a file in your home folder that only you can access): Mnemai opens without asking. If it's off, the password is requested on every launch, and until you enter it Mnemai shows nothing and learns nothing |
| What isn't encrypted | binary files (PDF, Word, images, meeting recordings), since other programs open them; settings needed before the password is entered (language, models, AI access permissions); folders of other programs (.obsidian and similar) |
| The cost | Obsidian and other editors can't open encrypted notes. If another program writes a note into the folder, Mnemai encrypts it the next time it opens |
| Interruption midway | files are encrypted one at a time: each is written alongside, checked to read back identically, and only then replaces the old one. If you shut the computer down midway, some files will stay unencrypted but all remain readable, and the next time Mnemai opens it will encrypt the rest |
| Claude Code, Cursor (MCP) | get the memory as before, if Mnemai is running or the password is remembered on this computer |

"Remove encryption" (the same switch, requires the password) returns your files to normal.

On Windows there is also system-level encryption (EFS): it's transparent to you, to Mnemai and to other programs, the key is your Windows account, and it isn't available on Windows Home.

## History and rollback

Every write to memory goes into a log: who wrote it, what, and when. Go to "Memory" → "History": any change can be undone with a single button. If the file was edited afterwards, the rollback removes only the lines from that entry and keeps the later edits; it refuses only if that exact line has already been edited by hand. Before the first edit of a file each day, Mnemai saves a copy to 95 Saves, and the last two copies are kept. Writes from chat, learning and other AIs are processed one at a time, so simultaneous writes don't overwrite each other. If a file open in the Mnemai editor changed while you were editing it, Mnemai won't overwrite it and will ask you to reopen it.

If a rule is phrased in different words ("Keep chat summaries short" and "Make summaries short"), Mnemai doesn't add a second line but rewrites the existing one in the new wording.

## Connecting Other AIs

- Claude Code, Claude Desktop, Cursor: Settings → "AI & Models" → "Memory in Other AIs" → "Connect" on the tile. Connected via MCP: memory_context, memory_search, memory_remember, memory_stale, memory_journal, memory_undo. Context is split into chunks of up to 9,000 characters. Cursor only receives rules and projects and writes nothing back. The tile shows whether a connection is already active.
- ChatGPT: via an OpenAI key through the OpenAI tile, or via a ChatGPT subscription through a separate Sign in with ChatGPT flow; generating responses requires the Codex CLI App Server to be installed. Gemini connects with its own Google AI Studio key. There is no browser extension: everything the AIs cannot do themselves, Mnemai handles locally on your computer.
- Over MCP, each AI sees in the journal only entries it is allowed to read, and can only roll back its own entries. After upgrading from a portable version, the connection in Claude and Cursor automatically switches to the new installation.
- Models: Settings → "AI & Models". At the top — "Currently responding": the default model's tile and model selection. Below — "Models" in two sections: "Paid" (subsection "Subscription" — Claude and ChatGPT by subscription; subsection "API Key" — Claude · API key, ChatGPT · API key, DeepSeek, Gemini, OpenRouter, OpenCode Go, YandexGPT; API is billed separately, OpenCode Go uses a subscription key) and "Free" (built-in model, Ollama, and Strata, running on this computer). The model menu in the top-left and the "Which AI do you want to talk to?" step at first launch follow the same structure. Tiles are equal-sized badges in each provider's colors: built-in, Claude subscription, Claude · API key (Anthropic), ChatGPT subscription (official Sign in with ChatGPT + Codex App Server), ChatGPT · API key, OpenCode Go, Gemini, OpenRouter, Ollama. ChatGPT can be connected in two ways: an OpenAI API key is billed separately by usage, while a ChatGPT subscription is connected through the official Sign in with ChatGPT window and requires separate consent to use the plan's quota. Mnemai stores its own OAuth tokens in the system keychain and does not read the Codex CLI session; the Codex App Server must be installed for generation. A Gemini Advanced subscription does not provide a Google AI Studio key: the API is billed separately. A connected tile is shown in color with a "connected" status; a disconnected one is gray. Each tile has a single button: "Enter Key" → the key field opens directly in the tile → "Save and Find Models" or "Cancel"; for Ollama it's an address field, for the built-in model it's "Choose and Download". The Claude subscription tile appears automatically if Claude Code is present on the computer: Mnemai searches for it not only in standard program paths but also in the locations used by installers (official, npm, WinGet, Volta, bun, Homebrew) and inside the Claude Desktop app. If Claude Code is found but you are not signed in, the tile shows a "Sign In" button: Claude Code's sign-in window opens, sign in with your subscription, then click "Check Again". If Claude Code is not found — "How to Install". Every connected AI has a "Disable" button: it disappears from all model lists (chat, consortium, "With and Without Memory"), while the key and settings are preserved; "Enable" brings it back. If an AI is connected but not responding due to an account issue — an exhausted Claude limit or subscription, insufficient account balance, an expired Claude Code session, a rejected key — the tile displays "not working" and the reason, that AI drops out of the lists, and the next working one responds. The "Check Again" button makes a small real request. The model menu in the top-left works the same way for all AIs: each connected provider shows its three best models (the newest full-size ones, then lightweight mini and flash variants) and an "All Models" link with a count. In "All Models", working models appear first; below a divider, "Legacy & Utility": previous generations (gpt-3.5, gpt-4, Claude 3), dated snapshots, and models for images, voice, and search. The selected model is visible in the menu even if it is not among the top three. The key field and verification are collapsed below the list. When a quota runs out, Mnemai retries automatically after half an hour. A key is verified immediately on save: an invalid key is not treated as connected. In "Memory in Other AIs", a connected tile shows a dot traveling along the Mnemai → app line.
- Built-in model: Settings → "AI & Models" → "Local Model".

## Proxy and VPN

Everything that goes out to the internet (models, search, model downloads) goes through a single proxy: the one set in Mnemai (on first launch, the "Proxy…" tray menu, Settings → App → "VPN and proxy"), otherwise the system proxy (Windows; macOS — System Settings → Network; Linux — the https_proxy variables and the GNOME settings), otherwise a direct connection. HTTP and SOCKS5 with a username and password are supported, and the password is kept in the system's secure storage. VPN by key: paste a vless://, vmess://, trojan://, ss:// link or an https:// subscription, and Mnemai will start Xray just for itself ("Import key" from the clipboard or "Enter key manually"). You can also go through a VPN client that's already running. "Check" reaches Anthropic through the proxy and tells you what's wrong. The built-in model doesn't use the proxy.

## Window, tray, installation

On first launch — a quick introduction: six use cases, one idea per screen (no need to re-explain, one memory across all AIs, fewer tokens in any AI, meeting → tasks, remembers decisions and deadlines, secrets stay with you) and AI selection. The tokens case shows a measurement from the "Token savings" section: a question about a 153,000-character contract, 29,643 input tokens for the full text versus 6,159 with Mnemai. "Skip" closes the introduction immediately.

Closing the window hides it to the tray, learning continues; the first time Mnemai asks "to tray or quit" and remembers the answer. "Quit" in the tray menu stops everything. In the tray menu: "Open Mnemai", "Learn now", "Pause learning", "Proxy…" and autostart ("Launch with Windows", on macOS "Open at login", on Linux "Launch at login"). Relaunching doesn't open a second copy, it shows the window of the first. On Windows, Mnemai removes dead process icons from the tray itself on launch. If the Linux desktop doesn't show the tray, closing the window quits the program.

Mnemai checks for updates itself: in the background, every six hours, without windows or prompts. When a new version is released, a quiet "Update" button with the version number appears next to the gear. It downloads the file appropriate for the system and updates the program: on Windows the installer runs on exit, on Linux the new file replaces the program and it restarts, on macOS the .dmg image opens — just drag Mnemai to "Applications". "Later" postpones the reminder until the next version, and you can check manually in the gear with the "Check" button. Background checks are disabled in config.json: "auto_update": false, or by launching with MNEMA_NO_UPDATE=1.

The installer installs Mnemai without administrator rights in %LOCALAPPDATA%\Programs\Mnemai, finds old versions and deletes only their program files: everything else in that folder (for example, memory created next to the program) remains. Uninstalling the program doesn't delete the memory either. There's also a portable version as an archive. The installer doesn't have a digital signature yet: Windows will show "Windows protected your PC" — click "More info" → "Run anyway". On a clean Windows 10, Mnemai will install the Microsoft WebView2 window component itself (internet needed once). macOS: .dmg image, drag Mnemai to "Applications". The program isn't signed by Apple, so the first time open it with right-click → "Open" (or System Settings → Privacy & Security → "Open Anyway"). Linux: single .AppImage file (make it executable and run) or .tar.gz archive with a folder. The window on Linux uses Qt; if it doesn't open, you need libxcb-cursor0 and libfuse2 packages (for AppImage).

If the memory folder isn't in place at launch (it was moved, renamed, or the external drive isn't connected), Mnemai says so and offers to specify where it is now, check again, or start a new memory. The first screens are in the system language. Mnemai explains service errors in words: what happened and what to do; the error remains in the conversation, the interrupted response is marked, "Stop" frees the conversation immediately.

## The gear, theme, language, achievements

The gear in the top right opens: learning (at the top is the status; when memory is on, the learning pause switch sits there too, and when memory is off there is only the label "Memory is off"; also the mode and the feed), theme, language, achievements (you can turn them off), "How Mnemai works" (the tour), "How memory works" (the guide) and "Mnemai Reference". Tips you have turned off come back here too: "Tutorial in new conversations" and "Expensive conversation tip". The close button on any window is a transparent circle with a thin cross, the same size as the "?" icon, and Escape closes it as well. In a conversation with learning turned off, the dot on the gear is orange; outside of it, the dot goes back to showing the learning state. The dot on the gear shows the state: green means it is learning, yellow means memory is off or learning is paused, gray means it learns only what you say explicitly, or learning is off. The learning status is visible in the input bar: "Mnemai is learning · memory updated N min ago". If there is no model for processing speech, it says "Mnemai remembers only what you say directly": only explicit things are saved ("remember …", corrections, decisions).

There are nine interface languages: Russian, English, Chinese, Spanish, Hindi, Portuguese, French, German, Japanese. The model replies in the selected language. Conversations and memory are not translated.

Achievements: 99 awards in five groups (getting started, memory growth, savings and habit, privacy, rare), and most of the rare ones are hidden until you earn them. Experience points for awards (10, 25, 50, 100) give you levels from "Newcomer" to "Eternal Memory".

The gear has "Mnemai Reference" — this is the reference inside the app: sections on the left, search at the top, and matches are highlighted. Settings always open on the first section, "AI and models". At launch, Mnemai shows a splash screen for a second: the logo, the name and the tagline "Free Memory AI Interface". The input bar's gear is small, in the top right next to the "?", and opens the input bar settings.

## Multiple memories

In Settings, on the left under the sections, there's a "Memory" block: all the memories on this computer, with the open one marked by a checkmark. Click another one to open it. "New memory" takes you to the first screen, and the current one stays in the list. The ⋮ menu next to a memory offers "Rename", which changes the name in the list (the folder on disk keeps its own name), and "Delete". Deleting asks twice: the second dialog, "Delete … for sure?", lists what will go (portrait, facts, conversations, history), and the "Delete" button wakes up after 10 seconds, with a red bar shrinking beneath it and a countdown running. The folder goes to the Recycle Bin, and you can restore it from there. If the memory is open, Mnemai first closes it and switches to the next one in the list, or to the first screen if there are no others.

## Telegram

Settings → Learning → "Telegram". Mnemai reads Telegram through its API, and it only reads: the Telegram client inside Mnemai can do nothing but sign in and read, and any other command (send, delete, mark as read, join, react) is rejected inside the app before it is ever sent. Signing in works like Telegram Desktop: you need the api_id and api_hash from my.telegram.org (API development tools), your phone number, the code from Telegram, and your cloud password if you have one. Below that is "Chats to read": "Add chats" opens a searchable list of your personal chats and groups, and you check the ones you want. As long as no chat is selected, Mnemai reads nothing. Channels and bots can't be selected. In the selected chats, the whole conversation is read: your messages are labeled "Me", and the others are labeled with the other person's name, which is how Mnemai learns about both you and the people around you. Your login is stored encrypted in your system's secure storage, while the chat list and what Mnemai has learned are kept in the memory folder, and Mnemai has no servers of its own. "Disconnect" erases the login; in Telegram, the session stays in "Devices" until you end it there.

## The "Memory" card at the bottom left

The card has two rows, and each one opens proof: "Local memory on your PC" opens the memory folder, and "Access settings" opens the "Which AI sees what" table. The card's gear icon leads to the protection settings, and the green "?" next to it opens the "How memory works" guide. The guide has 12 chapters: a table of contents on the left, and on the right a scene, an explanation, an example (what you say and what happens in memory) and a "Try it" button that takes you to the real place in the app. The chapters are: the folder on your computer, how the memory folder is organized, the date of a fact (when you said it), learning from conversations, save right away or ask first (the 60% and 80% thresholds), corrections become rules, picking what's needed before answering, AI permissions, secrets, old facts get re-asked, history with rollback, and the model on your computer. At the end comes "Check it yourself": the folder, who sees what, and what went outside.

Try it (the "+" menu under the input field and the "Memory" page):
- "Get to know each other" — seven short questions: who you are, where you live, what matters most right now, your projects, the people around you, how to talk to you, and what the AI must never do. Your answers are saved to memory as regular facts and don't overwrite anything.
- "How well does Mnemai know you" — a quiz of ten facts from memory: "Correct" (the fact's status gets today's date), "Not anymore" (you write how it is now, and the old one moves to the fact archive), "Not true" (the fact moves to the archive). You get a score at the end.
- "With and without memory" — ask one question to your connected AIs (up to three); each answers twice: like a regular chat without memory, and through Mnemai. The answers appear side by side.
- "Roast" — a consortium in a roast format.
Any result can be turned into a picture card ("Share"): copy it, save it to "Pictures/Mnemai", or copy a ready-made post text with a link. The picture shows only what you see in the window before sending.

## What Mnemai can't do

- Doesn't run programs or scripts. She works with files only through actions: in the memory folder and in working folders, each one recorded in the log and can be rolled back.
- System-level encryption (EFS) is available only on Windows; Mnemai's password encryption works everywhere.
- For a long scan, only the first 40 pages are recognized.
- Without internet, cloud models and search don't work. If the connection drops mid-conversation, a model on your computer answers instead (if it's downloaded) and notes this in a line above the reply.
- Doesn't read email or calendar until you give it an address and password or a link.
