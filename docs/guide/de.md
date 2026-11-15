<div align="center">

<img src="../img/brand/logo.svg" width="72" alt="Mnemai">

# Mnemai-Handbuch

Wie Mnemai funktioniert, Bildschirm für Bildschirm und Einstellung für Einstellung. Mnemai beantwortet Fragen über sich selbst aus genau diesem Text.

<sub><a href="en.md">English</a> · <a href="ru.md">Русский</a> · <a href="zh.md">中文</a> · <a href="es.md">Español</a> · <a href="hi.md">हिन्दी</a> · <a href="pt.md">Português</a> · <a href="fr.md">Français</a> · <b>Deutsch</b> · <a href="ja.md">日本語</a></sub>

<sub><a href="../../README.de.md">README</a></sub>

</div>

## Inhalt

- [Was ist Mnemai](#was-ist-mnemai)
- [Gedächtnis ein- oder ausgeschaltet](#gedächtnis-ein--oder-ausgeschaltet)
- [Memory-Ordner](#memory-ordner)
- [Zusätzliche Gedächtnisordner](#zusätzliche-gedächtnisordner)
- [Wie ein Fakt gespeichert wird](#wie-ein-fakt-gespeichert-wird)
- [Tab „Gedächtnis"](#tab-gedächtnis)
- [Porträt](#porträt)
- [Zusammenfassung von 10 Now und das Inhaltsverzeichnis](#zusammenfassung-von-10-now-und-das-inhaltsverzeichnis)
- [Wie Mnemai lernt](#wie-mnemai-lernt)
- [Lernquellen](#lernquellen)
- [Lernmodi](#lernmodi)
- [Wie Mnemai Texte versteht](#wie-mnemai-texte-versteht)
- [Wie Mnemai entscheidet: speichern oder nachfragen](#wie-mnemai-entscheidet-speichern-oder-nachfragen)
- [Lernfeed und Rückfrage im Gespräch](#lernfeed-und-rückfrage-im-gespräch)
- [Chat und Modelle](#chat-und-modelle)
- [Sitzungen](#sitzungen)
- [Wie sie antwortet](#wie-sie-antwortet)
- [Was das Modell in jeder Nachricht weiß](#was-das-modell-in-jeder-nachricht-weiß)
- [Dateien und Dokumente, auch PDF](#dateien-und-dokumente-auch-pdf)
- [Internet](#internet)
- [Genauer oder sparsamer](#genauer-oder-sparsamer)
- [Fragen per Schaltfläche, zweiter Durchgang, Zitat](#fragen-per-schaltfläche-zweiter-durchgang-zitat)
- [Wiederkehrende Aufgaben](#wiederkehrende-aufgaben)
- [Begriffs-Hinweise](#begriffs-hinweise)
- [Konsortium](#konsortium)
- [Aktionen auf dem Computer](#aktionen-auf-dem-computer)
- [Administratorpasswort](#administratorpasswort)
- [Gespräch ohne Lernen](#gespräch-ohne-lernen)
- [Stimme und Meetings](#stimme-und-meetings)
- [Integriertes Modell auf dem Computer](#integriertes-modell-auf-dem-computer)
- [Engine: Token und Last](#engine-token-und-last)
- [Wer von den KIs was sieht](#wer-von-den-kis-was-sieht)
- [Was den Computer verlässt](#was-den-computer-verlässt)
- [Speicher mit Passwort verschlüsseln](#speicher-mit-passwort-verschlüsseln)
- [Verlauf und Rückgängig-Machen](#verlauf-und-rückgängig-machen)
- [Verbindung anderer KI-Dienste](#verbindung-anderer-ki-dienste)
- [Proxy und VPN](#proxy-und-vpn)
- [Fenster, Tray, Installation](#fenster-tray-installation)
- [Zahnrad, Design, Sprache, Erfolge](#zahnrad-design-sprache-erfolge)
- [Mehrere Gedächtnisse](#mehrere-gedächtnisse)
- [Telegram](#telegram)
- [Karte „Gedächtnis" unten links](#karte-gedächtnis-unten-links)
- [Was Mnemai nicht kann](#was-mnemai-nicht-kann)

## Was ist Mnemai

Mnemai ist ein Gedächtnisprogramm für jede KI. Es merkt sich, wer du bist, woran du arbeitest, welche Entscheidungen du getroffen hast und wie man mit dir sprechen soll, und bringt das in das Gespräch mit jedem Modell ein: Claude, ChatGPT, Gemini, dem integrierten Modell auf deinem Computer, Cursor und Agenten. Das Gedächtnis ist ein Ordner mit gewöhnlichen Markdown-Dateien auf deinem Computer. Du kannst ihn in jedem Editor öffnen (auch in Obsidian) – und auch ohne Mnemai. Mnemai hat weder eine Cloud noch ein Konto. Das Programm besteht aus einem Fenster (Chat, Gedächtnis, Einstellungen) und einem Symbol im Infobereich der Taskleiste (unter macOS in der Menüleiste). Es läuft unter Windows 10 und 11, macOS 11 und neuer (Apple Silicon und Intel) sowie Linux (64-Bit, Ubuntu 22.04 und neuer und ähnliche Distributionen). Die persönliche Version ist kostenlos und Open Source (Lizenz AGPL-3.0), die Version für Unternehmen gibt es separat.

## Gedächtnis ein- oder ausgeschaltet

Das Gedächtnis ist der Hauptschalter von Mnemai: Du findest den Schalter im Bereich „Gedächtnis" unten links im Chat (derselbe sitzt unter Einstellungen → Lernen → „Gedächtnis"). Solange das Gedächtnis ausgeschaltet ist, leuchtet der Punkt auf dem Zahnrad oben rechts gelb. Ein neues Gedächtnis, das auf dem ersten Bildschirm angelegt wird, startet ausgeschaltet: Im Tutorial gibt es den Schritt „Gedächtnis aktivieren?" (standardmäßig „Ohne Gedächtnis"), und wenn das Tutorial nicht angezeigt wurde, erscheint dieselbe Frage in einem eigenen Fenster. Ein Gedächtnis, das schon vor der Einführung des Schalters existierte, bleibt eingeschaltet.

Ausgeschaltet ist es ein ganz normaler Chat mit jeder KI: Das Modell weiß nichts über den Besitzer, Mnemai merkt sich nichts (es findet kein Lernen statt, „Merk dir das" schreibt nichts auf, die Aktion „Ins Gedächtnis schreiben" wird abgelehnt), und Claude Code, Claude Desktop und Cursor erhalten keinen Zugriff auf das Gedächtnis und können nichts hineinschreiben. Alles andere funktioniert weiter: beliebige Modelle, Konsortium, Dokumente und die Token-Ersparnis dabei, Internet, Meetings, lokale Modelle sowie Dateiaktionen in Arbeitsordnern (der Gedächtnisordner ist für Aktionen gesperrt). Der Tab „Gedächtnis" zeigt den Bildschirm „Gedächtnis ausgeschaltet" mit den Schaltflächen „Gedächtnis aktivieren" und „Gespeichertes ansehen". Die Lerneinstellungen und „Welche KI was sieht" sind abgeblendet, versehen mit dem Hinweis „Gedächtnis ausgeschaltet" und der Schaltfläche „Aktivieren". Die Schaltfläche „Nicht lernen" im Chat ist inaktiv, und die Statuszeile zeigt „Gedächtnis ausgeschaltet · normaler Chat, nichts wird gespeichert".

## Memory-Ordner

Dein Gedächtnis liegt in dem Ordner, den du beim ersten Start ausgewählt hast. Darin findest du:

| Ordner oder Datei | Inhalt |
|---|---|
| 00 Inbox/Inbox.md | nicht einsortierte Fakten |
| 10 Now.md | Übersicht für heute: wer du bist, aktive Projekte, letzte Ereignisse, neue Fakten der letzten 14 Tage, Status älter als 30 Tage zur Überprüfung. Wird automatisch erstellt und nicht von Hand bearbeitet |
| 20 Projects/<Name>/_Project.md | Projekt-Hub: Status (active, paused, closed), Ziel, Startdatum, Schlüsselwörter, Verlauf. Die Projektdokumente liegen daneben |
| 30 People/<Name>.md | Personenkarte |
| 60 Events/JJJJ-MM.md | Entscheidungen und Statuswechsel nach Monaten, die neuesten oben |
| 70 Memory/Profile.md | wer du bist |
| 70 Memory/Rules.md | wie man mit dir arbeiten soll, eine Regel pro Zeile mit Datum |
| 70 Memory/Thoughts.md | deine Gedanken und Ideen |
| 70 Memory/Cards/<Thema>.md | Themenkarte: ein Fakt pro Zeile, Schlüsselwörter und versteckte Tags im Kopfbereich |
| 70 Memory/Fact archive/ | Fakten, die durch neuere ersetzt wurden. Das ist die Historie, die Modelle nicht erhalten |
| 70 Memory/Index.md | Inhaltsverzeichnis: Projekte, Karten und Personen mit Schlüsselwörtern. Wird automatisch erstellt |
| 80 Meetings/ | Meeting-Aufzeichnungen, Transkripte und Zusammenfassungen |
| 90 System/Journal/<Tag>.md | Journal: was von wem gespeichert wurde, in verständlicher Sprache |
| 90 System/Recipes/ | Rezepte für wiederkehrende Aufgaben |
| 95 Saves/ | Kopie einer Datei vor der ersten Änderung am Tag, die letzten zwei werden aufbewahrt |
| 99 Archive/ | abgeschlossene Projekte samt Dokumenten |
| .mnema/ | intern: KI-Zugriffe, Änderungsprotokoll, Snapshots zum Zurücksetzen, Tokens, Lerneinstellungen, Gespräche |

Du kannst die Dateien im Gedächtnis auch von Hand bearbeiten. Mnemai liest nur diese Struktur.

## Zusätzliche Gedächtnisordner

Einstellungen → Programm → „Zusätzliche Gedächtnisordner": weitere Ordner, die die KIs zusammen mit dem Hauptgedächtnis sehen. Geeignet ist jeder Ordner: Notizen, ein Obsidian-Vault, Dokumente, ein gemeinsamer Teamordner oder ein weiteres Mnemai-Gedächtnis. Die Schaltfläche „Obsidian verbinden" findet Obsidian-Vaults auf deinem Computer von selbst (anhand der Einstellungen von Obsidian selbst) und zeigt sie mit der Anzahl der Notizen an: Die markierten werden zum zusätzlichen Gedächtnis, den Ordner kannst du auch manuell angeben. Jeden anderen Ordner fügst du mit der Schaltfläche „Hinzufügen" (oder „Auswählen…") hinzu, entfernen kannst du ihn mit „Entfernen" daneben. Der Vault wird einmal vollständig im Hintergrund eingelesen, danach nur noch geänderte Notizen, deshalb bremsen auch Tausende von Notizen die Antworten nicht aus. Markdown- und Textdateien werden auf deinem Computer gelesen, an die Frage werden nur passende Stellen angehängt, und zwar im gleichen Umfang wie beim Gedächtnis (Regler „Genauer ↔ Sparsamer"). Themen, die für diese KI ausgeblendet sind (#money, #health, #private und die russischen Formen), werden auch aus diesen Dateien herausgeschnitten. Mnemai schreibt nichts in diese Ordner und lernt auch nicht aus ihnen.

## Wie ein Fakt gespeichert wird

Ein Fakt ist eine Zeile mit Datum: "- 21.09.2026 · Wir haben beschlossen, den Pilot im November zu starten". Ein Status wird mit dem Zusatz "(Status TT.MM.JJJJ)" geschrieben. Ein neuer Status zum selben Thema ersetzt den alten an Ort und Stelle, der alte wandert ins Faktenarchiv, und die Änderung erscheint im Ereignis-Feed. Was Mnemai selbst gelernt hat, ist mit dem Wort "gelernt" markiert, damit man sieht, was aus dem Lernen stammt.

Das Datum bei einem gelernten Fakt ist der Tag, an dem du es gesagt oder geschrieben hast, nicht der Tag, an dem Mnemai es gelesen hat. Wenn Mnemai heute einen Chatverlauf von vor einem Monat liest, bekommt der Fakt das Datum dieses Gesprächs, und der Beschluss landet in den Ereignissen dieses Monats. So wird Altes nicht als Neuigkeit ausgegeben.

Status, die älter als 30 Tage sind, listet Mnemai nicht gesondert auf. Das Modell kennt das Datum jedes Status: Geht es im Gespräch um einen Status, der älter als einen Monat ist, nennt es das Datum und fragt nach, ob er noch gilt.

## Tab „Gedächtnis"

Gedächtnis → Porträt: Oben siehst du dein Porträt mit Zählern für die Fakten, darunter die „Gedächtniskarte" – die Themen als Blasen rund um dich: Die Größe richtet sich nach der Anzahl der Fakten, ein Schloss markiert Themen, die nicht alle KIs sehen können, und was sich in den letzten drei Tagen geändert hat, pulsiert. Die Beschriftung einer kleinen Blase erscheint, wenn du mit der Maus darüberfährst. Unter der Karte findest du Themenkacheln: „Regeln für die KI", „Projekte", „Menschen um dich herum", die Abschnitte des Porträts, Themenkarten (die größten zuerst) und „Ereignisse und Entscheidungen". Auf jeder Kachel stehen die Anzahl der Fakten und zwei aktuelle Zeilen (bei Projekten und Personen sind es die ersten Namen). Ein Klick auf eine Kachel oder Blase öffnet das Thema in einem Fenster darüber: Alle Fakten stehen jeweils in einer Zeile pro Fakt, die neuesten oben und das Datum rechts. Dazu gibt es eine Suche, ein Klick klappt einen Fakt vollständig auf, bei gelernten Fakten findest du dort auch „Woher?", und der Stift öffnet die Datei. Gleiche Abschnitte des Porträts (zum Beispiel das offene und das verborgene „Wer ich bin") werden als ein Thema angezeigt.

## Porträt

Das Porträt besteht aus 2–3 Sätzen am Anfang von 70 Memory/Profile.md: Wer du bist, was du machst und was gerade für dich am wichtigsten ist. Jede KI bekommt es als Erstes. Mnemai erstellt das Porträt selbst, sobald sich mindestens drei Fakten über dich angesammelt haben: aus den offenen Abschnitten des Profils, den aktiven Projekten und den Karten ohne versteckte Tags (Geld, Gesundheit und Privates fließen nicht ins Porträt ein). Geschrieben wird es von dem Modell, das du für das Lernen ausgewählt hast; ohne Modell besteht es aus den Fakten selbst, in kurzen Sätzen. Das Porträt wird nach dem Lernen neu erstellt: sofort, wenn sich das Profil geändert hat, und höchstens einmal in 6 Stunden, wenn sich nur Karten und Projekte geändert haben. Wenn du das Porträt selbst umgeschrieben hast, fasst Mnemai es nicht mehr an. Die Erstellung erscheint im Protokoll als „Porträt erstellt“ und lässt sich im Verlauf rückgängig machen.

## Zusammenfassung von 10 Now und das Inhaltsverzeichnis

Mnemai baut 10 Now.md und 70 Memory/Index.md nach jedem Eintrag selbst neu auf. In 10 Now stehen: wer du bist, aktive Projekte, die letzten Ereignisse, frische Fakten der letzten 14 Tage (höchstens 12) und veraltete Status. Im Inhaltsverzeichnis findest du jedes Projekt, jede Karte und jede Person samt den Stichwörtern, über die du sie suchen kannst. Diese Dateien von Hand zu bearbeiten bringt nichts: Beim nächsten Aufbau gehen deine Änderungen verloren.

## Wie Mnemai lernt

Mnemai lernt von selbst, im Laufe deines Alltags. Fragebögen und Formulare musst du nicht ausfüllen. Das Programm erkennt Fakten in den Quellen, die du freigegeben hast, und entscheidet, ob es sie sofort speichert oder dich vorher fragt. Das Lernen läuft im Hintergrund per Timer (die Häufigkeit hängt vom Engine-Modus ab: von 10 Minuten bis 2 Stunden) und sofort bei jeder deiner Nachrichten im Mnemai-Chat. Beim ersten Start sieht Mnemai sich den Verlauf der letzten 90 Tage an.

Beim ersten Start fragt Mnemai: „Darf Mnemai andere Programme ansehen?“. „Nein, nur Mnemai“ – dann lernt sie nur aus Gesprächen mit ihr und aus deinen Korrekturen darin und arbeitet ausschließlich mit ihrem eigenen Gedächtnisordner: Sie liest weder Claude-Code-Chats noch Notizen, Dokumente, Telegram, den Browser oder die Erweiterung. „Ja, ich wähle aus“ – es öffnet sich eine Liste dessen, was auf dem Computer gefunden wurde (Claude-Code-Chats, Notizordner, Dokumente, Telegram-Export, Browserverlauf, Erweiterung) samt Pfaden. Kein Eintrag ist vorausgewählt, und Mnemai liest nur, was du markiert hast. E-Mail und Kalender schaltet sie nie von selbst ein: Dafür braucht es eine Adresse und ein Passwort oder einen geheimen Link.

All das lässt sich unter „Einstellungen → Lernen“ ändern. „Was Mnemai ansehen darf“ ist der Hauptschalter „Andere Programme und Browser“: Ist er ausgeschaltet, sind die Kacheln der externen Quellen mit einem Schloss gesperrt und lassen sich nicht aktivieren. Weiter unten, unter „Wo gelernt wird“, wird jede Quelle einzeln aktiviert; bei einigen kannst du einen Pfad und Ausnahmen festlegen.

Den eigenen Gedächtnisordner und die eigenen internen Modellaufrufe liest Mnemai nie.

## Lernquellen

| Quelle | Was gelesen wird |
|---|---|
| Gespräche in Mnemai | deine Nachrichten im Mnemai-Chat, sofort, während du schreibst |
| Gespräche in Claude Code | deine Nachrichten aus dem Claude-Code-Verlauf (Ordner ~/.claude/projects), nur neue Zeilen. Systemanfragen von Skripten mit einer Kennzeichnung wie "[SERVICE-NAME]" am Anfang werden übersprungen |
| ChatGPT-Export | die Datei conversations.json aus dem ChatGPT-Datenexport |
| Deine Korrekturen | "nein, so nicht", "das hatte ich doch gesagt", "niemals …" in Gesprächen mit der KI werden zu Regeln für alle KIs |
| Notizordner | neue Zeilen in Notizen, zum Beispiel in einem Obsidian-Vault. Systemordner (.obsidian, .trash, .git) sind ausgeschlossen |
| E-Mail | deine gesendeten E-Mails per IMAP, Zitate werden abgeschnitten |
| Telegram (Chats über die API) | der gesamte Chatverlauf – deine Nachrichten und die deiner Gesprächspartner – nur in den Chats, die du ausgewählt hast. Nur Lesezugriff, Details im Abschnitt "Telegram" |
| Telegram (Export) | deine eigenen Nachrichten aus dem Telegram-Desktop-Export |
| Kalender | eine .ics-Datei oder ein geheimer iCal-Link |
| Dokumente | neue und geänderte Word-Dokumente, Texte und Notizen im ausgewählten Ordner (.docx, .txt, .md) |
| Browserverlauf | Titel der gelesenen Seiten nach Tagen (Chrome, Edge, Yandex Browser). Standardmäßig wird nur beobachtet |

## Lernmodi

Der Modus wird für jede Quelle einzeln festgelegt:

| Modus | Was passiert |
|---|---|
| Nur ansehen | zeigt, was Mnemai lernen würde, schreibt aber nichts |
| Alles nachfragen | schreibt von sich aus nichts: Im Gespräch in Mnemai fragt sie nach, bei anderen Quellen zeigt sie nur an |
| Gemischt (Standard) | Sichere Informationen schreibt Mnemai selbst. Persönliches und Dinge, die dem Gedächtnis widersprechen, klärt sie bei Gesprächen in Mnemai direkt im Gespräch per Rückfrage, bei anderen Quellen entscheidet sie selbst. Schwache Vermutungen warten auf eine Wiederholung |
| Alles selbst | schreibt alles; als Absicherung dienen das Protokoll und die Rückgängig-Funktion |

Kommt ein Fakt in mehreren Quellen vor, gilt der vorsichtigste dieser Modi.

## Wie Mnemai Texte versteht

Normale Sprache kann Mnemai auf unterschiedliche Weise auswerten („Einstellungen" → „Lernen" → „Womit Texte verstanden werden"):

| Variante | So funktioniert es |
|---|---|
| Mnemai selbst (Standard) | das Modell, mit dem du standardmäßig sprichst – ein beliebiges verbundenes, ob in der Cloud oder auf dem Computer; ist keines vorhanden, werden nur explizite Signale erkannt |
| Ohne Modell | nur Explizites: „merk dir …", Korrekturen, Entscheidungen („entschieden …"), Statusdaten |
| Claude per Abo | über das installierte Claude Code, ohne Tools, Hooks und MCP, die Sitzung wird nicht gespeichert |
| Eigener Schlüssel | Anthropic oder OpenAI-kompatibel; der Schlüssel liegt im geschützten Speicher des Systems (Windows – DPAPI, macOS – Schlüsselbund, Linux – Passwortspeicher, falls vorhanden), nicht im Gedächtnisordner |
| Modell auf dem Computer | integriert oder Ollama, nichts verlässt den Computer |

Bevor ein Text an ein Cloud-Modell gesendet wird, werden Geheimnisse durch Platzhalter ersetzt (siehe „Was den Computer verlässt").

## Wie Mnemai entscheidet: speichern oder nachfragen

- Der Standard-Schwellenwert für die Sicherheit liegt bei 80 %. Liegt die Sicherheit bei 80 % oder höher und ist der Fakt nicht persönlich, speichert Mnemai ihn selbstständig. Bei 60 % bis 80 % fragt sie nach. Unter 60 % wartet sie, bis der Fakt noch einmal auftaucht.
- Wiederholung erhöht die Sicherheit: Zweimal 60 % ergeben 84 %, und der Fakt wird gespeichert.
- Geld, Gesundheit und Persönliches landen in einer Karte mit dem Tag #money, #health oder #private: Du kannst sie in der Tabelle „Welche KI was sieht" vor jeder KI verbergen. Kommt so etwas in einem Gespräch in Mnemai zur Sprache, fragt Mnemai zuerst direkt dort: „Das ist persönlich – soll ich es mir merken?"
- Widerspruch im Gedächtnis („wohnt in Kasan" gegen „kommt aus Jekaterinburg"): In einem Gespräch in Mnemai erscheint die Frage direkt dort („Jetzt ist es so", „Es war richtig", „Beides stimmt"). Aus anderen Quellen ersetzt der neue Fakt den alten. Hat die alte Zeile mehr ausgesagt, schreibt Mnemai sie um und behält den Rest bei. Das Frühere wandert ins Faktenarchiv.
- „Nie so etwas lernen" fügt eine Stoppphrase hinzu. Das Zurücksetzen eines gelernten Eintrags im Verlauf bedeutet „Nein": Das kommt nicht wieder.
- Eine Warteschlange „wartet auf dich" gibt es nicht: Mnemai sammelt keine Fragen an. Unter einem Gespräch steht immer höchstens eine Frage zum Gedächtnis; die nächste erscheint erst nach deiner Antwort.

## Lernfeed und Rückfrage im Gespräch

Der Feed „Ich lerne von dir" (Zahnrad → „Feed") zeigt, was Mnemai gelesen hat, was sie verstanden hat und warum sie sich so entschieden hat, zum Beispiel „Sicherheit 90 % bei einem Schwellenwert von 80 %, nicht persönlich – selbst gespeichert" oder „Das betrifft Geld – im verborgenen Bereich gespeichert". Wenn für das Gedächtnis dein Wort gebraucht wird, erscheint unter dem Gespräch die Karte „Ich frage kurz nach" mit Schaltflächen; deine Antwort wird sofort gespeichert. Bei jeder gelernten Zeile gibt es „Woher ich das weiß": die Quelle, deine Worte, wie oft es vorkam und warum es gespeichert wurde.

## Chat und Modelle

Mnemai ist ein Chat mit beliebigen Modellen – alle Modelle sind gleichwertig. Die Modellauswahl befindet sich oben links im Chat; das Menü enthält zwei Gruppen:

- Cloud-Modelle – funktionieren über das Internet: per Schlüssel (Anthropic, OpenAI, Gemini, OpenRouter, DeepSeek, YandexGPT; die Modellliste bezieht Mnemai vom Anbieter, bei YandexGPT aus dem Katalog Yandex Cloud AI Studio) oder per Abonnement (Claude Code);
- Lokal – kostenlos, ohne Internet, nichts verlässt den Computer: integriertes Modell (llama.cpp), Ollama und Strata.

Beim Verbinden und über „Prüfen" fragt Mnemai jedes Modell aus der Liste ChatGPT, Gemini, DeepSeek und YandexGPT mit einer kurzen Anfrage ab und behält nur die, die im Chat antworten: Abgekündigte Modelle (z. B. o4-mini, gpt-4, o1), Modelle für Audio, Bilder und Sprache sowie Modelle ausschließlich für eine andere API im Standard-OpenAI-Katalog (pro, codex) werden nicht in die Liste aufgenommen. Falls ein Anbieter ein Modell später abkündigt, verschwindet es nach dem ersten Fehler aus der Liste, und im Chat erscheint ein Hinweis, ein anderes Modell zu wählen. DeepSeek wird mit einem Schlüssel von platform.deepseek.com verbunden. YandexGPT – mit dem API-Schlüssel des Yandex Cloud AI Studio-Dienstkontos (Rolle ai.languageModels.user) und der Katalog-ID, in der es erstellt wurde: das Verbindungsfenster hat zwei Felder. YandexGPT-Modelle: Alice AI LLM, YandexGPT Pro 5.1, YandexGPT Pro 5, Alice AI LLM Flash sowie DeepSeek V4.1 Flash und Qwen3.6 35B aus demselben Katalog. Strata ist ein separates kostenloses Programm für große Modelle (Qwen, DeepSeek) auf der eigenen Grafikkarte (github.com/Niko1221/Strata): installiere es, starte das Modell mit dem Befehl strata launch – Mnemai findet die laufende Strata beim Start automatisch unter 127.0.0.1:8080; eine andere Adresse lässt sich im Verbindungsfenster von Strata eintragen.

Dieselben zwei Gruppen finden sich unter Einstellungen → KI und Modelle. Das Limit für die Antwortlänge (Einstellungen → Engine) gilt für alle Modelle, einschließlich Claude per Abonnement.

Gedächtnis und deine Regeln werden auf jede Nachricht angewendet; jedes Modell erhält nur das, was es sehen darf. Jede Unterhaltung hat einen Namen aus 1–3 Wörtern. Er lässt sich mit dem Stiftsymbol neben dem Namen, per Doppelklick auf den Namen oder über das Unterhaltungsmenü in der Liste ändern (Enter – speichern, Escape – abbrechen). Bei einer neuen Unterhaltung kann der Name vor der ersten Nachricht festgelegt werden – er wird zusammen mit ihr gespeichert. Manuell umbenannte Unterhaltungen ändert Mnemai nicht mehr; außerdem werden die Zeit der letzten Änderung und die verbrauchten Token angezeigt. Die Liste lässt sich nach Datum oder nach Token sortieren; der Filter „KI" zeigt Unterhaltungen mit einem bestimmten Modell.

Die Schaltfläche „Mnemai selbst beginnen lassen" in einer leeren Unterhaltung: Das Modell begrüßt dich und schlägt anhand des Gedächtnisses vor, womit du beginnen könntest. Ereignisse nennt es nur dann „kürzlich", wenn das Datum dies bestätigt; Entscheidungen, die älter als ein Monat sind, empfiehlt es zu überprüfen.

## Sitzungen

Die Schaltfläche „Neue Sitzung" befindet sich im Kopf der Liste, unter „Neues Gespräch". Eine Sitzung umfasst alle Gespräche, die seit dem letzten Klick begonnen wurden: „Neues Gespräch" öffnet ein Gespräch in der aktuellen Sitzung, „Neue Sitzung" beginnt eine neue Gruppe. In der Liste sind die Gespräche einer Sitzung durch eine Linie links verbunden, die Gruppe hat eine Beschriftung und rechts die Anzahl der Gespräche: die oberste heißt „Aktuelle Sitzung", frühere heißen „Sitzung · 24. Okt." (Tag des letzten Gesprächs). Ein Klick auf die Beschriftung klappt die Gruppe ein, der eingeklappte Zustand wird gespeichert. Direkt nach „Neue Sitzung" gibt es keine leere Zeile: Die oberste Gruppe bleibt die „Aktuelle Sitzung", bis in der neuen das erste Gespräch erscheint. Neben der Beschriftung gibt es das Menü ⋮: „Umbenennen" (eigener Name für die Gruppe) und „Löschen" (die Sitzung samt ihren Gesprächen; angeheftete bleiben erhalten, Gelerntes bleibt im Gedächtnis). Gespräche, die vor der Einführung von Sitzungen begonnen wurden, bilden eine eigene Sitzung am Ende der Liste, angeheftete stehen oben außerhalb der Gruppen. Bei der Suche, bei der Sortierung nach Tokens und bei der Gruppierung nach Tagen ist die Liste normal, ohne Sitzungen.

Neben den Schaltflächen steht „?": Eine Animation zeigt, warum es teuer ist, lange in einem Gespräch zu bleiben, und worin sich ein neues Gespräch und eine neue Sitzung unterscheiden.

Jedes Gespräch schickt dem Modell nur seinen eigenen Verlauf. Deshalb beginnt ein Gespräch in einer neuen Sitzung mit einem sauberen Kontext: Das Modell erhält das Gedächtnis und die Regeln, aber nicht den Chatverlauf früherer Gespräche. Ein langes Gespräch schickt mit jeder Antwort immer mehr Verlauf mit, deshalb ist es günstiger, ein neues Thema in einem neuen Gespräch oder einer neuen Sitzung zu beginnen – das Wichtige aus der Vergangenheit hat Mnemai bereits im Gedächtnis gespeichert.

Wenn eine Antwort dreimal so viel gekostet hat wie die erste Antwort desselben Modells in diesem Gespräch (Eingabe-Tokens samt Cache und Antwort), erscheint darunter die Karte „Das Gespräch ist teuer geworden" (bei einem kostenlosen Modell auf dem Computer erscheint sie nicht): zwei Balken – die erste und die letzte Antwort – und der Faktor, um den die letzte teurer ist. Die Schaltfläche „Gedächtnis aktualisieren und neue Sitzung starten" lässt Mnemai zuerst das gesamte Gespräch in einem Durchgang lernen und beginnt dann eine neue Sitzung mit sauberem Kontext. Eine Nachricht, die bereits früher gelernt wurde, gilt dabei nicht als Wiederholung. In einem Gespräch ohne Lernfunktion startet die Schaltfläche einfach eine neue Sitzung. „Nicht mehr anzeigen" schaltet den Hinweis ganz ab; wieder einschalten lässt er sich im Zahnrad („Hinweis zu teuren Gesprächen"). Das Kreuz auf der Karte blendet sie nur in diesem Gespräch aus.

## Wie sie antwortet

Einstellungen → „Antwortstil": Name, Anrede (du oder Sie), Antwortlänge (kurz, auf den Punkt, ausführlich), Geschlecht – für die Endungen (z. B. „bereit" bzw. grammatisch angepasste Formen) – und Charakter. Alle Auswahlmöglichkeiten sind Kacheln, rechts steht das „Antwortbeispiel": Dieselbe Frage zum Pilotprojekt, und die Antwort ändert sich sofort mit den Einstellungen, der Name sogar direkt bei der Eingabe. Die Charaktere – Sanft, Sachlich, Streng mit Prüfungen – sind Medaillen mit einer Prüfskala von eins bis drei. Darunter folgen Sets und ausführliche Regeln nach Gruppen.

## Was das Modell in jeder Nachricht weiß

Bevor das Modell antwortet, bekommt es:
- wie es mit dir arbeiten soll – die Regeln aus dem Abschnitt „Wie geantwortet wird" (Charakter, Anrede, deine Wörter);
- das Gedächtnis, das dieses Modell sehen darf (den Kopf des Gedächtnisses und die Zeilen, die zur Frage passen);
- Angaben dazu, wie Mnemai gerade aufgebaut ist: wo sie lernt, in welchem Modus sie läuft, womit sie Texte versteht und wie viele Einträge im Gedächtnis liegen;
- das heutige Datum;
- bei Fragen zu Mnemai selbst – die passenden Abschnitte dieser Wissensbasis.

Das Modell antwortet als Mnemai und spricht über ihre Fähigkeiten nur das, was Mnemai kann. Die Fähigkeiten der Engine, auf der sie läuft (zum Beispiel die Tools von Claude Code), gehören nicht zu Mnemai.

## Dateien und Dokumente, auch PDF

Eine Datei hängst du mit der Büroklammer unter dem Eingabefeld an oder ziehst sie per Drag-and-drop ins Fenster. Eine Datei darf bis zu 25 MB groß sein. Mnemai speichert sie neben dem Gespräch und extrahiert den Text selbst, auf deinem Computer und kostenlos.

| Format | Was Mnemai damit macht |
|---|---|
| PDF mit Textebene | extrahiert den Text seitenweise (mit Seitenzahlen) |
| PDF-Scan ohne Text | erkennt den Text auf deinem Computer (RapidOCR), bis zu 40 Seiten, und gibt ihn als Text an jedes beliebige Modell weiter. Das Alphabet richtet sich nach der Sprache der Oberfläche: Kyrillisch (und Englisch) für Russisch, Lateinisch mit Diakritika für europäische Sprachen, Chinesisch und Englisch für Chinesisch und Japanisch. Wenn sich nichts erkennen ließ, geht die Datei als Ganzes an das Modell: Eine solche Datei liest nur Anthropic mit eigenem API-Schlüssel |
| Passwortgeschütztes PDF | Mnemai sagt dir, dass die Datei passwortgeschützt ist, und schlägt vor, das Passwort zu entfernen ("Drucken → Als PDF speichern") |
| Excel (xlsx, xls), CSV, TSV | Tabelle nach Blättern, bis zu 2000 Zeilen pro Blatt |
| Word (docx), PowerPoint (pptx), OpenDocument, RTF, HTML | Text; Word-Tabellen zeilenweise, Zellen getrennt durch « \| » |
| Textdateien und Code (txt, md, json, xml, py und andere) | Text unverändert |
| Bilder (png, jpg, gif, webp) | wird als Bild an das Modell weitergegeben (sehen können es Anthropic, Modelle OpenAI-kompatibler Anbieter und Ollama mit Bildunterstützung) und zusätzlich erkennt Mnemai den Text im Bild auf deinem Computer – ihn erhält jedes Modell |
| Andere Formate | das Modell erhält nur den Dateinamen |

Der vollständige Text des Dokuments wird neben dem Gespräch gespeichert. Außer auf der genauesten Stufe von "Genauer ↔ Sparsamer" erhält das Modell den Anfang des Dokuments und die Abschnitte, die zur aktuellen Frage passen, nicht die ganze Datei. Auf der genauesten Stufe wird der Text vollständig eingefügt, aber nicht mehr als 60 000 Zeichen. So kannst du mit einem PDF: es zusammenfassen, eine Antwort im Text finden, Bankdaten und Zahlen herausziehen, zwei angehängte Dokumente vergleichen und Tabellen auswerten.

Dateien erstellen und bearbeiten, PDF, Word und Excel anlegen, fertige Word- und Excel-Dateien ändern, PDFs zusammenfügen, zuschneiden, drehen und aufteilen sowie Dateien über den Pfad lesen – das sind Dateiaktionen (siehe den Abschnitt unten). Was Mnemai mit Dateien nicht tut: Sie füllt keine PDF-Formulare aus und führt keine Programme oder Skripte aus.

## Internet

Der Schalter „Internet" unter dem Eingabefeld erlaubt die Suche, schaltet sie aber nicht für jede Nachricht ein. Mnemai sucht nur, wenn sich ohne aktuelle externe Daten sicher nicht antworten lässt: Preise, Kurse, Nachrichten, neueste Versionen, Fahrpläne, „jetzt" und „heute" – sowie wenn du ausdrücklich „such" oder „recherchiere" sagst. Bei Fragen zu Mnemai selbst, zu dir, bei Allgemeinwissen („Was ist …") und bei Aufgaben zu einem vorgegebenen Text geht das Programm nicht ins Netz. Ein Link in der Nachricht wird immer gelesen, auch bei ausgeschaltetem Schalter. Seiten hinter Links und VPN-Abos werden nur über Adressen im Internet geöffnet: Dieser Computer, das Heim- oder Büronetz und interne Adressen von Mnemai sind gesperrt.

Die Suche ist kostenlos und braucht keine Schlüssel: Bing und Yahoo über die Bibliothek ddgs, danach DuckDuckGo, Bing, Yandex und Wikipedia direkt. Ergebnisse, die nicht zur Mehrheit der Schlüsselwörter der Frage passen, werden verworfen. Die Seiten werden auf deinem Computer gelesen und bereinigt, das Modell erhält nummerierte Auszüge und verweist auf sie mit [1], [2]; die Quellen siehst du unter der Antwort. Ist das Internet ausgeschaltet, die Frage verlangt aber eindeutig aktuelle Daten, antwortet Mnemai mit dem, was sie weiß, und schlägt vor, die Suche einzuschalten.

## Genauer oder sparsamer

Einstellungen → Engine → Feinabstimmung → "Genauer ↔ Sparsamer" – ein Schieberegler mit fünf Stufen, standardmäßig in der Mitte. Genauer: Mehr Gedächtnis und mehr Dokumentabschnitte werden mit der Frage abgeglichen, das Modell fragt öfter nach, die Antwort wird teurer. Sparsamer: weniger davon, das Modell fragt nur nach, wenn es nicht anders geht.

| Stufe | Gedächtnis in der Anfrage | Dokumentabgleich | Gespräch | Rückfragen |
|---|---|---|---|---|
| Am sparsamsten | 2.000 Zeichen | bis zu 3.500 | bis zu 8.000 | nur wenn es nicht anders geht |
| Sparsamer | 3.000 | bis zu 5.000 | bis zu 11.000 | nur wenn es nicht anders geht |
| Ausgewogen (Standard) | 4.200 | bis zu 7.000 | bis zu 14.000 | bei Bedarf |
| Genauer | 8.000 | bis zu 12.000 | bis zu 20.000 | öfter |
| Maximal genau | 16.000 | vollständig | vollständig | bei jeder Unklarheit |

Außer auf der genauesten Stufe werden vom Gedächtnis der Anfang und die Zeilen übernommen, die zur Frage passen. Die letzten 6 Nachrichten des Gesprächs bleiben vollständig erhalten, ältere werden auf 400 Zeichen gekürzt. Dokumente und Webseiten werden in passenden Abschnitten übernommen. Unter der Antwort siehst du, wie viele Tokens eingespart wurden (Schätzung: etwa 3,5 Zeichen pro Token). Messung an einem Vertrag mit 153.000 Zeichen: 29.643 Eingabe-Tokens ohne Einsparung gegenüber 6.159 mit Einsparung – und die richtige Antwort lieferte nur die Variante mit Einsparung.

## Fragen per Schaltfläche, zweiter Durchgang, Zitat

Braucht das Modell eine Klarstellung, stellt es genau eine Frage als Karte: die Frage selbst, in einer Zeile der Grund, warum es fragt, und 2–4 Antwortoptionen untereinander, der Reihe nach, jeweils mit einer kurzen Erklärung, was bei der Auswahl passiert. Du wählst eine Option per Klick oder mit der Zifferntaste auf der Tastatur; unten auf der Karte kannst du auch mit eigenen Worten antworten. Nach der Antwort ist die gewählte Option mit einem Häkchen markiert. Das Zahnrad auf der Karte steuert, ob Fragen als Optionen gestellt werden, ob die Optionen erklärt werden und ob nur bei echtem Bedarf gefragt wird. Der „Zweite Durchgang“ (in den Einstellungen) bewirkt, dass das Modell den Entwurf anhand deiner Regeln und deines Gedächtnisses prüft, bevor du ihn siehst. Einen markierten Teil der Antwort kannst du in der nächsten Nachricht zitieren. Die Schaltfläche „Hilfreich“ unter einer Antwort zeigt, welche Antwortform für dich passt: Markierte Antworten nimmt sich das Modell als Vorbild für die Form.

## Wiederkehrende Aufgaben

Bei der zweiten ähnlichen Aufgabe (oder bei jeder, oder nie – das stellst du in den Einstellungen ein) schlägt Mnemai vor, ein Rezept zu speichern, damit du es beim nächsten Mal nicht erneut erklären musst und keine Tokens für Rückfragen verbrauchst. Ein Rezept – Ziel, Eingabedaten, Schritte, Format des Ergebnisses, Prüfungen und was nicht getan werden soll – liegt in 90 System/Recipes. Die nächste ähnliche Anfrage wird automatisch danach ausgeführt, unter der Antwort steht dann „nach Rezept „…"". Die Ähnlichkeit ermittelt Mnemai lokal auf deinem Computer, anhand übereinstimmender Wortstämme.

## Begriffs-Hinweise

Wenn du die „Hinweise" aktivierst (im Menü „+" unter dem Eingabefeld), ergänzt das Modell seine Antwort um ein kurzes Glossar: unklare Begriffe und alle Namen in der Antwort – Personen, Unternehmen, Produkte, Dienste, Communities (zum Beispiel Show HN), außer dir selbst und Personen, von denen du selbst erzählt hast. Mnemai schneidet das Glossar ab, unterstreicht diese Wörter in der Antwort und zeigt die Erklärung an, sobald du mit der Maus darüberfährst.

## Konsortium

„Mit verschiedenen KIs diskutieren" unter jeder Antwort: Zuerst öffnet sich das Fenster „Mit wem diskutieren?" – alle verbundenen Modelle außer dem Autor, die besten sind vorausgewählt, bis zu drei Gegner, das Fazit zieht das erste markierte Modell. Der Autor der Antwort verteidigt sie, die Gegner suchen, wo sie falsch oder unvollständig ist oder es eine bessere Variante gibt, am Ende steht das Fazit: ob die Antwort standhält oder nicht und was zu tun ist. Ist nur eine KI verbunden, diskutieren ihre Modelle untereinander (zum Beispiel Sonnet mit Opus). Das ist ein ganz normales Konsortium im Debattenformat, du kannst es fortsetzen, anhalten oder beenden.

Der Button „Konsortium" unter dem Eingabefeld startet eine Diskussion von 2–4 KIs (beliebige verbundene Modelle, auch das integrierte) über 1 bis 20 Runden. Sie sprechen abwechselnd, sehen einander und sprechen sich mit Namen an, die letzte KI zieht das Fazit: worin sie sich einig sind, worin nicht und was sie empfehlen. Über den Nachrichten sitzt ein runder Tisch: Wer spricht, wer als Nächstes dran ist, dazu die Buttons „Pause", „Fortsetzen", „Beenden", „Nochmal diskutieren". „Stoppen" (der Senden-Button, solange eine Antwort läuft) bricht den aktuellen Sprecher sofort ab: Das Gesagte bleibt mit dem Vermerk „unterbrochen" stehen, die anderen warten auf „Fortsetzen". Besetzung und Rundenzahl kannst du mitten im Verlauf ändern. Jeder Teilnehmer bekommt das ganze Gespräch: die letzten 16 Nachrichten vollständig, frühere gekürzt, angehängte Dokumente in den Abschnitten, die zur Frage passen, dazu den Text aus Bildern, die Bilder selbst und PDF. Formate: Rat, Debatte, Brainstorming, Red Team und Roast (die Idee, der Lebenslauf oder der Text wird hart auseinandergenommen, das Fazit beginnt mit einer Bewertung „N/10"). Unter dem Fazit gibt es „Teilen": eine Bildkarte mit dem Ergebnis. Wenn du während der Diskussion schreibst, stoppt der aktuelle Sprecher und das Gespräch geht mit deiner Nachricht weiter; ein Sprecher, der noch nichts gesagt hat (der Dienst hängt), wird sofort abgesetzt. Ein Teilnehmer, dessen Schlüssel nicht passt oder dessen Guthaben aufgebraucht ist, sagt das einmal und nimmt danach nicht mehr an der Diskussion teil; das Fazit zieht dann ein anderer. Jeder Teilnehmer erhält Erinnerungen gemäß seinen Zugriffsrechten. Das Konsortium lässt sich in ein bereits laufendes Gespräch einschalten.


Das Konsortium-Fenster ist zunächst schlicht: Wen du in den Rat holst (2–4 KIs, die Nummer auf der Karte ist die Reihenfolge), das Diskussionsformat und ein lebendiger Tisch mit den gewählten Teilnehmern in der Sprechreihenfolge. Der Button „Erweiterte Einstellungen" öffnet alles Weitere – Runden, Rollen, wer das Fazit zieht, Länge der Beiträge, Faktencheck und Rundenplan; jeder Bereich hat sein eigenes „?" mit einer Erklärung. „Einfacher" bringt dich zur schlichten Ansicht zurück.

Faktencheck (standardmäßig aktiviert): Stützt sich ein Teilnehmer auf einen Fakt, eine Zahl, ein Datum oder aktuelle Informationen, sucht er selbst im Internet – bis zu zwei Anfragen pro Zug – und antwortet mit Links [1], [2]. Die Quellen siehst du unter seinem Beitrag. Bei Meinungen und Ratschlägen sucht er nicht. Ein Zug mit Suche dauert länger: Das Modell antwortet zweimal, vor der Suche und danach. Du kannst das in den erweiterten Einstellungen ausschalten: „Im Internet suchen".

Das Zahnrad am Button „Konsortium" öffnet dieselben Einstellungen:

| Einstellung | Optionen |
|---|---|
| Format | Rat: eigene Antwort → Prüfung → Verbesserung → Streitpunkte → gemeinsame Antwort. Debatte: Die Teilnehmer sind abwechselnd dafür und dagegen, Positionen → Einwände → Urteil. Brainstorming: Ideen ohne Kritik → fremde Ideen weiterentwickeln → die drei besten (warum, erster Schritt, Risiko). Red Team: Angriff auf deinen Plan → wie die Lücken geschlossen werden → Liste der Risiken und was zu tun ist |
| Rollen | für jeden Teilnehmer: keine Rolle, Skeptiker, Praktiker, Finanzexperte, Jurist, Kreativer, Analyst, Kunde |
| Fazit zieht | die letzte KI in der Reihenfolge oder ein ausgewählter Teilnehmer: In der letzten Runde spricht er als Letzter |
| Beiträge | kurz (bis 80 Wörter, Fazit bis 120), normal (150 und 180), ausführlich (300 und 350) |

Unten im Fenster steht ein Schema: der Tisch mit den Teilnehmern in der Sprechreihenfolge, die Seite in der Debatte, ein Pokal bei dem, der das Fazit zieht, und der Rundenplan für das gewählte Format. Format, Länge und Rollen werden für den nächsten Rat gespeichert.

## Aktionen auf dem Computer

Das Modell im Chat kann mit Dateien arbeiten: eine Datei lesen (einschließlich PDF, Word, Excel, PowerPoint; Scans und Bilder werden auf dem Computer erkannt), einen Ordner ansehen, Dateien nach Wörtern suchen, eine Textdatei erstellen oder überschreiben (.md, .txt, .csv, .json, .html), einen Teil einer Datei ändern, ein PDF-, Word- oder Excel-Dokument aus Text mit Überschriften, Listen und Tabellen erstellen, eine Zeile im Speicher aufzeichnen. Funktioniert mit jedem Modell, ob in der Cloud oder auf dem Computer.

Fertige Dokumente:

| Was | Wie |
|---|---|
| Word (.docx) | Textersetzung mit Beibehaltung der Formatierung: Die Phrase wird gefunden, auch wenn sie ein fettgedrucktes Wort enthält oder innerhalb der Datei in Stücke aufgeteilt ist; der neue Text erhält die Formatierung der Stelle, an der die alte Phrase begann. Kopf- und Fußzeilen sowie Fußnoten auch |
| Excel (.xlsx, .xlsm) | Werte und Formeln in Zellen ("Tabelle1!B3 = 1500", "C7 = =SUMME(C1:C6)"), Textersetzung in Zellen; andere Blätter, Formate und Formeln bleiben erhalten. Eine Arbeitsmappe mit Diagrammen, Bildern oder Pivot-Tabellen bearbeitet Mnemai nicht – beim Speichern würden sie verloren gehen |
| PDF | mehrere Dateien zusammenführen, benötigte Seiten in der gewünschten Reihenfolge behalten (so auch ausschneiden, löschen, umordnen), Seiten um 90, 180 oder 270 Grad drehen, in Teile aufteilen. Die Originaldatei wird nicht geändert, die neue überschreibt keine vorhandene |

### Schnellbefehle, ohne Modell

Eindeutige Befehle werden sofort ausgeführt, ohne KI-Aufruf, bei jedem Modell gleich: „öffne terminal/chrome/firefox/link", „öffne wikipedia mit dem wort …", „öffne auf youtube …", „öffne google", „öffne yandex", „öffne habr", „öffne datei …", „lies datei …", „was ist im ordner …" (einschließlich „was ist in downloads"), „finde … in dateien", „finde … im speicher", „zeige speicher", „führe aus …" (oder `!befehl`), „merke dir …", „erstelle datei … mit text: …", „erstelle pdf/word/excel … aus: …", „wie spät ist es", „wieviel speicher/kerne/festplattenplatz". Bekannte Websites (Wikipedia, Google, Yandex, YouTube, GitHub, Habr, Stack Overflow, Kinopoisk) werden sofort geöffnet, mit Suche nach der angegebenen Anfrage. Installation auch sofort: „installiere aircrack" – ohne Fenster, Passwort im Chat. Alles andere – über das ausgewählte Modell.

### Nur Mnemai-Tools

Die Modelle haben keine eigenen Tools: Claude Code, DeepSeek Harness und Cloud-Modelle führen nichts selbst aus. Jede Aktion – Lesen und Schreiben von Dateien, Dokumente, Terminal, Öffnen von Programmen, Speicher – läuft über die MCP-Schicht von Mnemai (dieselbe, die Claude Desktop, Claude Code und Cursor über MCP sehen). Daher haben alle Modelle die gleichen Rechte, das gleiche Protokoll und die gleichen Einschränkungen.

### Terminal und Computersteuerung

Wenn der Computerzugriff aktiviert ist (standardmäßig ja), kann das Modell einen Befehl im Terminal ausführen: Prozesse, Hardware, Netzwerk und Festplatte anzeigen, ein Programm starten, ein Paket installieren, mit git arbeiten, eine Datei außerhalb der Speicherordner lesen oder ändern – alles, was das Terminal kann. Ein Befehl nach dem anderen, mit Timeout (standardmäßig 120 Sekunden, maximal 900 – für Installation und Skripte). Das Terminalfenster wird nicht geöffnet: Der Befehl läuft innerhalb des Chats, seine Ausgabe erscheint während der Ausführung in der Antwort, und der Rückgabecode sowie die vollständige Ausgabe bleiben in der Aktionszeile; die Ausführung wird im Protokoll "Speicher" → "Verlauf" aufgezeichnet. Mehrere Aktionen hintereinander führt Mnemai in einer Antwort aus, jede als kurze Zeile im Chat, und jede kann mit der Schaltfläche gestoppt werden. Ein Programm oder einen Link öffnen kann man mit einer Aktion `open_app name="chrome"` (oder `name="https://…"`): Mnemai findet das installierte Programm selbst und sagt Bescheid, wenn es nicht vorhanden ist. Das Modell weiß von diesem Zugriff und nutzt ihn, wenn die Aufgabe nicht mit Dateien gelöst werden kann. Passwörter, Schlüssel und Token werden nicht in der Antwort ausgegeben; destruktive Befehle werden ohne direkte Aufforderung nicht ausgeführt. sudo ist erlaubt: Mnemai fragt das Administrator-Passwort direkt im Chat, einmal, und es gelangt weder in die Konversation noch zum Modell.

Standardmäßig führt Mnemai die Aktion sofort aus. Wenn in Einstellungen → Programm → "Aktionen auf dem Computer" die Option "Nach Erlaubnis für jede Aktion fragen" aktiviert ist, erscheint unter der Antwort eine Karte "Mnemai möchte" – was genau und mit welcher Datei oder welchem Befehl, Schaltflächen "Ja", "Ja für diese Unterhaltung" (solche Aktionen in dieser Unterhaltung werden nicht mehr gefragt) und "Nein". Nach der Aktion bleibt in der Unterhaltung eine Zeile "Datei erstellt …" mit der Schaltfläche "Im Ordner anzeigen", und das Modell fährt mit der Antwort fort. Nichts geht ins Internet.

Wo möglich: Dateien – Speicherordner und Arbeitsordner, die du in Einstellungen → Programm → "Aktionen auf dem Computer" hinzugefügt hast; Terminal – auf dem gesamten Computer. Dort können auch Aktionen komplett deaktiviert werden, und der Schalter "Terminal und Computersteuerung" deaktiviert nur Befehle. Der Dienstordner .mnema ist gesperrt. Eine Notiz aus dem Speicher liest das Modell nach seinen Rechten: verborgene Themen bleiben verborgen. Ein Dokument überschreibt niemals ein vorhandenes – das neue erhält den Namen "bericht (2).pdf". Jede Aufzeichnung kann rückgängig gemacht werden: "Speicher" → "Verlauf" – sowohl im Speicher als auch in den Arbeitsordnern. PDF wird über den Browser Edge, Chrome oder Chromium ohne dessen Fenster erstellt: Edge ist in jedem Windows 10 und 11 vorhanden, auf macOS und Linux wird einer von ihnen benötigt.

## Administratorpasswort

Wenn ein Befehl oder eine Paketinstallation Administratorrechte erfordert, fragt Mnemai einmalig direkt im Chat nach dem Passwort – als Karte mit dem Befehl und einem maskierten Eingabefeld. Das Passwort wird von sudo selbst geprüft; es gelangt weder in den Chatverlauf noch in das Protokoll noch zum Modell und wird für nachfolgende Befehle gespeichert. Für sudo und Paketinstallationen öffnet sich kein Terminalfenster: Der Befehl läuft ohne Fenster, Fortschritt und Ergebnis sind im Chat sichtbar, und für Installationen gilt standardmäßig ein Timeout von 300 Sekunden. Ein sichtbares Terminalfenster bleibt nur interaktiven Programmen vorbehalten, die einen Bildschirm benötigen. Unter Windows gibt es kein sudo – die Karte erscheint dort nicht.

## Gespräch ohne Lernen

Mit dem Schalter „Ohne Lernen" unter dem Eingabefeld lernt die Memory aus diesem Gespräch nichts, und zwar ab der ersten Nachricht. Das Modell sieht die Memory weiterhin, aber aus dem Gespräch wird nichts Neues gespeichert, und auch die Markierung „Hilfreich" lehrt darin nichts.

## Stimme und Meetings

Das Mikrofon unter dem Eingabefeld: Damit kannst du einen Befehl einsprechen oder ein Meeting aufnehmen. Ein Befehl wird über das Mikrofon aufgenommen, auf deinem Computer erkannt und als Nachricht gesendet, die Audiodatei wird gelöscht. Bei einer Meeting-Aufnahme werden das Mikrofon und der Computerton auf zwei Kanälen aufgezeichnet, daher ist im Transkript zu sehen, wer spricht. Du kannst auch einfach eine Audio- oder Videodatei in den Chat ziehen (auch .mov vom iPhone, .mp4, .avi, .3gp, .m4v). Falls das Erkennungsmodell noch fehlt, muss es einmalig heruntergeladen werden (etwa 0,5 GB, Internetverbindung nötig) – Mnemai sagt dir Bescheid. Die Spracherkennung läuft über faster-whisper auf deinem Computer (Modell small oder medium, falls heruntergeladen). Alternativ geht auch das Cloud-Whisper mit einem OpenAI-Schlüssel: Das kostet $0.006 pro Minute, etwa $0.36 pro Stunde. Der Modus „Entscheidet selbst" (Standard) misst die Geschwindigkeit deines Computers in der ersten Minute und fragt wegen der Cloud nach, falls die Verarbeitung nicht in der Länge des Meetings oder in 10 Minuten fertig wäre. Audio und Расшифровка.md bleiben in 80 Meetings; im Chat landen das Transkript und eine kurze Zusammenfassung, und deine Worte fließen ins Lernen ein. Im Aufnahmefenster des Meetings gibt es oben rechts „Einstellungen" – das führt zu Einstellungen → Meeting-Aufnahmen. Dort ist der Weg eines Meetings in vier Schritten dargestellt: Aufnahme (ob das Audio gespeichert wird), Transkription (wo und mit welcher Genauigkeit), Zusammenfassung (welches Modell die Zusammenfassung erstellt), Gedächtnis (lernt aus deinen Worten). Klick auf einen Schritt, und darunter siehst du seine Beschreibung und die Einstellungen. Ganz oben findest du fertige Voreinstellungen: „Privat" (alles auf dem Computer, Audio wird gelöscht), „Ausgewogen" (entscheidet selbst), „Schnell" (Cloud-Whisper). Das Modell für die Zusammenfassung kannst du auch direkt im Aufnahmefenster auswählen.

## Integriertes Modell auf dem Computer

In Mnemai ist ein llama.cpp-Server integriert. Zur Auswahl stehen 13 GGUF-Modelle von Hugging Face in fünf Gruppen: leichte (Gemma 3 1B, Qwen2.5 1.5B, Llama 3.2 3B), ausgewogene (Gemma 3 4B – empfohlen, Qwen3 4B, Phi-4 mini), intelligente (Qwen2.5 7B, Llama 3.1 8B, YandexGPT 5 Lite 8B), besondere (Qwen3 4B Thinking, Qwen2.5 Coder 7B) und große (Gemma 3 12B, Mistral Small 3.2 24B). Bei jedem Modell siehst du, wofür es gedacht ist, wie groß es ist, wie viel Speicher es braucht und wie lange der Download bei deiner Verbindung dauert. Der Download lässt sich pausieren und später fortsetzen. Die Modelle liegen in ~/.mnema/models. Das Ganze funktioniert offline und kostenlos, ist aber schwächer als die Cloud-Modelle.

Solange ein Modell auf dem Computer ausgewählt ist, zeigt die Kopfzeile des Chats ein Thermometer an: die Prozessorauslastung, den Anteil des Modells, den Speicher und die Temperatur, sofern das System sie liefert (unter Windows nicht immer, unter Linux meist, unter macOS nicht). Wenn das Modell den Computer eine Minute lang aufheizt, senkt Mnemai selbstständig dessen Priorität und teilt dir das mit. Es gibt die Schaltflächen „Auslastung senken" und „Modell stoppen".

## Engine: Token und Last

„Einstellungen → Engine“, drei Modi:

| Modus | Genauer ↔ Sparsamer | Antwortlänge | Kerne | Kontext | Lernen |
|---|---|---|---|---|---|
| Sparsam | sparsamer (3.000 Zeichen Speicher) | bis zu 1.000 Token | ein Viertel | 4.096 | alle 2 Stunden |
| Ausgewogen (Standard) | ausgewogen (4.200) | 3.000 | die Hälfte | 8.192 | alle 30 Minuten |
| Maximum | maximal genau (16.000, ohne Kürzungen) | 8.000 | alle bis auf einen | 16.384 | alle 10 Minuten |

Die Feineinstellung ist eine einzige Spalte: „Genauer ↔ Sparsamer“, längste Antwort, Monatslimit, Prozessorkerne, wie viel sich Mnemai gleichzeitig merkt. Sobald du einen Regler manuell verschiebst, wechselt der Modus auf „Benutzerdefiniert“. Das Monatslimit zählt Cloud-Token; ist es aufgebraucht, werden Cloud-Anfragen mit einer verständlichen Meldung gestoppt, während das Modell auf deinem Computer weiterarbeitet. Die Antwortlänge von Claude über ein Abo lässt sich nicht begrenzen.

Darunter folgt ein eigener Bereich „Im Hintergrund“: „Arbeit nicht stören“ senkt die Priorität des Modells auf deinem Computer, „Lernen im Hintergrund“ legt fest, wie oft Mnemai die Lernquellen prüft.

## Wer von den KIs was sieht

Einstellungen → Sicherheit → „Wer von den KIs was sieht" — Tabelle: KIs in den Spalten, Speicherbereiche in den Zeilen, Block für gesperrte Themen (Geld, Gesundheit, Persönliches — werden auch aus freigegebenen Bereichen ausgeblendet). Änderungen werden sofort gespeichert, der Schalter unter der Spalte deaktiviert diese KI vollständig. Standardmäßig ist nichts verborgen, und jede KI kann Neues in den Posteingang legen:

| KI | Sieht | Kann ergänzen |
|---|---|---|
| Lokales Modell (integriert, Ollama, Strata) | alles | Posteingang |
| Claude, Claude Code | alles | Posteingang, Entscheidungen, Projekte, Karten, Personen, Regeln |
| ChatGPT | Profil, Regeln, Projekte, Karten, Entscheidungen | Posteingang |
| OpenRouter, DeepSeek, YandexGPT | Profil, Regeln, Projekte, Karten, Entscheidungen | Posteingang |
| Gemini | Profil, Regeln, Karten | Posteingang |
| Cursor | Regeln, Projekte | Posteingang |

Das lokale Modell sieht alles, weil keine Daten den Computer verlassen. Geld, Gesundheit und Persönliches sind standardmäßig für alle KIs sichtbar, denen Karten freigegeben sind: Um ein Thema vor einer KI zu verbergen, klicke in ihrer Spalte auf „sichtbar" – daraus wird dann „verborgen". Bei MCP blockiert ein langer Befehl die Antwort nicht: Der Client erhält Fortschrittsmeldungen und kann den Befehl abbrechen; sudo über MCP wird nur nach Eingabe des Passworts im Mnemai-Chat ausgeführt, und MCP öffnet kein Terminalfenster.

Ein versteckter Tag an einer Überschrift (z. B. „## Деньги #money") verbirgt diese und alles darunter. Ein Tag im Dateititel („# Деньги #money") oder in den Dateieigenschaften (tags) verbirgt die gesamte Datei. Auch russische Tags funktionieren – #деньги, #здоровье, #личное – in jeder Groß-/Kleinschreibung, ebenso Eigenschaften im Format, das Obsidian für tags (als Liste) verwendet. Eine Statusänderung bei einer verborgenen Karte erscheint im Aktivitäts-Feed mit demselben Tag und ist daher ebenfalls verborgen.

## Was den Computer verlässt

Bevor eine Anfrage an eine Cloud-KI geht (Chat, Konsortium, zweiter Durchgang, Gesprächstitel, Lern-Gehirn, Porträt) und bevor eine Anfrage an Suchmaschinen geht, werden Kartennummern (mit Luhn-Prüfung), Passwörter, PINs und CVV, API-Schlüssel, Tokens und VPN-Schlüssel, Telefonnummern, Reisepass, SNILS, INN und Kontonummern durch Platzhalter wie [TELEFON-1] ersetzt. Die Antwort kommt mit den echten Werten zurück, und zwar erst auf deinem Computer. Du schaltest das unter „Einstellungen → Sicherheit" ein. Das Lern-Gehirn bekommt bei einer fremden Cloud die Erinnerungen nach denselben Regeln wie die KI im Chat: Versteckte Themen werden ihm nicht geschickt. Jede Anfrage nach außen ist ein Eintrag im Protokoll: wann, an wen, wofür (Antwort im Chat, Lernen, Porträt, Gesprächstitel, Websuche), wie viele Zeichen, wie viel von dem verfügbaren Gedächtnis weitergegeben wurde und was ausgeblendet wurde (nur die Anzahl, nicht die Werte). Eine Anfrage, die nicht rausgegangen ist (kein Programm, kein Schlüssel, keine Verbindung), wird nicht ins Protokoll geschrieben. „Nach außen diese Woche" in der Karte „Gedächtnis" unten links zeigt den Bericht für die letzten 7 Tage.

## Speicher mit Passwort verschlüsseln

"Einstellungen → Sicherheit → Speicher mit Passwort verschlüsseln", unter Windows, macOS und Linux. Dasselbe wird dir beim ersten Start im Schritt "Speicher mit Passwort schützen?" angeboten: Standardmäßig ist kein Passwort gesetzt, du kannst ein eigenes eingeben oder auf "Sicheres Passwort generieren" klicken. Bei einem verschlüsselten Speicher sendet die Synchronisierung mit Google Drive, Dropbox, einem eigenen Ordner oder einer Station nur verschlüsselte Dateien; eine Kopie mit einem anderen Passwort wird nicht akzeptiert und überschreibt deine nicht. Mnemai verschlüsselt Notizen und Systemdateien mit dem, was du gesagt und getan hast, selbst: Gespräche, Text von Anhängen, das Protokoll und seine Snapshots für den Rollback, Lernspuren, den Bericht darüber, was nach außen gegangen ist, das Profil. Ohne Passwort lassen sie sich nicht lesen, selbst wenn man den Ordner kopiert.

| | |
|---|---|
| Funktionsweise | Ein zufälliger Speicherschlüssel (AES-256-GCM) verschlüsselt die Dateien, das Passwort verschlüsselt diesen Schlüssel per scrypt; beide liegen in .mnema/crypto.json |
| Passwort | mindestens 8 Zeichen, nicht wiederherstellbar: Wenn du es vergisst, ist der Speicher verloren. Du kannst es jederzeit ändern, die Dateien werden dabei nicht neu geschrieben |
| Auf diesem Computer merken | Der Schlüssel liegt im geschützten Speicher des Systems (Windows – DPAPI, macOS – Schlüsselbund, Linux – Passwortspeicher, falls vorhanden, sonst eine Datei im Home-Ordner, die nur du lesen kannst): Mnemai öffnet sich ohne Nachfrage. Ist die Option aus, wird bei jedem Start nach dem Passwort gefragt; bis dahin zeigt Mnemai nichts an und lernt nichts |
| Was nicht verschlüsselt wird | Binärdateien (PDF, Word, Bilder, Meeting-Aufnahmen) – sie werden von anderen Programmen geöffnet; Einstellungen, die vor der Passworteingabe gebraucht werden (Sprache, Modelle, Zugriffsrechte der KI); Ordner anderer Programme (.obsidian und ähnliche) |
| Preis | Obsidian und andere Editoren können verschlüsselte Notizen nicht öffnen. Eine Notiz, die ein anderes Programm in den Ordner geschrieben hat, verschlüsselt Mnemai beim nächsten Öffnen |
| Abbruch mittendrin | Die Dateien werden einzeln verschlüsselt: Jede wird daneben geschrieben, es wird geprüft, dass sie sich genauso zurücklesen lässt, und erst dann ersetzt sie die alte. Wenn der Computer mittendrin ausgeschaltet wird, bleibt ein Teil der Dateien unverschlüsselt, alle sind lesbar, und beim nächsten Öffnen verschlüsselt Mnemai den Rest nach |
| Claude Code, Cursor (MCP) | erhalten den Speicher wie bisher, wenn Mnemai läuft oder das Passwort auf diesem Computer gespeichert ist |

"Verschlüsselung aufheben" (derselbe Schalter, Passwort erforderlich) stellt normale Dateien wieder her.

Unter Windows gibt es außerdem die Verschlüsselung per Systemfunktion (EFS): Sie arbeitet transparent für dich, für Mnemai und für andere Programme, der Schlüssel ist dein Windows-Benutzerkonto; sie ist unter Windows Home nicht verfügbar.

## Verlauf und Rückgängig-Machen

Jeder Eintrag in den Speicher landet in einem Protokoll: wer ihn geschrieben hat, was und wann. Im Bereich „Speicher" → „Verlauf" lässt sich jede Änderung mit einem Klick rückgängig machen. Wurde die Datei danach noch geändert, entfernt das Zurücksetzen nur die Zeilen dieses Eintrags und lässt spätere Änderungen bestehen; es verweigert sich nur, wenn genau diese Zeile bereits von Hand angepasst wurde. Vor der ersten Änderung einer Datei am Tag legt Mnemai eine Kopie in 95 Saves ab, die zwei letzten bleiben erhalten. Einträge aus dem Chat, aus dem Lernen und von anderen KIs werden nacheinander abgearbeitet, daher gehen gleichzeitige Einträge nicht gegenseitig verloren. Hat sich eine Datei im Mnemai-Editor geändert, während du sie bearbeitest, überschreibt Mnemai sie nicht, sondern bittet dich, sie neu zu öffnen.

Wird eine Regel mit anderen Worten ausgedrückt („Fass Gespräche kurz zusammen" und „Mach die Zusammenfassungen kurz"), fügt Mnemai keine zweite Zeile hinzu, sondern formuliert die bisherige Zeile mit den neuen Worten um.

## Verbindung anderer KI-Dienste

- Claude Code, Claude Desktop, Cursor: Einstellungen → „KI und Modelle" → „Speicher in anderen KI-Diensten" → „Verbinden" auf der Kachel. Verbindung über MCP: memory_context, memory_search, memory_remember, memory_stale, memory_journal, memory_undo. Der Kontext wird in Abschnitte von bis zu 9 000 Zeichen aufgeteilt. Cursor erhält nur Regeln und Projekte und schreibt nichts zurück. Auf der Kachel ist zu sehen, ob die Verbindung bereits besteht.
- ChatGPT: entweder per OpenAI-Schlüssel über die OpenAI-Kachel oder per ChatGPT-Abonnement über das separate „Sign in with ChatGPT"; für Antworten muss der Codex CLI App Server installiert sein. Gemini wird mit dem eigenen Google AI Studio-Schlüssel verbunden. Eine Browser-Erweiterung gibt es nicht: alles, was die KI-Dienste selbst nicht können, erledigt Mnemai lokal auf dem Computer.
- Über MCP sieht jeder KI-Dienst im Journal nur die Einträge, die er lesen darf, und macht nur seine eigenen Einträge rückgängig. Nach einem Update von der portablen Version wechselt die Verbindung in Claude und Cursor automatisch auf das neue Programm.
- Modelle: Einstellungen → „KI und Modelle". Oben — „Antwortet gerade": die Medaille des Standardmodells und dessen Auswahl. Darunter — „Modelle" in zwei Abschnitten: „Kostenpflichtig" (Unterabschnitt „Per Abonnement" — Claude und ChatGPT per Abonnement; Unterabschnitt „Per API-Schlüssel" — Claude · API-Schlüssel, ChatGPT · API-Schlüssel, DeepSeek, Gemini, OpenRouter, OpenCode Go, YandexGPT; API wird separat abgerechnet, OpenCode Go per Abonnementschlüssel) und „Kostenlos" (eingebautes Modell, Ollama und Strata, auf diesem Computer). Genauso aufgeteilt sind das Modellmenü oben links und der Schritt „Mit welcher KI sprechen?" beim ersten Start. Kacheln sind gleichwertige Medaillen in den Farben des Anbieters: eingebaut, Claude per Abonnement, Claude · API-Schlüssel (Anthropic), ChatGPT per Abonnement (offizielles Sign in with ChatGPT + Codex App Server), ChatGPT · API-Schlüssel, OpenCode Go, Gemini, OpenRouter, Ollama. ChatGPT lässt sich auf zwei Wegen verbinden: Der OpenAI-API-Schlüssel wird nach Verbrauch separat abgerechnet, das ChatGPT-Abonnement wird über das offizielle Fenster „Sign in with ChatGPT" und eine separate Zustimmung zur Nutzung des Planlimits verbunden. Mnemai speichert eigene OAuth-Token im Systemspeicher und liest den Codex CLI-Login nicht aus; für die Generierung muss der Codex App Server installiert sein. Ein Gemini Advanced-Abonnement liefert keinen Google AI Studio-Schlüssel: die API wird separat abgerechnet. Verbundene Kacheln sind farbig mit dem Status „verbunden", nicht verbundene grau. Auf der Kachel gibt es eine Schaltfläche: „Schlüssel eingeben" → das Schlüsselfeld öffnet sich direkt in der Kachel → „Speichern und Modelle suchen" oder „Abbrechen"; bei Ollama eine Adresse, beim eingebauten Modell „Auswählen und herunterladen". Claude per Abonnement erscheint automatisch, wenn Claude Code auf dem Computer vorhanden ist: Mnemai sucht es nicht nur in den Programmsuchpfaden, sondern auch dort, wo Installer es ablegen (offizieller Installer, npm, WinGet, Volta, bun, Homebrew), sowie innerhalb der Claude Desktop-App. Ist Claude Code gefunden, aber kein Account angemeldet, erscheint auf der Kachel die Schaltfläche „Anmelden": Ein Claude Code-Fenster öffnet sich, dort erfolgt die Anmeldung per Abonnement, danach „Erneut prüfen". Ist Claude Code nicht gefunden — „Installationsanleitung". Jeder verbundene KI-Dienst hat eine Schaltfläche „Deaktivieren": er verschwindet aus allen Modelllisten (Chat, Konsortium, „Mit und ohne Speicher"), Schlüssel und Einstellungen bleiben erhalten, „Aktivieren" stellt ihn wieder her. Ist ein KI-Dienst verbunden, antwortet aber nicht wegen eines Kontoproblems — erschöpftes Limit oder abgelaufenes Claude-Abonnement, kein Guthaben, veralteter Claude Code-Login, abgelehnter Schlüssel —, zeigt die Kachel „funktioniert nicht" und den Grund an, der KI-Dienst verschwindet aus den Listen, und der nächste funktionierende antwortet stattdessen. Die Schaltfläche „Erneut prüfen" sendet eine kleine echte Anfrage. Das Modellmenü oben links ist für alle KI-Dienste gleich aufgebaut: Für jeden verbundenen gibt es die drei besten Modelle (die neuesten vollständigen, dann leichte Mini- und Flash-Modelle) und einen Link „Alle Modelle" mit Zähler. Unter „Alle Modelle" stehen zuerst funktionierende Modelle, darunter nach einem Trennstrich „Alte und Dienstmodelle": vergangene Generationen (gpt-3.5, gpt-4, Claude 3), datierte Kopien, Modelle für Bilder, Sprache und Suche. Das ausgewählte Modell ist im Menü sichtbar, auch wenn es nicht zu den drei besten gehört. Schlüssel und Prüfung sind unterhalb der Liste eingeklappt. Ein erschöpftes Limit versucht Mnemai nach einer halben Stunde automatisch erneut. Der Schlüssel wird sofort beim Speichern geprüft: ein falscher Schlüssel gilt nicht als verbunden. Unter „Speicher in anderen KI-Diensten" läuft auf der Kachel eines verbundenen Dienstes entlang der Linie Mnemai → Programm ein Punkt.
- Eingebautes Modell: Einstellungen → „KI und Modelle" → „Lokales Modell".

## Proxy und VPN

Alles, was ins Internet geht (Modelle, Suche, Herunterladen von Modellen), läuft über einen einzigen Proxy: zuerst den, der in Mnemai festgelegt ist (beim ersten Start, im Tray-Menü unter „Proxy …", unter „Einstellungen" → „Programm" → „VPN und Proxy"), sonst den Systemproxy (Windows; macOS — Systemeinstellungen → Netzwerk; Linux — die Variablen https_proxy und die GNOME-Einstellung), sonst direkt. HTTP und SOCKS5 werden mit Benutzername und Passwort unterstützt, das Passwort liegt im geschützten Speicher des Systems. VPN per Schlüssel: Füge einen Link vless://, vmess://, trojan://, ss:// oder ein Abo https:// ein, und Mnemai startet Xray nur für sich selbst („Schlüssel importieren" aus der Zwischenablage oder „Schlüssel manuell eingeben"). Es geht auch über einen bereits laufenden VPN-Client. „Prüfen" erreicht Anthropic über den Proxy und sagt dir, was nicht stimmt. Das integrierte Modell läuft nicht über den Proxy.

## Fenster, Tray, Installation

Beim ersten Start gibt es eine kurze Einführung: sechs Anwendungsfälle, je ein Gedanke pro Bildschirm (kein erneutes Erklären nötig, ein Gedächtnis für alle KIs, weniger Token in jeder KI, Meeting → Aufgaben, merkt sich Lösungen und Fristen, Geheimnisse bleiben bei dir) und Auswahl der KI. Der Anwendungsfall zu Token zeigt eine Messung aus dem Abschnitt "Token-Ersparnis": Frage zu einem Vertrag mit 153.000 Zeichen, 29.643 Eingabe-Token für den ganzen Text gegenüber 6.159 mit Mnemai. "Überspringen" schließt die Einführung sofort.

Beim Schließen des Fensters wird es in den Tray verschoben, das Lernen läuft weiter; beim ersten Mal fragt Mnemai "in Tray oder beenden" und merkt sich die Antwort. "Beenden" im Tray-Menü stoppt alles. Im Tray-Menü: "Mnemai öffnen", "Jetzt lernen", "Lernen pausieren", "Proxy…" und Autostart ("Mit Windows starten", auf macOS "Beim Anmelden in macOS öffnen", auf Linux "Beim Systemstart starten"). Ein erneuter Start öffnet keine zweite Instanz, sondern zeigt das Fenster der ersten. Unter Windows entfernt Mnemai beim Start selbst Tray-Symbole abgestürzter Prozesse. Falls der Linux-Desktop keinen Tray anzeigt, beendet das Schließen des Fensters das Programm.

Mnemai prüft Updates selbst: im Hintergrund, alle sechs Stunden, ohne Fenster und Fragen. Wenn eine neue Version erscheint, taucht neben dem Zahnrad eine unauffällige Schaltfläche "Aktualisieren" mit der Versionsnummer auf. Sie lädt die zum System passende Datei herunter und aktualisiert das Programm: unter Windows startet der Installer beim Beenden, unter Linux ersetzt die neue Datei das Programm und es startet neu, unter macOS öffnet sich das .dmg-Image — du musst Mnemai nur noch in "Programme" ziehen. "Später" verschiebt die Erinnerung bis zur nächsten Version, und manuell prüfen kannst du über das Zahnrad mit der Schaltfläche "Prüfen". Hintergrundprüfungen werden in config.json deaktiviert: "auto_update": false, oder durch Start mit MNEMA_NO_UPDATE=1.

Der Installer installiert Mnemai ohne Administratorrechte in %LOCALAPPDATA%\Programs\Mnemai, findet alte Versionen und löscht nur deren Programmdateien: alles andere in diesem Ordner (zum Beispiel Gedächtnis, das neben dem Programm erstellt wurde) bleibt erhalten. Das Deinstallieren des Programms löscht das Gedächtnis ebenfalls nicht. Es gibt auch eine portable Version als Archiv. Der Installer ist derzeit ohne digitale Signatur: Windows zeigt "Windows hat Ihren PC geschützt" — klicke auf "Weitere Informationen" → "Trotzdem ausführen". Auf einem frischen Windows 10 installiert Mnemai selbst die Fensterkomponente Microsoft WebView2 (Internet wird einmal benötigt). macOS: .dmg-Image, ziehe Mnemai in "Programme". Das Programm ist ohne Apple-Signatur, deshalb öffne es beim ersten Mal per Rechtsklick → "Öffnen" (oder Systemeinstellungen → Datenschutz & Sicherheit → "Trotzdem öffnen"). Linux: eine .AppImage-Datei (mache sie ausführbar und starte sie) oder ein .tar.gz-Archiv mit einem Ordner. Das Fenster unter Linux wird mit Qt gezeichnet; falls es sich nicht öffnet, werden die Pakete libxcb-cursor0 und libfuse2 (für AppImage) benötigt.

Falls beim Start der Gedächtnisordner nicht am richtigen Ort ist (verschoben, umbenannt oder externe Festplatte nicht angeschlossen), sagt Mnemai das und bietet an, den neuen Ort anzugeben, erneut zu prüfen oder ein neues Gedächtnis zu beginnen. Die ersten Bildschirme erscheinen in der Systemsprache. Fehler von Diensten erklärt Mnemai in Worten: was passiert ist und was zu tun ist; der Fehler bleibt im Gespräch, eine abgebrochene Antwort ist markiert, "Stoppen" gibt das Gespräch sofort frei.

## Zahnrad, Design, Sprache, Erfolge

Das Zahnrad oben rechts öffnet: Lernen (oben steht der Status; ist der Speicher eingeschaltet, findest du dort auch den Schalter zum Pausieren des Lernens, ist er ausgeschaltet, steht dort nur der Hinweis "Speicher ausgeschaltet"; außerdem Modus und Verlauf), Design, Sprache, Erfolge (lassen sich ausschalten), "So funktioniert Mnemai" (Tour), "So funktioniert der Speicher" (Guide) und das "Mnemai-Handbuch". Ausgeschaltete Tipps kannst du hier ebenfalls wieder aktivieren: "Tutorial in neuen Gesprächen" und "Hinweis auf teure Gespräche". Das Schließen-Kreuz jedes Fensters ist ein durchsichtiger Kreis mit einem dünnen Kreuz, so groß wie das "?"-Symbol; auch mit Escape lässt sich das Fenster schließen. In einem Gespräch ohne Lernen ist der Punkt am Zahnrad orange, außerhalb eines solchen Gesprächs richtet er sich wieder nach dem Lernstatus. Der Punkt am Zahnrad zeigt den Status an: grün – Mnemai lernt, gelb – Speicher ausgeschaltet oder Lernen pausiert, grau – Mnemai lernt nur ausdrücklich Gesagtes oder das Lernen ist ausgeschaltet. Den Lernstatus siehst du in der Eingabezeile: "Mnemai lernt · Speicher vor N Min. aktualisiert". Gibt es kein Modell zur Auswertung von Sprache, steht dort "Mnemai merkt sich nur direkt Gesagtes": Gespeichert wird nur Ausdrückliches ("merk dir …", Korrekturen, Entscheidungen).

Es gibt neun Sprachen für die Oberfläche: Russisch, Englisch, Chinesisch, Spanisch, Hindi, Portugiesisch, Französisch, Deutsch, Japanisch. Das Modell antwortet in der gewählten Sprache. Gespräche und Speicher werden nicht übersetzt.

Erfolge: 99 Auszeichnungen in fünf Gruppen (Einstieg, Speicherwachstum, Ersparnis und Gewohnheit, Datenschutz, Seltene); die meisten seltenen sind verborgen, bis du sie erhältst. Erfahrungspunkte für Auszeichnungen (10, 25, 50, 100) bringen dich durch Level von "Neuling" bis "Ewiges Gedächtnis".

Im Zahnrad-Menü findest du das "Mnemai-Handbuch" – das ist das Handbuch direkt im Programm: links die Abschnitte, oben die Suche, Treffer werden hervorgehoben. Die Einstellungen öffnen sich immer beim ersten Abschnitt "KI und Modelle". Beim Start zeigt Mnemai kurz einen Startbildschirm: Logo, Name und den Schriftzug "Free Memory AI Interface". Das Zahnrad der Eingabezeile ist klein, sitzt oben rechts neben dem "?" und öffnet die Einstellungen der Eingabezeile.

## Mehrere Gedächtnisse

In den Einstellungen findest du links unter den Bereichen den Block „Gedächtnis": alle Gedächtnisse dieses Computers, das geöffnete ist mit einem Häkchen markiert. Ein Klick auf ein anderes öffnet es. „Neues Gedächtnis" führt zum ersten Bildschirm, das aktuelle bleibt in der Liste. Im Menü ⋮ eines Gedächtnisses gibt es „Umbenennen" – das ändert den Namen in der Liste (der Ordner auf der Festplatte behält seinen Namen) – und „Löschen". Das Löschen fragt zweimal nach: Im zweiten Fenster „Wirklich löschen …?" steht, was verschwindet (Porträt, Fakten, Gespräche, Verlauf), und die Schaltfläche „Löschen" wird erst nach 10 Sekunden aktiv – unter ihr schrumpft ein roter Balken und ein Countdown läuft. Der Ordner landet im Papierkorb, von dort kannst du ihn wiederherstellen. Ein geöffnetes Gedächtnis schließt Mnemai zuerst und wechselt zum nächsten in der Liste, und wenn es keine weiteren gibt, zum ersten Bildschirm.

## Telegram

"Einstellungen → Lernen → „Telegram"". Mnemai liest Telegram über die API und liest ausschließlich: Der Telegram-Client in Mnemai beherrscht nur Anmeldung und Lesen, jeder andere Befehl (senden, löschen, als gelesen markieren, beitreten, Reaktion) wird im Programm selbst abgelehnt, bevor er abgeschickt wird. Die Anmeldung läuft wie in Telegram Desktop: api_id und api_hash von my.telegram.org (API development tools), Telefonnummer, Code aus Telegram und das Cloud-Passwort, falls du eines hast. Darunter findest du „Chats zum Lesen": „Chats hinzufügen" öffnet eine durchsuchbare Liste deiner persönlichen Chats und Gruppen, in der du die gewünschten markierst. Solange kein Chat ausgewählt ist, liest Mnemai nichts. Kanäle und Bots lassen sich nicht auswählen. In den ausgewählten Chats wird der gesamte Verlauf gelesen: Deine Nachrichten sind mit „Ich" gekennzeichnet, die anderen mit dem Namen des Gesprächspartners, sodass Mnemai sowohl dich als auch die Menschen um dich herum kennenlernt. Die Anmeldung wird verschlüsselt im geschützten Speicher des Systems abgelegt, die Chatliste und das Gelernte liegen im Speicherordner; Mnemai hat keine eigenen Server. „Trennen" löscht die Anmeldung; in Telegram bleibt die Sitzung unter „Geräte" bestehen, bis du sie dort beendest.

## Karte „Gedächtnis" unten links

Zwei Zeilen, und jede öffnet einen Beweis: „Lokales Gedächtnis auf dem PC" öffnet den Gedächtnisordner, „Zugriffseinstellungen" öffnet die Tabelle „Welche KI was sieht". Das Zahnrad der Karte führt zu den Schutzeinstellungen, das grüne „?" daneben öffnet den Guide „Wie das Gedächtnis funktioniert" mit 12 Kapiteln: links das Inhaltsverzeichnis, rechts eine Szene, die Erklärung, ein Beispiel (was du sagst und was im Gedächtnis passiert) und die Schaltfläche „Ausprobieren", die dich zu der echten Stelle im Programm bringt. Die Kapitel: der Ordner auf dem Computer, wie der Gedächtnisordner aufgebaut ist, das Datum eines Fakts – wann du es gesagt hast, Lernen aus Gesprächen, sofort speichern oder nachfragen (Schwellen 60 % und 80 %), Korrekturen werden zu Regeln, die Auswahl des Passenden vor der Antwort, Rechte der KI, Geheimnisse, Altes wird neu hinterfragt, Verlauf mit Rücksetzen, das Modell auf dem Computer. Am Ende steht „Selbst prüfen": der Ordner, wer was sieht, was nach außen gegangen ist.

Ausprobieren (Menü „+" unter dem Eingabefeld und Seite „Gedächtnis"):
- „Kennenlernen" – sieben kurze Fragen: wer du bist, wo du wohnst, was gerade am wichtigsten ist, Projekte, Menschen um dich herum, wie man mit dir sprechen soll und was die KI nicht tun darf. Die Antworten landen als ganz normale Fakten im Gedächtnis und überschreiben nichts.
- „Wie gut kennt Mnemai dich?" – ein Quiz aus zehn Fakten aus dem Gedächtnis: „Stimmt" (der Status bekommt das heutige Datum), „Stimmt nicht mehr" (du schreibst, wie es jetzt ist, das Alte wandert ins Faktenarchiv), „Falsch" (der Fakt wandert ins Archiv). Am Ende gibt es eine Punktzahl.
- „Mit und ohne Gedächtnis" – eine Frage an die verbundenen KIs (bis zu drei); jede antwortet zweimal: wie ein normaler Chat ohne Gedächtnis und über Mnemai. Die Antworten stehen nebeneinander.
- „Roast" – ein Konsortium im Roast-Format.

Jedes Ergebnis lässt sich in eine Bildkarte verwandeln („Teilen"): kopieren, unter „Bilder/Mnemai" speichern oder den fertigen Posttext mit Link kopieren. Auf dem Bild steht nur das, was vor dem Senden im Fenster zu sehen ist.

## Was Mnemai nicht kann

- Sie startet keine Programme oder Skripte. Mit Dateien arbeitet sie nur über Aktionen: im Gedächtnisordner und in Arbeitsordnern, jede davon steht im Protokoll und lässt sich rückgängig machen.
- Verschlüsselung über das System (EFS) gibt es nur unter Windows; die Verschlüsselung mit einem Mnemai-Passwort funktioniert überall.
- Bei einem langen Scan werden nur die ersten 40 Seiten erkannt.
- Ohne Internet funktionieren Cloud-Modelle und die Suche nicht. Wenn das Netz mitten im Gespräch ausfällt, antwortet das Modell auf deinem Computer (sofern es heruntergeladen ist) und weist in einer Zeile über der Antwort darauf hin.
- Sie liest weder E-Mails noch Kalender, solange du ihr keine Adresse und kein Passwort oder keinen Link gibst.
