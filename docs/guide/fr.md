<div align="center">

<img src="../img/brand/logo.svg" width="72" alt="Mnemai">

# Guide de Mnemai

Comment fonctionne Mnemai, écran par écran et réglage par réglage. Mnemai répond aux questions sur lui-même à partir de ce même texte.

<sub><a href="en.md">English</a> · <a href="ru.md">Русский</a> · <a href="zh.md">中文</a> · <a href="es.md">Español</a> · <a href="hi.md">हिन्दी</a> · <a href="pt.md">Português</a> · <b>Français</b> · <a href="de.md">Deutsch</a> · <a href="ja.md">日本語</a></sub>

<sub><a href="../../README.fr.md">README</a></sub>

</div>

## Sommaire

- [Qu'est-ce que Mnemai](#quest-ce-que-mnemai)
- [La mémoire est activée ou désactivée](#la-mémoire-est-activée-ou-désactivée)
- [Dossier de mémoire](#dossier-de-mémoire)
- [Dossiers de mémoire supplémentaires](#dossiers-de-mémoire-supplémentaires)
- [Comment un fait est enregistré](#comment-un-fait-est-enregistré)
- [Onglet Mémoire](#onglet-mémoire)
- [Portrait](#portrait)
- [Résumé de 10 Now et table des matières](#résumé-de-10-now-et-table-des-matières)
- [Comment Mnemai apprend](#comment-mnemai-apprend)
- [Sources d'apprentissage](#sources-dapprentissage)
- [Modes d'apprentissage](#modes-dapprentissage)
- [Comment Mnemai comprend les textes](#comment-mnemai-comprend-les-textes)
- [Comment Mnemai décide : enregistrer ou demander](#comment-mnemai-décide--enregistrer-ou-demander)
- [Fil d'apprentissage et question en cours de conversation](#fil-dapprentissage-et-question-en-cours-de-conversation)
- [Chat et modèles](#chat-et-modèles)
- [Sessions](#sessions)
- [Comment répond Mnemai](#comment-répond-mnemai)
- [Ce que le modèle sait à chaque message](#ce-que-le-modèle-sait-à-chaque-message)
- [Fichiers et documents, y compris les PDF](#fichiers-et-documents-y-compris-les-pdf)
- [Internet](#internet)
- [Plus précis ou plus économe](#plus-précis-ou-plus-économe)
- [Questions à choix, seconde passe, citation](#questions-à-choix-seconde-passe-citation)
- [Tâches récurrentes](#tâches-récurrentes)
- [Aide pour les termes](#aide-pour-les-termes)
- [Consortium](#consortium)
- [Actions sur l'ordinateur](#actions-sur-lordinateur)
- [Mot de passe administrateur](#mot-de-passe-administrateur)
- [Conversation sans apprentissage](#conversation-sans-apprentissage)
- [Voix et réunions](#voix-et-réunions)
- [Modèle intégré sur ton ordinateur](#modèle-intégré-sur-ton-ordinateur)
- [Moteur : jetons et charge](#moteur--jetons-et-charge)
- [Qui parmi les IA voit quoi](#qui-parmi-les-ia-voit-quoi)
- [Ce qui quitte ton ordinateur](#ce-qui-quitte-ton-ordinateur)
- [Chiffrement de la mémoire par mot de passe](#chiffrement-de-la-mémoire-par-mot-de-passe)
- [Historique et annulation](#historique-et-annulation)
- [Connexion d'autres IA](#connexion-dautres-ia)
- [Proxy et VPN](#proxy-et-vpn)
- [Fenêtre, barre d'état système, installation](#fenêtre-barre-détat-système-installation)
- [Engrenage, thème, langue, succès](#engrenage-thème-langue-succès)
- [Plusieurs mémoires](#plusieurs-mémoires)
- [Telegram](#telegram)
- [Carte « Mémoire » en bas à gauche](#carte--mémoire--en-bas-à-gauche)
- [Ce que Mnemai ne sait pas faire](#ce-que-mnemai-ne-sait-pas-faire)

## Qu'est-ce que Mnemai

Mnemai est un programme de mémoire pour n'importe quelle IA. Il retient qui tu es, sur quoi tu travailles, quelles décisions tu as prises et comment te parler, et il injecte tout cela dans la conversation avec n'importe quel modèle : Claude, ChatGPT, Gemini, le modèle intégré sur ton ordinateur, Cursor et les agents. La mémoire est un dossier de simples fichiers Markdown sur ton ordinateur ; tu peux l'ouvrir dans n'importe quel éditeur (y compris Obsidian), même sans Mnemai. Mnemai n'a ni cloud ni compte. Le programme se compose d'une seule fenêtre (chat, mémoire, paramètres) et d'une icône dans la zone de notification (sur macOS, dans la barre des menus). Il fonctionne sous Windows 10 et 11, macOS 11 et versions ultérieures (Apple Silicon et Intel) et Linux (64 bits, Ubuntu 22.04 et versions ultérieures, ainsi que les distributions similaires). La version personnelle est gratuite et open source (licence AGPL-3.0) ; la version pour les entreprises est proposée séparément.

## La mémoire est activée ou désactivée

La mémoire est l'interrupteur principal de Mnemai : le commutateur se trouve dans le panneau "Mémoire", en bas à gauche du chat (le même que dans Réglages → Apprentissage → "Mémoire"). Tant que la mémoire est désactivée, le point sur l'engrenage en haut à droite est jaune. Une nouvelle mémoire créée sur le premier écran démarre désactivée : le tutoriel comporte une étape "Activer la mémoire ?" (par défaut "Sans mémoire"), et si le tutoriel n'a pas été affiché, la même question apparaît dans une fenêtre à part. Une mémoire qui existait avant l'apparition de l'interrupteur reste activée.

Quand elle est désactivée, c'est un chat ordinaire avec n'importe quelle IA : le modèle ne sait rien de son propriétaire, Mnemai ne retient rien (l'apprentissage est à l'arrêt, "retiens" n'écrit rien, l'action "écrire dans la mémoire" est refusée), et Claude Code, Claude Desktop et Cursor ne reçoivent pas la mémoire et ne peuvent pas y écrire. Tout le reste fonctionne : tous les modèles, le consortium, les documents et l'économie de tokens qui leur est associée, internet, les réunions, les modèles locaux, les actions sur les fichiers dans les dossiers de travail (le dossier de la mémoire est fermé aux actions). L'onglet "Mémoire" affiche l'écran "Mémoire désactivée" avec les boutons "Activer la mémoire" et "Voir ce qui est enregistré". Les réglages d'apprentissage et "Qui voit quoi parmi les IA" sont grisés, avec la mention "Mémoire désactivée" et un bouton "Activer", le bouton "Sans apprentissage" dans le chat est inactif, et la barre d'état affiche "Mémoire désactivée · chat ordinaire, rien n'est retenu".

## Dossier de mémoire

La mémoire se trouve dans le dossier que tu as choisi au premier lancement. Voici ce qu'il contient :

| Dossier ou fichier | Contenu |
|---|---|
| 00 Inbox/Inbox.md | faits non triés |
| 10 Now.md | résumé du jour : qui tu es, projets actifs, derniers événements, faits récents des 14 derniers jours, statuts de plus de 30 jours à vérifier. Il se génère tout seul, ne le modifie pas à la main |
| 20 Projects/<nom>/_Project.md | page centrale du projet : statut (active, paused, closed), objectif, date de début, mots-clés, journal. Les documents du projet sont rangés à côté |
| 30 People/<nom>.md | fiche d'une personne |
| 60 Events/AAAA-MM.md | décisions et changements de statut par mois, les plus récents en haut |
| 70 Memory/Profile.md | qui tu es |
| 70 Memory/Rules.md | comment travailler avec toi, une règle par ligne avec sa date |
| 70 Memory/Thoughts.md | tes pensées et tes idées |
| 70 Memory/Cards/<thème>.md | fiche d'un thème : un fait par ligne, mots-clés et tags cachés en en-tête |
| 70 Memory/Fact archive/ | faits remplacés par des faits plus récents. C'est l'historique, les modèles ne le reçoivent pas |
| 70 Memory/Index.md | sommaire : projets, fiches et personnes avec leurs mots-clés. Il se génère tout seul |
| 80 Meetings/ | comptes rendus de réunions, transcriptions et résumés |
| 90 System/Journal/<jour>.md | journal : ce qui a été enregistré et par qui, en langage clair |
| 90 System/Recipes/ | recettes pour les tâches récurrentes |
| 95 Saves/ | copie d'un fichier avant sa première modification de la journée, les deux dernières sont conservées |
| 99 Archive/ | projets clos avec leurs documents |
| .mnema/ | fichiers techniques : accès des IA, journal des modifications, instantanés pour la restauration, jetons, paramètres d'apprentissage, conversations |

Tu peux modifier les fichiers de la mémoire à la main. Mnemai ne lit que cette structure.

## Dossiers de mémoire supplémentaires

Paramètres → Application → "Dossiers de mémoire supplémentaires" : d'autres dossiers que les IA voient en plus de la mémoire principale. N'importe lequel convient : notes, coffre Obsidian, documents, dossier partagé d'équipe ou encore une autre mémoire Mnemai. Le bouton "Connecter Obsidian" trouve tout seul les coffres Obsidian présents sur ton ordinateur (d'après les réglages d'Obsidian lui-même) et les affiche avec leur nombre de notes : ceux que tu coches deviennent une mémoire supplémentaire, et tu peux aussi indiquer le dossier manuellement. Tout autre dossier s'ajoute avec le bouton "Ajouter" (ou "Choisir…"), et se retire avec "Retirer" à côté. Le coffre est lu en entier une seule fois en arrière-plan, puis seules les notes modifiées sont relues, si bien que même des milliers de notes ne ralentissent pas les réponses. Les fichiers Markdown et texte sont lus sur ton ordinateur, et seuls les passages pertinents sont envoyés avec ta question, dans la limite du même volume que la mémoire (curseur "Plus précis ↔ Plus économe"). Les thèmes masqués pour cette IA (#money, #health, #private et leurs équivalents russes) sont également supprimés de ces fichiers. Mnemai n'écrit rien dans ces dossiers et n'apprend pas à partir de leur contenu.

## Comment un fait est enregistré

Un fait, c'est une ligne avec une date : "- 21.09.2026 · On a décidé de lancer le pilote en novembre". Le statut s'écrit avec la mention "(statut JJ.MM.AAAA)". Un nouveau statut portant sur le même sujet remplace l'ancien à sa place, l'ancien part dans l'archive des faits, et le changement apparaît dans le fil des événements. Ce que Mnemai a appris elle-même est marqué du mot "appris", pour que l'on voie clairement ce qui vient de l'apprentissage.

La date d'un fait appris est le jour où tu l'as dit ou écrit, et non le jour où Mnemai l'a lu. Si Mnemai lit aujourd'hui une conversation vieille d'un mois, le fait recevra la date de cette conversation, et la décision sera classée dans les événements de ce mois-là. Ainsi, une information ancienne n'est pas présentée comme une nouveauté.

Mnemai ne sort pas les statuts de plus de 30 jours dans une liste à part. Le modèle connaît la date de chaque statut : si la conversation porte sur un statut de plus d'un mois, il indique de quelle date il date et demande s'il est toujours d'actualité.

## Onglet Mémoire

Mémoire → Portrait : en haut, ton portrait avec des compteurs de faits ; en dessous, la « Carte de la mémoire » — les thèmes sous forme de bulles autour de toi : la taille dépend du nombre de faits, un cadenas marque les thèmes que toutes les IA ne voient pas, et ce qui a été mis à jour ces trois derniers jours pulse. Le libellé d'une petite bulle s'affiche au survol. Sous la carte, des tuiles de thèmes : « Règles pour l'IA », « Projets », « Les gens autour de toi », les sections du portrait, les fiches de thèmes (les plus grandes en premier) et « Événements et décisions ». Chaque tuile affiche le nombre de faits et deux lignes récentes (pour les projets et les personnes, ce sont les premiers noms). Un clic sur une tuile ou une bulle ouvre le thème dans une fenêtre superposée : tous les faits, une ligne par fait, les plus récents en haut, la date à droite, une recherche ; un clic déploie le fait en entier, et pour un fait appris, un « D'où ça vient ? » apparaît au même endroit ; le crayon ouvre le fichier. Les sections du portrait identiques (par exemple « Qui je suis », ouvert et masqué) sont regroupées en un seul thème.

## Portrait

Le portrait tient en 2 ou 3 phrases au début de 70 Memory/Profile.md : qui tu es, ce que tu fais, ce qui compte le plus pour toi en ce moment. C'est la première chose que reçoit chaque IA. Mnemai le rédige elle-même dès qu'elle a réuni au moins trois faits sur toi, tirés des sections ouvertes du profil, des projets actifs et des fiches sans tags masqués (l'argent, la santé et le personnel n'entrent pas dans le portrait). Il est rédigé par le modèle choisi pour l'apprentissage ; sans modèle, Mnemai se contente d'aligner les faits en phrases courtes. Le portrait est régénéré après l'apprentissage : immédiatement si le profil a changé, et au plus une fois toutes les 6 heures si seules des fiches ou des projets ont changé. Si tu réécris le portrait toi-même, Mnemai n'y touche plus. La génération apparaît dans le journal sous la mention « portrait généré » et peut être annulée dans l'historique.

## Résumé de 10 Now et table des matières

Mnemai reconstruit elle-même 10 Now.md et 70 Memory/Index.md après chaque enregistrement. 10 Now contient qui tu es, tes projets actifs, les derniers événements, les faits récents des 14 derniers jours (12 au maximum) et les statuts obsolètes. La table des matières liste chaque projet, chaque fiche et chaque personne avec les mots qui permettent de les retrouver. Inutile de modifier ces fichiers à la main : à la prochaine reconstruction, ta modification sera perdue.

## Comment Mnemai apprend

Mnemai apprend toute seule, au fil de ta vie. Pas besoin de remplir de questionnaires ni de formulaires. Elle repère des faits dans les sources que tu as autorisées, puis décide de les enregistrer tout de suite ou de te poser la question. L'apprentissage se fait en arrière-plan, selon un minuteur (la fréquence dépend du mode du moteur : de 10 minutes à 2 heures), et immédiatement à chaque message que tu envoies dans le chat Mnemai. Au premier lancement, elle parcourt l'historique des 90 derniers jours.

Au premier lancement, Mnemai te demande : « Mnemai peut-elle consulter d'autres programmes ? ». « Non, seulement Mnemai » : elle apprend uniquement de tes conversations avec elle et de tes corrections, et ne travaille qu'avec son propre dossier de mémoire : elle ne lit ni les chats Claude Code, ni les notes, ni les documents, ni Telegram, ni le navigateur, ni l'extension. « Oui, je choisis lesquels » : une liste de ce qui a été trouvé sur l'ordinateur s'ouvre (chats Claude Code, dossier de notes, Documents, export Telegram, historique du navigateur, extension) avec les chemins ; aucun élément n'est coché, et Mnemai ne lit que ce que tu as coché. Elle n'active jamais d'elle-même la messagerie ni le calendrier : il faut pour cela une adresse et un mot de passe, ou un lien secret.

Tout cela se modifie dans « Paramètres » → « Apprentissage ». « Ce que Mnemai peut consulter » est l'interrupteur principal « Autres programmes et navigateur » : s'il est désactivé, les tuiles des sources externes sont verrouillées par un cadenas et ne peuvent pas être activées. Plus bas, dans « Où apprendre », chaque source s'active séparément, et pour certaines tu peux indiquer un chemin et des exclusions.

Mnemai ne lit jamais son propre dossier de mémoire ni ses propres appels de service au modèle.

## Sources d'apprentissage

| Source | Ce qu'elle lit |
|---|---|
| Conversations dans Mnemai | tes messages dans le chat de Mnemai, immédiatement, pendant que tu écris |
| Conversations dans Claude Code | tes messages issus de l'historique de Claude Code (dossier ~/.claude/projects), uniquement les nouvelles lignes. Les requêtes techniques des scripts, marquées au début par une étiquette du type "[SERVICE-NOM]", sont ignorées |
| Export ChatGPT | le fichier conversations.json issu de l'export de données de ChatGPT |
| Tes corrections | les "non, pas comme ça", "je te l'avais dit", "jamais de…" dans tes conversations avec l'IA deviennent des règles pour toutes les IA |
| Dossier de notes | les nouvelles lignes dans les notes, par exemple dans un coffre Obsidian. Les dossiers système (.obsidian, .trash, .git) sont exclus |
| E-mails | tes e-mails envoyés via IMAP, les citations sont supprimées |
| Telegram (conversations via l'API) | l'intégralité des conversations — tes messages et ceux de tes interlocuteurs — uniquement dans les discussions que tu as choisies. Lecture seule, plus de détails dans la section "Telegram" |
| Telegram (export) | tes propres messages issus de l'export de Telegram Desktop |
| Calendrier | un fichier .ics ou un lien iCal secret |
| Documents | les documents Word nouveaux et modifiés, ainsi que les textes et notes du dossier choisi (.docx, .txt, .md) |
| Historique du navigateur | les titres des pages consultées, jour par jour (Chrome, Edge, Yandex Browser). Par défaut, Mnemai se contente d'observer |

## Modes d'apprentissage

Le mode se règle pour chaque source :

| Mode | Ce qui se passe |
|---|---|
| Observation seule | Mnemai montre ce qu'elle aurait retenu, sans rien écrire |
| Toujours demander | Mnemai n'écrit rien d'elle-même : dans une conversation dans Mnemai, elle pose la question ; pour les autres sources, elle se contente de montrer |
| Mixte (par défaut) | Mnemai écrit d'elle-même ce dont elle est sûre. Pour ce qui est personnel ou contredit la mémoire, dans une conversation dans Mnemai, elle te pose la question directement dans la conversation ; pour les autres sources, elle décide seule. Les intuitions fragiles attendent d'être confirmées par une répétition |
| Autonome | Mnemai écrit tout, avec le journal et la restauration comme garde-fous |

Si un fait apparaît dans plusieurs sources, c'est le mode le plus prudent parmi elles qui s'applique.

## Comment Mnemai comprend les textes

Mnemai peut analyser le langage courant de plusieurs façons (Paramètres → Apprentissage → "Modèle de compréhension des textes") :

| Option | Fonctionnement |
|---|---|
| Elle-même (par défaut) | le modèle avec lequel tu discutes par défaut — n'importe quel modèle connecté, dans le cloud ou sur ton ordinateur ; s'il n'y en a aucun, seuls les signaux explicites sont pris en compte |
| Sans modèle | uniquement l'explicite : « retiens … », les corrections, les décisions (« j'ai décidé … »), les dates de statut |
| Claude via abonnement | via Claude Code installé, sans outils, sans hooks ni MCP, la session n'est pas enregistrée |
| Ta propre clé | Anthropic ou un service compatible avec OpenAI ; la clé est stockée dans le coffre sécurisé du système (Windows — DPAPI, macOS — Trousseau d'accès, Linux — gestionnaire de mots de passe, s'il y en a un), et non dans le dossier de mémoire |
| Modèle sur l'ordinateur | intégré ou Ollama, rien ne quitte ton ordinateur |

Avant l'envoi d'un texte à un modèle cloud, les secrets sont remplacés par des marqueurs (voir "Ce qui quitte l'ordinateur").

## Comment Mnemai décide : enregistrer ou demander

- Le seuil de confiance par défaut est de 80 %. À partir de 80 % de confiance, si le fait n'est pas personnel, Mnemai l'enregistre d'elle-même. Entre 60 % et 80 %, elle te pose la question. En dessous de 60 %, elle attend de le croiser une nouvelle fois.
- Une répétition renforce la confiance : deux fois 60 % font 84 %, et le fait est enregistré.
- L'argent, la santé et le personnel arrivent dans une fiche avec le tag #money, #health ou #private : tu peux la masquer à n'importe quelle IA dans le tableau « Qui voit quoi parmi les IA ». Si le sujet est abordé dans une conversation dans Mnemai, elle te demande d'abord sur place : « C'est personnel — je le retiens ? ».
- Contradiction dans la mémoire (« habite à Kazan » contre « originaire d'Ekaterinbourg ») : dans une conversation dans Mnemai, la question est posée sur place (« Maintenant c'est ça », « C'était juste », « Les deux sont vrais ») ; depuis les autres endroits, le nouveau fait remplace l'ancien, et si l'ancienne ligne en disait plus, Mnemai la réécrit en conservant le reste. L'ancienne version part dans l'archive des faits.
- « Ne jamais apprendre ce genre de chose » ajoute une phrase d'arrêt. Annuler dans l'historique une entrée apprise vaut pour un « non » : elle ne reviendra pas.
- Il n'y a pas de file d'attente « en attente de ta réponse » : Mnemai n'accumule pas les questions. Il n'y a jamais plus d'une question sur la mémoire affichée sous la conversation à la fois ; la suivante apparaît après ta réponse.

## Fil d'apprentissage et question en cours de conversation

Le fil « J'apprends de toi » (engrenage → « Fil ») montre ce que Mnemai a lu, ce qu'elle a compris et pourquoi elle a décidé ainsi, par exemple « confiance de 90 % pour un seuil de 80 %, pas personnel — enregistré automatiquement » ou « c'est de l'argent — enregistré dans la partie masquée ». Si la mémoire a besoin de ton avis, une carte « Je précise pour la mémoire » avec des boutons apparaît sous la conversation ; ta réponse est enregistrée immédiatement. Chaque ligne apprise a son « D'où je tiens ça » : la source, tes propres mots, le nombre de fois où l'information est apparue et la raison de l'enregistrement.

## Chat et modèles

Mnemai est un chat avec n'importe quel modèle, tous les modèles sont égaux. Le choix du modèle se fait en haut à gauche du chat, le menu comporte deux groupes :

- Cloud — fonctionnent via Internet : par clé (Anthropic, OpenAI, Gemini, OpenRouter, DeepSeek, YandexGPT ; Mnemai récupère la liste des modèles auprès du fournisseur, et pour YandexGPT depuis le catalogue Yandex Cloud AI Studio) ou par abonnement (Claude Code) ;
- Sur l'ordinateur — gratuits, sans Internet, rien ne sort : modèle intégré (llama.cpp), Ollama et Strata.

Lors de la connexion et via « Vérifier », Mnemai interroge chaque modèle de la liste ChatGPT, Gemini, DeepSeek et YandexGPT avec une courte requête et ne conserve que ceux qui répondent dans le chat : les modèles abandonnés (par exemple o4-mini, gpt-4, o1), les modèles pour l'audio, les images et la voix, ainsi que les modèles réservés à une autre API dans le catalogue OpenAI standard (pro, codex) ne figurent pas dans la liste. Si un fournisseur retire un modèle ultérieurement, dès le premier échec il disparaît de la liste et le chat indique d'en choisir un autre. DeepSeek se connecte avec une clé depuis platform.deepseek.com. YandexGPT se connecte avec la clé API d'un compte de service Yandex Cloud AI Studio (rôle ai.languageModels.user) et l'ID du catalogue dans lequel il a été créé : la fenêtre de connexion comporte deux champs. Modèles YandexGPT : Alice AI LLM, YandexGPT Pro 5.1, YandexGPT Pro 5, Alice AI LLM Flash, ainsi que DeepSeek V4.1 Flash et Qwen3.6 35B issus du même catalogue. Strata est un programme gratuit distinct pour les grands modèles (Qwen, DeepSeek) sur ta propre carte graphique (github.com/Niko1221/Strata) : installe-le, lance un modèle avec la commande strata launch — Mnemai détecte automatiquement Strata en cours d'exécution sur 127.0.0.1:8080 au démarrage ; pour une autre adresse, renseigne-la dans la fenêtre de connexion Strata.

Ces deux mêmes groupes se retrouvent dans Paramètres → IA et modèles. La limite de longueur de réponse (Paramètres → Moteur) est commune à tous les modèles, y compris Claude par abonnement.

La mémoire et tes règles s'appliquent à chaque message, chaque modèle ne reçoit que ce qu'il est autorisé à voir. Chaque conversation a un titre de 1 à 3 mots. Tu peux le modifier via le crayon à côté du titre, par double-clic sur le titre ou depuis le menu de la conversation dans la liste (Entrée pour valider, Échap pour annuler). Dans une nouvelle conversation, tu peux définir le titre avant le premier message ; il sera enregistré avec celui-ci. Un titre modifié manuellement ne sera plus touché par Mnemai, qui affiche l'heure de la dernière modification et les tokens consommés. La liste se trie par date ou par tokens ; le filtre « IA » affiche les conversations avec un seul modèle.

Le bouton « Laisser Mnemai commencer » dans une conversation vide : le modèle dit bonjour et propose par où commencer, en s'appuyant sur la mémoire. Il qualifie les événements de récents uniquement si leur date le justifie, et suggère de vérifier les décisions vieilles de plus d'un mois.

## Sessions

Le bouton « Nouvelle session » se trouve en haut de la liste, sous « Nouvelle conversation ». Une session regroupe toutes les conversations commencées depuis ton dernier clic : « Nouvelle conversation » ouvre une conversation dans la session en cours, « Nouvelle session » démarre un nouveau groupe. Dans la liste, les conversations d'une même session sont reliées par un trait à gauche ; chaque groupe a un intitulé et, à droite, le nombre de conversations : le groupe du haut s'appelle « Session en cours », les précédents « Session · 24 oct » (le jour de la dernière conversation). Un clic sur l'intitulé replie le groupe, et l'état replié est mémorisé. Juste après « Nouvelle session », aucune ligne vide n'apparaît : le groupe du haut reste la « Session en cours » tant que la nouvelle session ne contient pas sa première conversation. À côté de l'intitulé, un menu ⋮ propose « Renommer » (pour donner ton propre nom au groupe) et « Supprimer » (la session est supprimée avec ses conversations ; les conversations épinglées restent, et ce qui a été appris reste dans la mémoire). Les conversations commencées avant l'apparition des sessions forment une session à part, à la fin de la liste, et les conversations épinglées sont tout en haut, hors des groupes. Pendant une recherche, un tri par tokens ou un regroupement par jours, la liste s'affiche normalement, sans sessions.

À côté des boutons, un « ? » : une animation montre pourquoi rester longtemps dans une même conversation coûte cher, et en quoi une nouvelle conversation diffère d'une nouvelle session.

Chaque conversation n'envoie au modèle que son propre historique. C'est pourquoi la conversation d'une nouvelle session démarre avec un contexte vierge : le modèle reçoit la mémoire et les règles, mais pas les échanges des conversations précédentes. Une longue conversation renvoie un historique de plus en plus volumineux à chaque réponse ; mieux vaut donc lancer un nouveau sujet dans une nouvelle conversation ou une nouvelle session — Mnemai a déjà enregistré dans la mémoire l'essentiel du passé.

Lorsqu'une réponse coûte trois fois plus cher que la première réponse du même modèle dans cette conversation (tokens d'entrée, cache et réponse compris), une carte « La conversation devient coûteuse » apparaît sous cette réponse (elle n'apparaît pas pour un modèle gratuit exécuté sur l'ordinateur). Elle affiche deux barres, la première et la dernière réponse, et indique combien de fois la dernière coûte plus cher. Le bouton « Mettre à jour la mémoire et démarrer une nouvelle session » fait d'abord apprendre à Mnemai toute la conversation en une seule passe, puis démarre une nouvelle session avec un contexte vierge. Un message déjà appris auparavant n'est pas considéré comme un doublon. Dans une conversation sans apprentissage, le bouton se contente de démarrer une nouvelle session. « Ne plus afficher » désactive complètement ce conseil ; pour le réactiver, va dans l'engrenage (« Conseil sur les conversations coûteuses »). La croix sur la carte ne la masque que dans cette conversation.

## Comment répond Mnemai

Paramètres → "Façon de répondre" : prénom, forme d'adresse (tutoiement ou vouvoiement), longueur des réponses (court, droit au but, détaillé), genre — pour les accords (par exemple « prêt » ou « prête »), et personnalité. Tous les choix se font via des tuiles ; à droite, un "Exemple de réponse" : la même question sur le pilote, et la réponse change immédiatement avec les réglages, le prénom dès la saisie. Les personnalités — Douce, Professionnelle, Stricte avec vérifications — sont des médailles avec une échelle de vérifications de une à trois. Plus bas, des ensembles de règles et des règles détaillées par groupe.

## Ce que le modèle sait à chaque message

Avant de répondre, le modèle reçoit :
- comment travailler avec toi : les règles de la section « Comment elle répond » (caractère, façon de s'adresser à toi, tes mots) ;
- la mémoire que ce modèle a le droit de voir (l'en-tête de la mémoire et les lignes liées à ta question) ;
- des informations sur la configuration actuelle de Mnemai : où elle apprend, dans quel mode, avec quoi elle comprend les textes, combien d'entrées contient la mémoire ;
- la date du jour ;
- pour les questions sur Mnemai elle-même : les sections utiles de cette base de connaissances.

Le modèle répond en tant que Mnemai et ne parle de ses capacités que dans la mesure de ce que sait faire Mnemai. Les capacités du moteur sur lequel elle fonctionne (par exemple, les outils de Claude Code) ne font pas partie de Mnemai.

## Fichiers et documents, y compris les PDF

Tu joins un fichier avec le trombone sous le champ de saisie, ou en le glissant dans la fenêtre. Un fichier peut peser jusqu'à 25 Mo. Mnemai l'enregistre à côté de la conversation et en extrait elle-même le texte, sur ton ordinateur et gratuitement.

| Format | Ce que fait Mnemai |
|---|---|
| PDF avec couche de texte | extrait le texte page par page (avec les numéros de page) |
| PDF scanné sans texte | reconnaît le texte sur ton ordinateur (RapidOCR), jusqu'à 40 pages, et le transmet à n'importe quel modèle sous forme de texte. L'alphabet dépend de la langue de l'interface : cyrillique (et anglais) pour le russe, alphabet latin avec diacritiques pour les langues européennes, chinois et anglais pour le chinois et le japonais. Si rien n'a pu être reconnu, le fichier est envoyé tel quel au modèle : seul Anthropic sait alors le lire, avec une clé API |
| PDF protégé par mot de passe | Mnemai t'indique que le fichier est protégé par un mot de passe et te propose de le retirer ("Imprimer → Enregistrer au format PDF") |
| Excel (xlsx, xls), CSV, TSV | tableau feuille par feuille, jusqu'à 2000 lignes par feuille |
| Word (docx), PowerPoint (pptx), OpenDocument, RTF, HTML | texte ; les tableaux Word sont rendus ligne par ligne, avec les cellules séparées par « \| » |
| Fichiers texte et code (txt, md, json, xml, py et autres) | texte tel quel |
| Images (png, jpg, gif, webp) | transmises au modèle comme image (Anthropic, les modèles des fournisseurs compatibles OpenAI et Ollama avec prise en charge des images savent les voir) ; en plus, Mnemai reconnaît sur ton ordinateur le texte présent dans l'image, et n'importe quel modèle le reçoit |
| Autres formats | le modèle reçoit uniquement le nom du fichier |

Le texte intégral du document est conservé à côté de la conversation. Sauf au cran le plus précis du curseur "Plus précis ↔ Plus économe", le modèle reçoit le début du document et les passages qui répondent à la question en cours, et non le fichier entier. Au cran le plus précis, le texte est inséré en entier, dans la limite de 60 000 caractères. Avec un PDF, tu peux ainsi : le résumer, trouver une réponse dans le texte, extraire des coordonnées et des chiffres, comparer deux documents joints, analyser des tableaux.

Créer et modifier des fichiers, produire des PDF, Word et Excel, modifier des fichiers Word et Excel existants, fusionner, découper, faire pivoter et séparer des PDF, lire des fichiers à partir de leur chemin : ce sont des actions sur les fichiers (voir la section ci-dessous). Ce que Mnemai ne fait pas avec les fichiers : elle ne remplit pas les formulaires PDF, ne lance ni programmes ni scripts.

## Internet

Le bouton « Internet » sous le champ de saisie autorise la recherche, mais ne l'active pas pour chaque message. Mnemai ne cherche que lorsqu'il est impossible de répondre sans données externes récentes : prix, taux de change, actualités, dernières versions, horaires, « maintenant » et « aujourd'hui », ou lorsque tu demandes explicitement « trouve » ou « cherche ». Pour les questions sur Mnemai elle-même, sur toi, pour les connaissances générales (« qu'est-ce que … ») et pour les tâches portant sur un texte donné, elle ne va pas sur le web. Un lien dans un message est toujours lu, même si le bouton est désactivé. Les pages d'un lien et les abonnements VPN ne s'ouvrent que pour des adresses sur internet : cet ordinateur, le réseau domestique ou de bureau et les adresses de service de Mnemai sont bloqués.

La recherche est gratuite, sans clés : Bing et Yahoo via la bibliothèque ddgs, puis DuckDuckGo, Bing, Yandex et Wikipédia directement. Les résultats qui ne correspondent pas à la majorité des mots-clés de la question sont écartés. Les pages sont lues et nettoyées sur ton ordinateur, le modèle reçoit des extraits numérotés et s'y réfère par [1], [2], et les sources sont visibles sous la réponse. Si internet est désactivé alors que la question exige clairement des données récentes, Mnemai répond avec ce qu'elle sait et te propose d'activer la recherche.

## Plus précis ou plus économe

Paramètres → Moteur → Réglages avancés → "Plus précis ↔ Plus économe" : un seul curseur à cinq crans, placé par défaut au milieu. Plus précis : davantage de mémoire et de morceaux du document sont confrontés à la question, le modèle demande plus souvent des précisions, et la réponse coûte plus cher. Plus économe : moins de tout cela, et le modèle ne demande des précisions que lorsqu'il ne peut vraiment pas faire autrement.

| Cran | Mémoire dans la requête | Document confronté | Conversation | Demande des précisions |
|---|---|---|---|---|
| Le plus économe | 2 000 caractères | jusqu'à 3 500 | jusqu'à 8 000 | seulement quand il ne peut vraiment pas faire autrement |
| Plus économe | 3 000 | jusqu'à 5 000 | jusqu'à 11 000 | seulement quand il ne peut vraiment pas faire autrement |
| Équilibré (par défaut) | 4 200 | jusqu'à 7 000 | jusqu'à 14 000 | quand c'est nécessaire |
| Plus précis | 8 000 | jusqu'à 12 000 | jusqu'à 20 000 | plus souvent |
| Le plus précis | 16 000 | en entier | en entier | au moindre doute |

Sauf au cran le plus précis, la mémoire est transmise avec son début et les lignes qui se rapportent à la question. Les 6 derniers messages de la conversation sont envoyés en entier, les plus anciens sont raccourcis à 400 caractères. Les documents et les pages web sont transmis sous forme de morceaux pertinents. Sous la réponse, tu vois combien de tokens ont été économisés (estimation : environ 3,5 caractères par token). Mesure sur un contrat de 153 000 caractères : 29 643 tokens en entrée sans économie, contre 6 159 avec, et seule la variante avec économie a donné la bonne réponse.

## Questions à choix, seconde passe, citation

Quand le modèle a besoin d'une précision, il pose une seule question sous forme de carte : la question elle-même, en une ligne pourquoi il la pose, et 2 à 4 options en colonne, dans l'ordre, chacune avec une courte explication de ce qui se passera si tu la choisis. Tu choisis une option en cliquant dessus ou avec un chiffre du clavier ; en bas de la carte, tu peux aussi répondre avec tes propres mots. Après ta réponse, l'option choisie est cochée. L'engrenage sur la carte permet de régler : poser ou non les questions sous forme d'options, expliquer ou non les options, ne demander que lorsque c'est vraiment nécessaire. La « Seconde passe » (dans les paramètres) demande au modèle de vérifier son brouillon avec tes règles et ta mémoire avant que tu ne le voies. Tu peux citer un passage sélectionné de la réponse dans le message suivant. Le bouton « Utile » sous la réponse indique quelle forme de réponse te convient : le modèle prend les réponses marquées comme exemple de forme.

## Tâches récurrentes

À la deuxième tâche similaire (ou à chaque fois, ou jamais — c'est réglable dans les paramètres), Mnemai te propose d'enregistrer une recette, pour que tu n'aies pas à tout réexpliquer la prochaine fois et que tu ne dépenses pas de tokens en précisions. La recette — objectif, données d'entrée, étapes, format du résultat, vérifications et ce qu'il ne faut pas faire — est stockée dans 90 System/Recipes. La demande similaire suivante est exécutée automatiquement d'après cette recette, et sous la réponse tu vois « d'après la recette « … » ». Mnemai détermine la similarité sur ton ordinateur, en comparant les radicaux des mots.

## Aide pour les termes

Quand les « Infobulles » sont activées (dans le menu « + » sous le champ de saisie), le modèle ajoute à sa réponse un court glossaire : les termes peu clairs et tous les noms propres présents dans la réponse — personnes, entreprises, produits, services, communautés (par exemple Show HN), sauf toi et les personnes dont tu as parlé toi-même. Mnemai retire le glossaire du texte, souligne ces mots dans la réponse et affiche l'explication au survol.

## Consortium

« Débattre avec d'autres IA » sous chaque réponse : une fenêtre « Avec qui débattre ? » s'ouvre d'abord, avec tous les modèles connectés sauf l'auteur de la réponse. Les meilleurs sont cochés d'avance, jusqu'à trois adversaires, et le premier modèle coché rédige la conclusion. L'auteur de la réponse la défend, les adversaires cherchent où elle est fausse, incomplète, ou s'il existe une meilleure option, puis vient la conclusion : la réponse tient-elle ou non, et que faire. Si une seule IA est connectée, ses modèles débattent entre eux (par exemple Sonnet contre Opus). C'est un consortium ordinaire au format débat : tu peux le poursuivre, l'arrêter ou le terminer.

Le bouton « Consortium » sous le champ de saisie lance une discussion entre 2 et 4 IA (n'importe quels modèles connectés, y compris celui qui est intégré) sur 1 à 20 tours. Elles parlent chacune à leur tour, se voient entre elles et s'interpellent par leur nom ; la dernière fait la synthèse : sur quoi elles sont d'accord, sur quoi elles ne le sont pas, ce qu'elles conseillent. Au-dessus des messages se trouve une table ronde : qui parle, qui est le suivant, avec les boutons « Pause », « Reprendre », « Terminer », « Rediscuter ». « Arrêter » (le bouton d'envoi, pendant qu'une réponse est en cours) coupe immédiatement l'intervenant en cours : ce qu'il a dit reste, marqué « interrompu », et les autres attendent « Reprendre ». Tu peux modifier la composition et le nombre de tours en cours de route. Chaque participant reçoit toute la conversation : les 16 derniers messages en entier, les plus anciens sous forme abrégée, les documents joints par extraits pertinents selon la question, le texte des images, les images elles-mêmes et les PDF. Formats : conseil, débat, brainstorming, red team et « grillade » (l'idée, le CV ou le texte est démoli sans ménagement, et la conclusion commence par une note « N/10 »). Sous la conclusion, « Partager » crée une carte-image avec le résultat. Si tu écris pendant la discussion, l'intervenant en cours s'arrête et la conversation reprend à partir de ton message ; un intervenant qui n'a encore rien dit (service bloqué) est retiré immédiatement. Un participant dont la clé ne fonctionne pas ou qui n'a plus de crédit le signale une seule fois, puis ne participe plus à la discussion ; la conclusion est alors rédigée par un autre. Chaque participant reçoit la mémoire selon ses propres droits d'accès. Le consortium peut être branché sur une conversation déjà en cours.

La fenêtre du consortium est d'abord simple : qui convier au conseil (2 à 4 IA, le numéro sur la carte indique l'ordre de passage), le format de la discussion et une table vivante avec les participants choisis et leur ordre d'intervention. Le bouton « Réglages avancés » ouvre tout le reste : les tours, les rôles, qui fait la synthèse, la longueur des interventions, la vérification des faits et le plan des tours ; chaque section a son propre « ? » avec une explication. « Plus simple » ramène à la vue simple.

La vérification des faits (activée par défaut) : si un participant s'appuie sur un fait, un chiffre, une date ou des informations récentes, il cherche lui-même sur internet, jusqu'à deux requêtes par tour, et répond avec des liens [1], [2]. Les sources sont visibles sous son intervention. Pour les opinions et les conseils, il ne cherche pas. Un tour avec recherche est plus long : le modèle répond deux fois, avant et après la recherche. Tu peux la désactiver dans les réglages avancés : « Chercher sur internet ».

La roue dentée sur le bouton « Consortium » ouvre les mêmes réglages :

| Réglage | Options |
|---|---|
| Format | Conseil : sa propre réponse → vérification → amélioration → points litigieux → réponse commune. Débat : les participants prennent tour à tour le pour et le contre, positions → objections → verdict. Brainstorming : idées sans critique → développement des idées des autres → les trois meilleures (pourquoi, premier pas, risque). Red team : attaque de ton plan → comment combler les failles → liste des risques et que faire |
| Rôles | pour chaque participant : sans rôle, sceptique, praticien, financier, juriste, créatif, analyste, client |
| Synthèse par | le dernier dans l'ordre ou un participant choisi : au dernier tour, il parle en dernier |
| Interventions | court (jusqu'à 80 mots, synthèse 120), normal (150 et 180), développé (300 et 350) |

En bas de la fenêtre se trouve un schéma : la table avec les participants dans l'ordre d'intervention, le camp de chacun dans les débats, une coupe pour celui qui fait la synthèse, et le plan des tours pour le format choisi. Le format, la longueur et les rôles sont mémorisés pour le prochain conseil.

## Actions sur l'ordinateur

Le modèle dans le chat peut travailler avec des fichiers : lire un fichier (y compris PDF, Word, Excel, PowerPoint ; les scans et images sont reconnus sur l'ordinateur), parcourir un dossier, rechercher des fichiers par mots-clés, créer ou réécrire un fichier texte (.md, .txt, .csv, .json, .html), modifier une portion de fichier, créer un document PDF, Word ou Excel à partir d'un texte avec titres, listes et tableaux, enregistrer une ligne dans la mémoire. Fonctionne avec n'importe quel modèle, cloud ou local.

Documents prêts à l'emploi :

| Quoi | Comment |
|---|---|
| Word (.docx) | remplacement de texte avec conservation de la mise en forme : la phrase est trouvée même si elle contient un mot en gras ou est fragmentée en plusieurs morceaux dans le fichier ; le nouveau texte reçoit la mise en forme de l'emplacement où commençait l'ancienne phrase. En-têtes, pieds de page et notes de bas de page également |
| Excel (.xlsx, .xlsm) | valeurs et formules dans les cellules ("Feuil1!B3 = 1500", "C7 = =SUM(C1:C6)"), remplacement de texte dans les cellules ; les autres feuilles, formats et formules restent intacts. Mnemai ne modifie pas les classeurs contenant des graphiques, des images ou des tableaux croisés dynamiques — ils disparaîtraient lors de l'enregistrement |
| PDF | fusionner plusieurs fichiers, conserver les pages souhaitées dans l'ordre voulu (ainsi que couper, supprimer, réorganiser), faire pivoter les pages de 90, 180 ou 270 degrés, diviser en parties. Le fichier source n'est pas modifié, le nouveau fichier n'écrase pas l'existant |

### Commandes rapides, sans modèle

Les commandes sans ambiguïté s'exécutent immédiatement, sans appel à l'IA, de la même façon quel que soit le modèle : « ouvre le terminal/chrome/firefox/lien », « ouvre wikipedia avec le mot… », « ouvre sur youtube… », « ouvre google », « ouvre yandex », « ouvre habr », « ouvre le fichier… », « lis le fichier… », « qu'y a-t-il dans le dossier… » (y compris « qu'y a-t-il dans les téléchargements »), « trouve… dans les fichiers », « trouve… dans la mémoire », « affiche la mémoire », « exécute… » (ou `!commande`), « mémorise… », « crée le fichier… avec le texte :… », « fais un pdf/word/excel… à partir de :… », « quelle heure est-il », « combien de mémoire/cœurs/espace disque ». Les sites connus (Wikipédia, Google, Яндекс, YouTube, GitHub, Хабр, Stack Overflow, Кинопоиск) s'ouvrent directement avec une recherche sur la requête indiquée. Tout le reste et toute formulation ambiguë passent comme avant par le modèle sélectionné.

### Uniquement les outils Mnemai

Les modèles n'ont pas leurs propres outils : Claude Code, DeepSeek Harness et les modèles cloud ne lancent rien par eux-mêmes. Toute action — lecture et écriture de fichiers, documents, terminal, ouverture d'applications, mémoire — passe par la couche MCP de Mnemai (la même que celle visible par Claude Desktop, Claude Code et Cursor via MCP). Tous les modèles ont donc les mêmes droits, le même journal et les mêmes restrictions.

### Terminal et contrôle de l'ordinateur

Si l'accès à l'ordinateur est activé (par défaut — oui), le modèle peut exécuter une commande dans le terminal : consulter les processus, le matériel, le réseau et le disque, lancer un programme, installer un paquet, travailler avec git, lire ou modifier un fichier hors des dossiers mémoire — tout ce que sait faire le terminal. Une commande à la fois, avec un délai d'attente (120 secondes par défaut, 900 au maximum — pour les installations et scripts). Aucune fenêtre de terminal ne s'ouvre : la commande s'exécute dans le chat, sa sortie apparaît dans la réponse au fil de l'exécution, et le code de retour ainsi que la sortie complète restent dans la ligne d'action ; l'exécution est enregistrée dans le journal "Mémoire" → "Historique". Mnemai enchaîne plusieurs actions dans une même réponse, chacune affichée en une courte ligne dans le chat, et il est possible d'arrêter n'importe laquelle via un bouton. Ouvrir une application ou un lien se fait en une seule action `open_app name="chrome"` (ou `name="https://…"`) : Mnemai trouve elle-même l'application installée et signale si elle est absente. Le modèle est informé de cet accès et l'utilise lorsqu'une tâche ne peut pas être résolue par les fichiers. Les mots de passe, clés et jetons ne sont pas affichés dans la réponse ; les commandes destructives ne sont pas exécutées sans demande explicite. sudo est autorisé : Mnemai demandera le mot de passe administrateur directement dans le chat, une seule fois, et il ne figurera ni dans la conversation ni ne sera transmis au modèle.

Par défaut, Mnemai effectue l'action immédiatement. Si dans Paramètres → Application → "Actions sur l'ordinateur" tu actives "Demander une autorisation pour chaque action", une carte "Mnemai souhaite" apparaît sous la réponse — indiquant ce qu'elle veut faire et avec quel fichier ou quelle commande, avec les boutons "Oui", "Oui pour cette conversation" (les mêmes actions dans cette conversation ne seront plus demandées) et "Non". Après l'action, une ligne "Fichier créé…" reste dans la conversation avec un bouton "Afficher dans le dossier", et le modèle poursuit sa réponse. Rien n'est envoyé sur internet.

Périmètre autorisé : fichiers — le dossier mémoire et les dossiers de travail que tu as ajoutés dans Paramètres → Application → "Actions sur l'ordinateur" ; terminal — sur tout l'ordinateur. Au même endroit, les actions peuvent être désactivées entièrement, et le bouton "Terminal et contrôle de l'ordinateur" désactive uniquement les commandes. Le dossier système .mnema est verrouillé. Le modèle lit une note de la mémoire selon ses propres droits : les sujets masqués restent masqués. Un document n'écrase jamais un fichier existant — le nouveau reçoit le nom "rapport (2).pdf". Toute écriture peut être annulée : "Mémoire" → "Historique" — aussi bien dans la mémoire que dans les dossiers de travail. Le PDF est généré via le navigateur Edge, Chrome ou Chromium sans ouvrir sa fenêtre : Edge est présent sur tout Windows 10 et 11 ; sur macOS et Linux, l'un d'eux est nécessaire.

## Mot de passe administrateur

Si une commande ou une installation de paquet nécessite des droits d'administrateur, Mnemai demande le mot de passe directement dans le chat — via une carte affichant la commande et un champ masqué, une seule fois. Le mot de passe est vérifié par sudo lui-même ; il n'est transmis ni à la conversation, ni au journal, ni au modèle, et est mémorisé pour les commandes suivantes. Pour sudo et l'installation de paquets, aucune fenêtre de terminal ne s'ouvre : la commande s'exécute sans fenêtre, la progression et le résultat sont visibles dans le chat, et l'installation dispose par défaut de 300 secondes. Une fenêtre de terminal visible est réservée aux programmes interactifs qui ont besoin d'un écran. Sur Windows, sudo n'existe pas — la carte n'apparaît pas.

## Conversation sans apprentissage

Le bouton « Sans apprentissage » sous le champ de saisie : cette conversation n'apprend rien à la mémoire, dès le premier message. Le modèle continue de voir la mémoire, mais rien de nouveau n'est enregistré à partir de la conversation, et le marquage « Utile » n'y apprend rien non plus.

## Voix et réunions

Le micro sous le champ de saisie sert à dicter une commande ou à enregistrer une réunion. La commande est enregistrée depuis le micro, reconnue sur ton ordinateur et envoyée sous forme de message, puis l'audio est supprimé. L'enregistrement d'une réunion capture le micro et le son de l'ordinateur sur deux canaux distincts, ce qui permet de voir qui parle dans la transcription. Tu peux aussi simplement glisser un fichier audio ou vidéo dans le chat (y compris les .mov d'iPhone, .mp4, .avi, .3gp, .m4v). Si le modèle de reconnaissance n'est pas encore installé, tu dois le télécharger une seule fois (environ 0,5 Go, connexion internet requise) — Mnemai te le signalera. La reconnaissance repose sur faster-whisper, exécuté sur ton ordinateur (modèle small ou medium, s'il est téléchargé). Tu peux aussi passer par Whisper dans le cloud avec une clé OpenAI : cela coûte 0,006 $ la minute, soit environ 0,36 $ l'heure. Le mode « Laisser Mnemai décider » (par défaut) mesure la vitesse de ton ordinateur pendant la première minute et, s'il ne peut pas terminer dans la durée de la réunion ou en 10 minutes, te demande si tu veux passer par le cloud. L'audio et Расшифровка.md restent dans 80 Meetings ; la transcription et un court résumé arrivent dans le chat, et tes propres paroles alimentent l'apprentissage. Dans la fenêtre d'enregistrement de la réunion, en haut à droite, se trouve « Configurer », qui mène à « Paramètres » → « Enregistrements de réunions ». Le parcours de la réunion y est présenté en quatre étapes : « Enregistrement » (conserver ou non l'audio), « Transcription » (où et avec quelle précision), « Résumé » (quel modèle rédige le résumé), « Mémoire » (apprentissage à partir de tes paroles). Clique sur une étape : sa description et ses réglages s'affichent en dessous. En haut, des préréglages sont proposés : « Privé » (tout reste sur l'ordinateur, l'audio est supprimé), « Équilibré » (Mnemai décide), « Rapide » (Whisper dans le cloud). Tu peux aussi choisir le modèle de résumé directement dans la fenêtre d'enregistrement.

## Modèle intégré sur ton ordinateur

Mnemai intègre un serveur llama.cpp. Tu as le choix entre 13 modèles GGUF de Hugging Face, répartis en cinq groupes : légers (Gemma 3 1B, Qwen2.5 1.5B, Llama 3.2 3B), équilibrés (Gemma 3 4B — recommandé, Qwen3 4B, Phi-4 mini), performants (Qwen2.5 7B, Llama 3.1 8B, YandexGPT 5 Lite 8B), spécialisés (Qwen3 4B Thinking, Qwen2.5 Coder 7B), grands (Gemma 3 12B, Mistral Small 3.2 24B). Pour chacun, tu vois à quoi il sert, sa taille, la mémoire nécessaire et le temps de téléchargement avec ta connexion. Le téléchargement peut être mis en pause et repris. Les modèles sont stockés dans ~/.mnema/models. Le modèle fonctionne sans internet et gratuitement, mais il est moins puissant que les modèles cloud.

Tant qu'un modèle local est sélectionné, un thermomètre s'affiche dans l'en-tête du chat : charge du processeur, part utilisée par le modèle, mémoire et température, si le système la fournit (Windows — pas toujours, Linux — en général, macOS — non). Si le modèle fait chauffer l'ordinateur pendant une minute, Mnemai réduit elle-même sa priorité et te le signale. Les boutons « Réduire la charge » et « Arrêter le modèle » sont à ta disposition.

## Moteur : jetons et charge

Réglages → Moteur, trois modes :

| Mode | Plus précis ↔ Plus économe | Longueur de réponse | Cœurs | Contexte | Apprentissage |
|---|---|---|---|---|---|
| Éco | plus économe (3 000 caractères de mémoire) | jusqu'à 1 000 jetons | un quart | 4 096 | toutes les 2 heures |
| Équilibré (par défaut) | équilibré (4 200) | 3 000 | la moitié | 8 192 | toutes les 30 minutes |
| Maximum | précision maximale (16 000, sans réduction) | 8 000 | tous sauf un | 16 384 | toutes les 10 minutes |

Réglage avancé — une seule colonne : « Plus précis ↔ Plus économe », la réponse la plus longue, la limite mensuelle, les cœurs du processeur, la quantité qu'elle garde en tête. Dès que tu déplaces un curseur à la main, le mode passe sur « Personnalisé ». La limite mensuelle compte les jetons du cloud ; une fois qu'elle est atteinte, les requêtes vers le cloud s'arrêtent avec un message clair, tandis que le modèle local sur ton ordinateur continue de fonctionner. Il est impossible de limiter la longueur des réponses de Claude via l'abonnement.

Plus bas se trouve un bloc distinct « En arrière-plan » : « Ne pas déranger pendant le travail » baisse la priorité du modèle local sur ton ordinateur, « Apprentissage en arrière-plan » règle la fréquence à laquelle Mnemai vérifie les sources d'apprentissage.

## Qui parmi les IA voit quoi

Paramètres → Sécurité → "Qui parmi les IA voit quoi" — un tableau : les IA en colonnes, les parties de la mémoire en lignes, plus un bloc de sujets fermés (Argent, Santé, Personnel — ils sont retirés même des parties autorisées). Chaque clic est enregistré immédiatement, et l'interrupteur sous une colonne désactive entièrement cette IA. Par défaut, rien n'est masqué, et n'importe quelle IA peut déposer du nouveau contenu dans la boîte de réception :

| IA | Voit | Peut ajouter à |
|---|---|---|
| Modèle sur l'ordinateur (intégré, Ollama, Strata) | tout | boîte de réception |
| Claude, Claude Code | tout | boîte de réception, décisions, projets, fiches, personnes, règles |
| ChatGPT | profil, règles, projets, fiches, décisions | boîte de réception |
| OpenRouter, DeepSeek, YandexGPT | profil, règles, projets, fiches, décisions | boîte de réception |
| Gemini | profil, règles, fiches | boîte de réception |
| Cursor | règles, projets | boîte de réception |

Le modèle sur l'ordinateur voit tout, car rien ne quitte ton ordinateur. L'argent, la santé et le personnel sont visibles par défaut pour toutes les IA qui ont accès aux Fiches : pour cacher un sujet à l'une d'elles, clique sur "visible" dans sa colonne, et ça passera à "masqué".

Un tag masqué sur un titre (par exemple "## Argent #money") cache ce titre et tout ce qui se trouve en dessous. Un tag sur le titre principal "# Argent #money" ou dans les propriétés du fichier (tags) cache le fichier entier. Les tags en russe fonctionnent aussi — #деньги, #здоровье, #личное — quelle que soit la casse, ainsi que les propriétés telles qu'Obsidian les écrit (tags sous forme de liste). Un changement de statut dans une fiche masquée apparaît dans le fil d'événements avec le même tag, il est donc masqué lui aussi.

## Ce qui quitte ton ordinateur

Avant toute requête vers une IA cloud (chat, consortium, deuxième passe, titres des conversations, cerveau d'apprentissage, portrait) et avant toute requête vers les moteurs de recherche, les numéros de carte (avec vérification de Luhn), les mots de passe, les codes PIN et CVV, les clés API, les jetons et clés VPN, les numéros de téléphone, le passeport, le SNILS, l'INN et les numéros de compte sont remplacés par des marqueurs du type [ТЕЛЕФОН-1]. La réponse revient avec les vraies valeurs, directement sur ton ordinateur. Cette option s'active dans «Paramètres → Sécurité». Le cerveau d'apprentissage sur un cloud tiers reçoit la mémoire selon les mêmes règles que l'IA du chat : les sujets masqués ne lui sont pas transmis. Chaque requête vers l'extérieur correspond à une ligne dans le journal : quand, à qui, pourquoi (réponse dans le chat, apprentissage, portrait, titre de conversation, recherche sur Internet), combien de caractères, quelle part de la mémoire disponible est partie, ce qui est masqué (uniquement le nombre, jamais les valeurs). Une requête qui n'est pas partie (pas de programme, pas de clé, pas de connexion) n'est pas inscrite dans le journal. «Sorties de la semaine» dans la carte «Mémoire», en bas à gauche, affiche le rapport des 7 derniers jours.

## Chiffrement de la mémoire par mot de passe

Réglages → Sécurité → « Chiffrer la mémoire avec un mot de passe », sur Windows, macOS et Linux. La même option t'est proposée au premier lancement, à l'étape « Protéger la mémoire par un mot de passe ? » : par défaut, sans mot de passe ; tu peux saisir le tien ou cliquer sur « Générer un mot de passe fort ». Pour une mémoire chiffrée, la synchronisation avec Google Drive, Dropbox, un dossier à toi ou une station n'envoie que des fichiers chiffrés ; une copie protégée par un autre mot de passe est refusée et n'écrase pas la tienne. Mnemai chiffre elle-même les notes et les fichiers internes qui contiennent ce que tu as dit et fait : conversations, texte des pièces jointes, journal et ses instantanés pour la restauration, traces de l'apprentissage, rapport sur ce qui est sorti de l'appareil, portrait. Sans le mot de passe, impossible de les lire, même en copiant le dossier.

| | |
|---|---|
| Fonctionnement | une clé de mémoire aléatoire (AES-256-GCM) chiffre les fichiers, et le mot de passe chiffre cette clé via scrypt ; les deux se trouvent dans .mnema/crypto.json |
| Mot de passe | au moins 8 caractères, impossible à récupérer : si tu l'oublies, la mémoire est perdue. Tu peux le changer à tout moment, les fichiers ne sont pas réécrits pour autant |
| Se souvenir sur cet ordinateur | la clé est conservée dans le stockage sécurisé du système (Windows : DPAPI, macOS : Trousseau d'accès, Linux : gestionnaire de mots de passe s'il y en a un, sinon un fichier dans le dossier personnel, accessible uniquement par toi) : Mnemai s'ouvre sans rien demander. Si l'option est désactivée, le mot de passe est demandé à chaque lancement, et tant qu'il n'est pas saisi, Mnemai n'affiche rien et n'apprend rien |
| Ce qui n'est pas chiffré | les fichiers binaires (PDF, Word, images, enregistrements de réunions), car d'autres programmes les ouvrent ; les réglages nécessaires avant la saisie du mot de passe (langue, modèles, droits d'accès de l'IA) ; les dossiers des autres programmes (.obsidian et similaires) |
| Contrepartie | Obsidian et les autres éditeurs ne pourront pas ouvrir les notes chiffrées. Si un autre programme enregistre une note dans le dossier, Mnemai la chiffrera à la prochaine ouverture |
| Interruption en cours de route | les fichiers sont chiffrés un par un : chacun est écrit à côté, on vérifie qu'il se relit à l'identique, puis il remplace l'ancien. Si tu éteins l'ordinateur en plein milieu, une partie des fichiers restera en clair, mais tous restent lisibles ; à la prochaine ouverture, Mnemai chiffrera les fichiers restants |
| Claude Code, Cursor (MCP) | reçoivent la mémoire comme avant, si Mnemai est lancée ou si le mot de passe est mémorisé sur cet ordinateur |

« Retirer le chiffrement » (le même interrupteur, le mot de passe est requis) rétablit des fichiers ordinaires.

Sur Windows, il existe aussi le chiffrement du système (EFS) : il est transparent pour toi, pour Mnemai et pour les autres programmes, la clé est ton compte Windows, et il n'est pas disponible sous Windows Home.

## Historique et annulation

Chaque ajout à la mémoire est consigné dans un journal : qui l'a écrit, quoi et quand. Section « Mémoire » → « Historique » : n'importe quelle modification s'annule d'un seul clic. Si le fichier a été modifié depuis, l'annulation ne retire que les lignes de cet ajout et conserve les modifications plus récentes ; elle ne refuse de s'exécuter que si cette ligne elle-même a déjà été corrigée à la main. Avant la première modification d'un fichier dans la journée, Mnemai en place une copie dans 95 Saves, et les deux dernières sont conservées. Les ajouts issus du chat, de l'apprentissage et des autres IA sont traités un par un, donc des écritures simultanées ne s'écrasent pas entre elles. Si un fichier ouvert dans l'éditeur de Mnemai a changé pendant que tu le modifiais, Mnemai ne l'écrase pas et te demande de le rouvrir.

Si une règle est formulée avec d'autres mots (« Fais-moi des résumés de conversation courts » et « Rends les résumés courts »), Mnemai n'ajoute pas une seconde ligne : elle réécrit l'ancienne avec les nouveaux mots.

## Connexion d'autres IA

- Claude Code, Claude Desktop, Cursor : Paramètres → "IA et modèles" → "Mémoire dans d'autres IA" → "Connecter" sur la tuile. Connexion via MCP : memory_context, memory_search, memory_remember, memory_stale, memory_journal, memory_undo. Le contexte est divisé en parties de 9 000 caractères maximum. Cursor reçoit uniquement les règles et les projets et n'écrit rien. La tuile indique si la connexion est déjà établie.
- ChatGPT : via une clé OpenAI par la tuile OpenAI, ou via un abonnement ChatGPT par un Sign in with ChatGPT dédié ; les réponses nécessitent Codex CLI App Server installé. Gemini se connecte avec sa propre clé Google AI Studio. Il n'y a pas d'extension navigateur : tout ce que les IA ne savent pas faire elles-mêmes, Mnemai le fait sur ton ordinateur.
- Via MCP, chaque IA ne voit dans le journal que les entrées qu'elle est autorisée à lire, et n'annule que ses propres entrées. Après une mise à jour depuis la version portable, la connexion dans Claude et Cursor bascule automatiquement vers le nouveau programme.
- Modèles : Paramètres → "IA et modèles". En haut — "Répond actuellement" : la médaille du modèle par défaut et son sélecteur. En dessous — "Modèles" en deux sections : "Payants" (sous-section "Par abonnement" — Claude et ChatGPT par abonnement ; sous-section "Par clé API" — Claude · clé API, ChatGPT · clé API, DeepSeek, Gemini, OpenRouter, OpenCode Go, YandexGPT ; l'API est facturée séparément, OpenCode Go — par clé d'abonnement) et "Gratuits" (modèle intégré, Ollama et Strata, sur cet ordinateur). Le menu des modèles en haut à gauche et l'étape "Avec quelle IA parler ?" au premier lancement sont organisés de la même façon. Les tuiles sont des médailles égales aux couleurs du fournisseur : intégrée, Claude par abonnement, Claude · clé API (Anthropic), ChatGPT par abonnement (Sign in with ChatGPT officiel + Codex App Server), ChatGPT · clé API, OpenCode Go, Gemini, OpenRouter, Ollama. ChatGPT peut être connecté de deux façons : la clé API OpenAI est facturée séparément à l'usage, tandis que l'abonnement ChatGPT se connecte via la fenêtre officielle Sign in with ChatGPT et un consentement distinct à l'utilisation du quota du plan. Mnemai stocke ses propres tokens OAuth dans le trousseau système et ne lit pas la session Codex CLI ; la génération nécessite Codex App Server installé. L'abonnement Gemini Advanced ne donne pas de clé Google AI Studio : l'API est facturée séparément. Une tuile connectée est colorée, avec le statut "connecté" ; une tuile non connectée est grise. La tuile a un seul bouton : "Saisir la clé" → le champ de clé s'ouvre directement dans la tuile → "Enregistrer et rechercher des modèles" ou "Annuler" ; pour Ollama — l'adresse, pour le modèle intégré — "Choisir et télécharger". Claude par abonnement apparaît automatiquement si Claude Code est présent sur l'ordinateur : Mnemai le recherche non seulement dans les chemins de recherche de programmes, mais aussi aux emplacements d'installation des installeurs (officiel, npm, WinGet, Volta, bun, Homebrew), ainsi qu'à l'intérieur de l'application Claude Desktop. Si Claude Code est trouvé mais que la connexion au compte n'est pas effectuée, la tuile affiche un bouton "Se connecter" : la fenêtre Claude Code s'ouvre, on s'y connecte avec son abonnement, puis "Vérifier à nouveau". S'il n'est pas trouvé — "Comment installer". Chaque IA connectée dispose d'un bouton "Désactiver" : elle disparaît de toutes les listes de modèles (chat, consortium, "Avec et sans mémoire"), la clé et les paramètres sont conservés, "Activer" la remet en place. Si une IA est connectée mais ne répond pas en raison d'un problème de compte — quota ou abonnement Claude épuisé, solde insuffisant, session Claude Code expirée, clé refusée — la tuile affiche "ne fonctionne pas" et la raison, l'IA est retirée des listes, et c'est la suivante disponible qui répond. Le bouton "Vérifier à nouveau" envoie une petite requête réelle. Le menu des modèles en haut à gauche est organisé de la même façon pour toutes les IA : pour chaque IA connectée — les trois meilleurs modèles (les plus récents full-size, puis les légers mini et flash) et un lien "Tous les modèles" avec un compteur. Dans "Tous les modèles", les modèles actifs apparaissent en premier, puis sous la ligne de séparation "Anciens et utilitaires" : les générations précédentes (gpt-3.5, gpt-4, Claude 3), les copies datées, les modèles pour les images, la voix et la recherche. Le modèle sélectionné est visible dans le menu, même s'il ne fait pas partie des trois meilleurs. La clé et la vérification y sont réduites sous la liste. Lorsqu'un quota est épuisé, Mnemai réessaie automatiquement dans une demi-heure. La clé est vérifiée immédiatement à l'enregistrement : une clé incorrecte n'est pas considérée comme connectée. Dans "Mémoire dans d'autres IA", une tuile connectée affiche un point animé sur la ligne Mnemai → programme.
- Modèle intégré : Paramètres → "IA et modèles" → "Modèle local".

## Proxy et VPN

Tout ce qui sort vers Internet (modèles, recherche, téléchargement de modèles) passe par un seul proxy : celui défini dans Mnemai (au premier lancement, via le menu de la zone de notification « Proxy… », ou dans Paramètres → Application → « VPN et proxy »), sinon le proxy système (Windows ; macOS — Réglages Système → Réseau ; Linux — les variables https_proxy et le réglage de GNOME), sinon une connexion directe. HTTP et SOCKS5 avec identifiant et mot de passe, le mot de passe étant conservé dans le coffre sécurisé du système. VPN par clé : colle un lien vless://, vmess://, trojan://, ss:// ou un abonnement https://, et Mnemai lance Xray rien que pour elle (« Importer une clé » depuis le presse-papiers ou « Saisir la clé manuellement »). Tu peux aussi passer par un client VPN déjà lancé. « Tester » essaie de joindre Anthropic via le proxy et t'indique ce qui ne va pas. Le modèle intégré ne passe pas par le proxy.

## Fenêtre, barre d'état système, installation

Au premier lancement — une brève introduction : six cas d'usage avec une idée par écran (pas besoin de réexpliquer, une seule mémoire pour tous les IA, moins de tokens dans n'importe quel IA, réunion → tâches, se souvient des solutions et des délais, les secrets restent chez toi) et le choix de l'IA. Le cas sur les tokens montre la mesure de la section "Économie de tokens" : une question sur un contrat de 153 000 caractères, 29 643 tokens d'entrée pour tout le texte contre 6 159 avec Mnemai. "Passer" ferme l'introduction immédiatement.

Fermer la fenêtre la masque dans la barre d'état système, l'apprentissage continue ; la première fois Mnemai demande "masquer ou quitter" et mémorise la réponse. "Quitter" dans le menu de la barre d'état système arrête tout. Dans le menu de la barre d'état système : "Ouvrir Mnemai", "Apprendre maintenant", "Pause d'apprentissage", "Proxy…" et démarrage automatique ("Lancer avec Windows", sur macOS "Ouvrir à la connexion macOS", sur Linux "Lancer à la connexion"). Un nouveau lancement n'ouvre pas une deuxième copie, mais affiche la fenêtre de la première. Sur Windows, Mnemai supprime elle-même les icônes des processus terminés de la barre d'état système au démarrage. Si le bureau Linux n'affiche pas la barre d'état système, fermer la fenêtre quitte le programme.

Mnemai vérifie les mises à jour elle-même : en arrière-plan, toutes les six heures, sans fenêtres ni questions. Quand une nouvelle version sort, un bouton discret "Mettre à jour" avec le numéro de version apparaît à côté de l'engrenage. Il télécharge le fichier adapté au système et met à jour le programme : sur Windows l'installateur se lance à la fermeture, sur Linux le nouveau fichier remplace le programme et il redémarre, sur macOS l'image .dmg s'ouvre — il reste à glisser Mnemai dans "Applications". "Plus tard" reporte le rappel jusqu'à la prochaine version, et on peut vérifier manuellement dans l'engrenage avec le bouton "Vérifier". Les vérifications en arrière-plan se désactivent dans config.json : "auto_update": false, ou au lancement avec MNEMA_NO_UPDATE=1.

L'installateur installe Mnemai sans droits administrateur dans %LOCALAPPDATA%\Programs\Mnemai, trouve les anciennes versions et supprime uniquement leurs fichiers programme : tout le reste dans ce dossier (par exemple, la mémoire créée à côté du programme) reste. La désinstallation du programme ne supprime pas non plus la mémoire. Il existe aussi une version portable en archive. L'installateur est pour l'instant sans signature numérique : Windows affichera "Windows a protégé votre ordinateur" — clique sur "Informations complémentaires" → "Exécuter quand même". Sur Windows 10 propre, Mnemai installera elle-même le composant de fenêtre Microsoft WebView2 (Internet nécessaire une fois). macOS : image .dmg, glisse Mnemai dans "Applications". Le programme est sans signature Apple, donc la première fois ouvre-le avec clic droit → "Ouvrir" (ou Réglages Système → Confidentialité et sécurité → "Ouvrir quand même"). Linux : un fichier .AppImage (rends-le exécutable et lance-le) ou archive .tar.gz avec dossier. La fenêtre sur Linux utilise Qt ; si elle ne s'ouvre pas, les paquets libxcb-cursor0 et libfuse2 (pour AppImage) sont nécessaires.

Si au lancement le dossier de mémoire n'est pas à sa place (il a été déplacé, renommé ou le disque externe n'est pas connecté), Mnemai le dit et propose d'indiquer où il se trouve maintenant, de vérifier à nouveau ou de commencer une nouvelle mémoire. Les premiers écrans sont dans la langue du système. Mnemai explique les erreurs des services avec des mots : ce qui s'est passé et quoi faire ; l'erreur reste dans la conversation, la réponse interrompue est marquée, "Arrêter" libère la conversation immédiatement.

## Engrenage, thème, langue, succès

L'engrenage en haut à droite donne accès à : l'apprentissage (en haut, son état ; quand la mémoire est activée, on y trouve aussi l'interrupteur de pause de l'apprentissage, et quand elle est désactivée, seulement la mention « Mémoire désactivée » ; le mode, le fil), le thème, la langue, les succès (on peut les désactiver), « Comment fonctionne Mnemai » (la visite guidée), « Comment fonctionne la mémoire » (le guide) et le « Manuel Mnemai ». Les astuces désactivées reviennent ici aussi : « Tutoriel dans les nouvelles conversations » et « Conseil sur une conversation coûteuse ». La croix de n'importe quelle fenêtre est un cercle transparent avec une fine croix, de la taille du symbole « ? » ; Échap ferme aussi la fenêtre. Dans une conversation sans apprentissage, le point sur l'engrenage est orange ; en dehors, il reflète de nouveau l'état de l'apprentissage. Le point sur l'engrenage indique l'état : vert — Mnemai apprend, jaune — la mémoire est désactivée ou l'apprentissage est en pause, gris — elle n'apprend que ce qu'on lui dit explicitement, ou l'apprentissage est désactivé. L'état de l'apprentissage est visible dans la zone de saisie : « Mnemai apprend · mémoire mise à jour il y a N min ». S'il n'y a pas de modèle pour analyser la parole, on y lit « Mnemai retient uniquement ce qui est dit directement » : seuls les éléments explicites sont enregistrés (« souviens-toi de… », corrections, décisions).

Neuf langues d'interface : russe, anglais, chinois, espagnol, hindi, portugais, français, allemand, japonais. Le modèle répond dans la langue choisie. Les conversations et la mémoire ne sont pas traduites.

Succès : 99 récompenses réparties en cinq groupes (prise en main, croissance de la mémoire, économies et habitude, confidentialité, rares) ; la plupart des succès rares restent cachés jusqu'à leur obtention. L'expérience gagnée grâce aux récompenses (10, 25, 50, 100) fait monter de niveau, de « Débutant » à « Mémoire éternelle ».

Dans l'engrenage se trouve le « Manuel Mnemai » — c'est le manuel intégré au programme : les sections à gauche, la recherche en haut, les résultats sont surlignés. Les paramètres s'ouvrent toujours sur la première section, « IA et modèles ». Au lancement, Mnemai affiche pendant une seconde un écran de démarrage : le logo, le nom et la signature « Free Memory AI Interface ». L'engrenage de la zone de saisie est petit, en haut à droite à côté du « ? », et ouvre les réglages de la zone de saisie.

## Plusieurs mémoires

Dans les réglages, à gauche sous les rubriques, se trouve le bloc « Mémoire » : toutes les mémoires de cet ordinateur, la mémoire ouverte est cochée. Un clic sur une autre l'ouvre. « Nouvelle mémoire » mène au premier écran, et la mémoire actuelle reste dans la liste. Le menu ⋮ d'une mémoire propose « Renommer » — le nom change dans la liste (le dossier sur le disque garde le sien) — et « Supprimer ». La suppression demande confirmation à deux reprises : dans la seconde fenêtre, « Vraiment supprimer … ? », la liste de ce qui va disparaître s'affiche (portrait, faits, conversations, historique), et le bouton « Supprimer » ne s'active qu'au bout de 10 secondes — une barre rouge diminue en dessous et un compte à rebours défile. Le dossier part à la corbeille, tu peux l'y récupérer. Si la mémoire est ouverte, Mnemai la ferme d'abord et passe à la suivante dans la liste ; s'il n'y en a pas d'autre, elle revient au premier écran.

## Telegram

"Paramètres" → "Apprentissage" → "Telegram". Mnemai lit Telegram via son API, et uniquement en lecture : le client Telegram intégré à Mnemai sait seulement se connecter et lire, et toute autre commande (envoyer, supprimer, marquer comme lu, rejoindre, réagir) est rejetée par le programme lui-même avant d'être envoyée. La connexion fonctionne comme dans Telegram Desktop : api_id et api_hash depuis my.telegram.org (API development tools), numéro de téléphone, code reçu dans Telegram et mot de passe cloud, si tu en as un. Plus bas se trouve la section "Chats à lire" : "Ajouter des chats" ouvre la liste de tes conversations privées et de tes groupes, avec une recherche, et tu coches ceux qui t'intéressent. Tant qu'aucun chat n'est sélectionné, Mnemai ne lit rien. Les canaux et les bots ne peuvent pas être sélectionnés. Dans les chats choisis, la conversation est lue en entier : tes messages sont marqués "Moi", les autres portent le nom de l'interlocuteur, ce qui permet à Mnemai de te connaître, toi comme les personnes qui t'entourent. Les identifiants de connexion sont stockés chiffrés dans le coffre sécurisé du système, la liste des chats et ce que Mnemai a appris sont conservés dans le dossier de mémoire, et Mnemai n'a pas de serveurs à elle. "Déconnecter" efface la connexion ; côté Telegram, la session reste visible dans "Appareils" tant que tu ne l'y termines pas.

## Carte « Mémoire » en bas à gauche

Deux lignes, chacune ouvre une preuve : « Mémoire locale sur le PC » ouvre le dossier de la mémoire, « Paramètres d'accès » ouvre le tableau « Quelle IA voit quoi ». L'engrenage de la carte mène aux paramètres de protection, et le « ? » vert à côté ouvre le guide « Comment fonctionne la mémoire » en 12 chapitres : le sommaire à gauche, à droite une scène, l'explication, un exemple (ce que tu dis et ce qui se passe dans la mémoire) et le bouton « Essayer », qui t'emmène vers le vrai endroit du programme. Les chapitres : le dossier sur l'ordinateur, comment le dossier de mémoire est organisé, la date du fait — quand tu l'as dit, l'apprentissage à partir des conversations, enregistrer tout de suite ou demander (seuils de 60 % et 80 %), les corrections deviennent des règles, la sélection de l'essentiel avant la réponse, les droits de l'IA, les secrets, l'ancien redemandera, l'historique avec retour en arrière, le modèle sur l'ordinateur. À la fin — « Vérifie toi-même » : le dossier, qui voit quoi, ce qui est sorti vers l'extérieur.

Essayer (menu « + » sous le champ de saisie et page « Mémoire ») :
- « Premiers pas » — sept questions courtes : qui tu es, où tu habites, ce qui compte le plus en ce moment, tes projets, les personnes autour de toi, comment on doit te parler et ce que l'IA n'a pas le droit de faire. Les réponses sont enregistrées dans la mémoire comme des faits ordinaires et n'écrasent rien.
- « Mnemai te connaît-elle bien ? » — un quiz de dix faits de la mémoire : « Exact » (le statut reçoit la date du jour), « Plus vraiment » (tu écris ce qu'il en est maintenant, l'ancien part dans l'archive des faits), « Faux » (le fait part dans l'archive). À la fin, tu obtiens ton score.
- « Avec et sans mémoire » — une question posée aux IA connectées (jusqu'à trois) ; chacune répond deux fois : comme un chat ordinaire sans mémoire, puis via Mnemai. Les réponses s'affichent côte à côte.
- « Le grill » — un consortium au format « grill » (roast).

Tout résultat peut être transformé en carte-image (« Partager ») : la copier, l'enregistrer dans « Images/Mnemai » ou copier le texte de publication tout prêt avec le lien. Sur l'image, il n'y a que ce qui est visible dans la fenêtre avant l'envoi.

## Ce que Mnemai ne sait pas faire

- Elle ne lance ni programmes ni scripts. Elle ne travaille avec les fichiers que par des actions : dans le dossier de mémoire et dans les dossiers de travail, chacune est consignée dans le journal et peut être annulée.
- Le chiffrement par les outils du système (EFS) n'existe que sous Windows ; le chiffrement par mot de passe Mnemai fonctionne partout.
- Pour un long scan, seules les 40 premières pages sont reconnues.
- Sans internet, les modèles cloud et la recherche ne fonctionnent pas. Si la connexion tombe au milieu d'une conversation, c'est le modèle sur ton ordinateur qui répond (s'il est téléchargé), et elle l'indique dans une ligne au-dessus de la réponse.
- Elle ne lit ni les e-mails ni le calendrier tant que tu ne lui as pas donné l'adresse et le mot de passe, ou un lien.
