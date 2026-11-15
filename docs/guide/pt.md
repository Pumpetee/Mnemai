<div align="center">

<img src="../img/brand/logo.svg" width="72" alt="Mnemai">

# Guia do Mnemai

Como o Mnemai funciona, tela por tela e configuração por configuração. O Mnemai responde perguntas sobre si mesmo com este mesmo texto.

<sub><a href="en.md">English</a> · <a href="ru.md">Русский</a> · <a href="zh.md">中文</a> · <a href="es.md">Español</a> · <a href="hi.md">हिन्दी</a> · <b>Português</b> · <a href="fr.md">Français</a> · <a href="de.md">Deutsch</a> · <a href="ja.md">日本語</a></sub>

<sub><a href="../../README.pt.md">README</a></sub>

</div>

## Conteúdo

- [O que é a Mnemai](#o-que-é-a-mnemai)
- [Memória ligada ou desligada](#memória-ligada-ou-desligada)
- [Pasta de memória](#pasta-de-memória)
- [Pastas de memória adicionais](#pastas-de-memória-adicionais)
- [Como um fato é registrado](#como-um-fato-é-registrado)
- [Aba Memória](#aba-memória)
- [Retrato](#retrato)
- [Resumo do 10 Now e o índice](#resumo-do-10-now-e-o-índice)
- [Como a Mnemai aprende](#como-a-mnemai-aprende)
- [Fontes de aprendizado](#fontes-de-aprendizado)
- [Modos de aprendizado](#modos-de-aprendizado)
- [Como o Mnemai entende textos](#como-o-mnemai-entende-textos)
- [Como a Mnemai decide: gravar ou perguntar](#como-a-mnemai-decide-gravar-ou-perguntar)
- [Feed de aprendizado e pergunta na conversa](#feed-de-aprendizado-e-pergunta-na-conversa)
- [Chat e modelos](#chat-e-modelos)
- [Sessões](#sessões)
- [Como ela responde](#como-ela-responde)
- [O que o modelo sabe em cada mensagem](#o-que-o-modelo-sabe-em-cada-mensagem)
- [Arquivos e documentos, incluindo PDF](#arquivos-e-documentos-incluindo-pdf)
- [Internet](#internet)
- [Mais preciso ou mais econômico](#mais-preciso-ou-mais-econômico)
- [Perguntas em botões, segunda passada, citação](#perguntas-em-botões-segunda-passada-citação)
- [Tarefas recorrentes](#tarefas-recorrentes)
- [Dicas para termos](#dicas-para-termos)
- [Consórcio](#consórcio)
- [Ações no computador](#ações-no-computador)
- [Senha do administrador](#senha-do-administrador)
- [Conversa sem aprendizado](#conversa-sem-aprendizado)
- [Voz e reuniões](#voz-e-reuniões)
- [Modelo integrado no computador](#modelo-integrado-no-computador)
- [Mecanismo: tokens e carga](#mecanismo-tokens-e-carga)
- [Quem dos IAs vê o quê](#quem-dos-ias-vê-o-quê)
- [O que sai do computador](#o-que-sai-do-computador)
- [Criptografia da memória com senha](#criptografia-da-memória-com-senha)
- [Histórico e reversão](#histórico-e-reversão)
- [Conectar outras IAs](#conectar-outras-ias)
- [Proxy e VPN](#proxy-e-vpn)
- [Janela, bandeja do sistema e instalação](#janela-bandeja-do-sistema-e-instalação)
- [Engrenagem, tema, idioma, conquistas](#engrenagem-tema-idioma-conquistas)
- [Várias memórias](#várias-memórias)
- [Telegram](#telegram)
- [Cartão "Memória" no canto inferior esquerdo](#cartão-memória-no-canto-inferior-esquerdo)
- [O que o Mnemai não faz](#o-que-o-mnemai-não-faz)

## O que é a Mnemai

A Mnemai é um programa de memória para qualquer IA. Ela lembra quem você é, no que você está trabalhando, quais decisões você tomou e como conversar com você, e leva isso para a conversa com qualquer modelo: Claude, ChatGPT, Gemini, o modelo integrado no computador, Cursor e agentes. A memória é uma pasta de arquivos Markdown comuns no seu computador, que pode ser aberta em qualquer editor (inclusive o Obsidian) e até sem a Mnemai. A Mnemai não tem nuvem nem conta. O programa é uma única janela (chat, memória, configurações) e um ícone na bandeja do sistema (no macOS, na barra de menus). Funciona no Windows 10 e 11, no macOS 11 ou mais recente (Apple Silicon e Intel) e no Linux (64 bits, Ubuntu 22.04 ou mais recente e similares). A versão pessoal é gratuita e de código aberto (licença AGPL-3.0); a versão para empresas é vendida separadamente.

## Memória ligada ou desligada

A memória é o interruptor principal do Mnemai: fica no painel "Memória", no canto inferior esquerdo do chat (o mesmo que em Configurações → Aprendizado → "Memória"). Enquanto a memória estiver desligada, o ponto na engrenagem, no canto superior direito, fica amarelo. Uma memória nova, criada na primeira tela, começa desligada: no tutorial há a etapa "Ligar a memória?" (o padrão é "Sem memória"), e, se o tutorial não for exibido, a mesma pergunta aparece em uma janela separada. Uma memória que já existia antes do interruptor continua ligada.

Desligada, o Mnemai funciona como um chat comum com qualquer IA: o modelo não sabe nada sobre o dono da memória, o Mnemai não memoriza nada (o aprendizado não acontece, o "lembre-se" não grava, a ação "gravar na memória" é recusada), e o Claude Code, o Claude Desktop e o Cursor não recebem a memória e não conseguem gravar nela. Todo o resto continua funcionando: quaisquer modelos, consórcio, documentos e a economia de tokens com eles, internet, reuniões, modelos locais e ações com arquivos nas pastas de trabalho (a pasta da memória fica fechada para as ações). A aba "Memória" mostra a tela "Memória desligada" com os botões "Ligar memória" e "Ver o que foi gravado". As configurações de aprendizado e "Quem vê o quê entre as IAs" ficam esmaecidas, com o aviso "Memória desligada" e o botão "Ligar"; o botão "Sem aprendizado" no chat fica inativo, e a barra de status mostra "Memória desligada · chat comum, nada é memorizado".

## Pasta de memória

A memória fica na pasta que você escolheu na primeira execução. Dentro dela:

| Pasta ou arquivo | O que tem lá |
|---|---|
| 00 Inbox/Inbox.md | fatos ainda não organizados |
| 10 Now.md | resumo do dia: quem você é, projetos ativos, últimos eventos, fatos recentes dos últimos 14 dias, status com mais de 30 dias para revisar. É montado automaticamente, não edite à mão |
| 20 Projects/<nome>/_Project.md | hub do projeto: status (active, paused, closed), objetivo, data de início, palavras-chave, diário. Os documentos do projeto ficam ao lado |
| 30 People/<nome>.md | ficha da pessoa |
| 60 Events/AAAA-MM.md | decisões e mudanças de status por mês, as mais novas no topo |
| 70 Memory/Profile.md | quem você é |
| 70 Memory/Rules.md | como trabalhar com você, uma regra por linha com data |
| 70 Memory/Thoughts.md | seus pensamentos e ideias |
| 70 Memory/Cards/<tema>.md | ficha de um tema: um fato por linha, palavras-chave e tags ocultas no cabeçalho |
| 70 Memory/Fact archive/ | fatos substituídos por outros mais recentes. É o histórico, os modelos não o recebem |
| 70 Memory/Index.md | índice: projetos, fichas e pessoas com palavras-chave. É montado automaticamente |
| 80 Meetings/ | gravações de reuniões, transcrições e resumos |
| 90 System/Journal/<dia>.md | diário: o que foi registrado e por quem, em linguagem humana |
| 90 System/Recipes/ | receitas de tarefas recorrentes |
| 95 Saves/ | cópia do arquivo antes da primeira edição do dia; as duas mais recentes são mantidas |
| 99 Archive/ | projetos encerrados junto com os documentos |
| .mnema/ | arquivos de serviço: acessos das IAs, registro de edições, snapshots para reverter, tokens, configurações de aprendizado, conversas |

Você pode editar os arquivos de memória à mão. O Mnemai lê somente essa estrutura.

## Pastas de memória adicionais

Configurações → Programa → "Pastas de memória adicionais": outras pastas que as IAs enxergam junto com a memória principal. Qualquer uma serve: anotações, cofre do Obsidian, documentos, pasta compartilhada da equipe ou até outra memória do Mnemai. O botão "Conectar Obsidian" encontra sozinho os cofres do Obsidian no computador (a partir das configurações do próprio Obsidian) e mostra cada um com o número de notas: os marcados passam a ser memória adicional, e também dá para indicar a pasta manualmente. Qualquer outra pasta é adicionada pelo botão "Adicionar" (ou "Escolher…"), e para remover é só clicar em "Remover" ao lado. O cofre é lido por inteiro uma única vez em segundo plano e, depois disso, apenas as notas alteradas, então nem milhares de notas deixam as respostas mais lentas. Arquivos Markdown e de texto são lidos no computador, e só os trechos relevantes vão junto com a pergunta, dentro do mesmo limite de volume da memória (controle deslizante "Mais preciso ↔ Mais econômico"). Os temas ocultos para essa IA (#money, #health, #private e as formas em russo) também são removidos desses arquivos. O Mnemai não grava nada nessas pastas e não aprende com elas.

## Como um fato é registrado

Um fato é uma linha com data: "- 21.09.2026 · Decidimos iniciar o piloto em novembro". O status é escrito com a marca "(status DD.MM.AAAA)". Um novo status sobre o mesmo assunto substitui o antigo no mesmo lugar, o antigo vai para o arquivo de fatos, e a mudança aparece no feed de eventos. O que a própria Mnemai aprendeu é marcado com a palavra "aprendido", para que dê para ver o que veio do aprendizado.

A data de um fato aprendido é o dia em que você disse ou escreveu aquilo, e não o dia em que a Mnemai leu. Se hoje a Mnemai ler uma conversa de um mês atrás, o fato recebe a data dessa conversa, e a decisão vai para os eventos daquele mês. Assim, o que é antigo não passa por novidade.

A Mnemai não separa os status com mais de 30 dias em uma lista à parte. O modelo sabe a data de cada status: se a conversa tocar em um status com mais de um mês, ele diz de que data ele é e pergunta se ainda está valendo.

## Aba Memória

Memória → Perfil: no topo fica o perfil com os contadores de fatos; logo abaixo, o "Mapa da memória" — os temas em bolhas ao seu redor: o tamanho depende do número de fatos, o cadeado marca os temas que nem todas as IAs enxergam, e pulsa o que foi atualizado nos últimos três dias. O nome de uma bolha pequena aparece ao passar o mouse. Embaixo do mapa ficam os blocos de temas: "Regras para a IA", "Projetos", "Pessoas ao seu redor", as seções do perfil, os cartões de temas (os maiores primeiro) e "Eventos e decisões". Cada bloco mostra o número de fatos e duas linhas recentes (em projetos e pessoas, os primeiros nomes). Ao clicar em um bloco ou em uma bolha, o tema abre numa janela sobreposta: todos os fatos, uma linha por fato, os mais recentes no topo, data à direita, busca; clicar expande o fato por inteiro, e nos fatos aprendidos aparece ali mesmo o "De onde veio?"; o lápis abre o arquivo. Seções iguais do perfil (por exemplo, "Quem sou eu" aberto e oculto) são mostradas como um único tema.

## Retrato

O retrato são 2–3 frases no início de 70 Memory/Profile.md: quem você é, o que faz e o que é mais importante para você agora. Ele é o primeiro trecho que cada IA recebe. A Mnemai monta o retrato sozinha quando já há pelo menos três fatos sobre você: das seções abertas do perfil, dos projetos ativos e dos cartões sem tags ocultas (dinheiro, saúde e assuntos pessoais não entram no retrato). Quem escreve é o modelo escolhido para o aprendizado; sem modelo, ela usa os próprios fatos, em frases curtas. O retrato é remontado depois do aprendizado: imediatamente, se o perfil mudou, e no máximo uma vez a cada 6 horas, se só os cartões e os projetos mudaram. Se você reescrever o retrato por conta própria, a Mnemai não mexe mais nele. A montagem aparece no registro como "montou o retrato" e pode ser desfeita no histórico.

## Resumo do 10 Now e o índice

O Mnemai reconstrói sozinha o 10 Now.md e o 70 Memory/Index.md após cada registro. No 10 Now ficam quem você é, os projetos ativos, os últimos eventos, os fatos recentes dos últimos 14 dias (no máximo 12) e os status desatualizados. No índice ficam todos os projetos, fichas e pessoas, com as palavras pelas quais você pode encontrá-los. Editar esses arquivos à mão não adianta: na próxima reconstrução, a alteração será perdida.

## Como a Mnemai aprende

A Mnemai aprende sozinha, ao longo do seu dia a dia. Não precisa preencher questionários nem formulários. Ela percebe fatos nas fontes que você permitiu e decide se anota na hora ou se pergunta a você. O aprendizado acontece em segundo plano, por temporizador (a frequência depende do modo do mecanismo: de 10 minutos a 2 horas), e imediatamente a cada mensagem sua no chat da Mnemai. Na primeira execução, ela analisa o histórico dos últimos 90 dias.

Na primeira execução, a Mnemai pergunta: "A Mnemai pode olhar outros programas?". "Não, só a Mnemai" — ela aprende apenas com as conversas com ela e com as correções feitas nelas, e trabalha somente com a própria pasta de memória: não lê os chats do Claude Code, anotações, documentos, Telegram, navegador nem a extensão. "Sim, vou escolher o quê" — abre-se uma lista do que foi encontrado no computador (chats do Claude Code, pasta de anotações, Documentos, exportação do Telegram, histórico do navegador, extensão) com os caminhos; nenhum item vem marcado, e a Mnemai lê somente o que você marcar. E-mail e calendário ela nunca ativa por conta própria: para eles são necessários endereço e senha ou um link secreto.

Tudo isso pode ser alterado em Configurações → Aprendizado. Em "O que a Mnemai pode ver", o interruptor principal "Outros programas e navegador": quando está desativado, os blocos de fontes externas ficam bloqueados com um cadeado e não podem ser ativados. Logo abaixo, em "Onde aprender", cada fonte é ativada separadamente, e em algumas é possível indicar o caminho e as exceções.

A Mnemai nunca lê a própria pasta de memória nem as próprias chamadas de serviço ao modelo.

## Fontes de aprendizado

| Fonte | O que ela lê |
|---|---|
| Conversas no Mnemai | suas mensagens no chat do Mnemai, na hora, enquanto você escreve |
| Conversas no Claude Code | suas mensagens do histórico do Claude Code (pasta ~/.claude/projects), somente as linhas novas. Solicitações de serviço de scripts com um marcador do tipo "[SERVIÇO-NOME]" no início são ignoradas |
| Exportação do ChatGPT | o arquivo conversations.json da exportação de dados do ChatGPT |
| Suas correções | "não, não é assim", "eu já disse", "nunca…" em conversas com a IA viram regras para todas as IAs |
| Pasta de notas | novas linhas nas notas, por exemplo em um cofre do Obsidian. Pastas de sistema (.obsidian, .trash, .git) são excluídas |
| E-mail | seus e-mails enviados via IMAP, com as citações removidas |
| Telegram (conversas via API) | a conversa inteira — suas mensagens e as dos seus interlocutores — apenas nos chats que você escolheu. Somente leitura, mais detalhes na seção "Telegram" |
| Telegram (exportação) | suas próprias mensagens da exportação do Telegram Desktop |
| Calendário | arquivo .ics ou link secreto iCal |
| Documentos | documentos Word novos e alterados, textos e notas na pasta escolhida (.docx, .txt, .md) |
| Histórico do navegador | títulos das páginas lidas, por dia (Chrome, Edge, Yandex Browser). Por padrão, apenas observa |

## Modos de aprendizado

O modo é definido para cada fonte:

| Modo | O que acontece |
|---|---|
| Só observa | mostra o que aprenderia, sem gravar nada |
| Pergunta tudo | não grava nada por conta própria: em uma conversa no Mnemai, ela pergunta; em outros lugares, apenas mostra |
| Misto (padrão) | grava sozinha o que tem certeza. O que é pessoal ou contradiz a memória, vindo de uma conversa no Mnemai, ela confirma com uma pergunta na própria conversa; vindo de outros lugares, decide sozinha. Suposições fracas esperam se repetir |
| Tudo sozinha | grava tudo, com o histórico de alterações e a reversão como garantia |

Se um fato aparecer em várias fontes, vale o modo mais cauteloso entre elas.

## Como o Mnemai entende textos

O Mnemai pode interpretar a linguagem do dia a dia de várias maneiras ("Configurações → Aprendizado → "Como entender textos""):

| Opção | Como funciona |
|---|---|
| Automático (padrão) | o modelo com que você conversa por padrão — qualquer um conectado, na nuvem ou no computador; se não houver nenhum, apenas sinais explícitos |
| Sem modelo | só o que é explícito: "lembre …", correções, decisões ("decidi …"), datas de status |
| Claude por assinatura | pelo Claude Code instalado, sem ferramentas, hooks nem MCP, e a sessão não é salva |
| Chave própria | Anthropic ou compatível com OpenAI; a chave fica no armazenamento seguro do sistema (Windows — DPAPI, macOS — Keychain, Linux — armazenamento de senhas, se houver), não na pasta de memória |
| Modelo no computador | integrado ou Ollama, nada sai do seu computador |

Antes de enviar o texto a um modelo na nuvem, os segredos são substituídos por marcadores (veja "O que sai do computador").

## Como a Mnemai decide: gravar ou perguntar

- O limite de confiança padrão é 80%. Com confiança de 80% ou mais e um fato que não seja pessoal, ela grava por conta própria. Entre 60% e 80%, ela pergunta. Abaixo de 60%, ela espera até o fato aparecer de novo.
- A repetição aumenta a confiança: duas ocorrências de 60% resultam em 84%, e o fato é gravado.
- Dinheiro, saúde e assuntos pessoais vão para um cartão com a tag #money, #health ou #private: você pode ocultá-lo de qualquer IA na tabela "Quem vê o quê em cada IA". Se isso surgir numa conversa dentro da Mnemai, ela primeiro pergunta ali mesmo: "Isso é pessoal — quer que eu lembre?".
- Contradição na memória ("mora em Kazan" versus "é de Ecaterimburgo"): numa conversa dentro da Mnemai, a pergunta aparece ali mesmo ("Agora é assim", "Estava certo", "Os dois estão certos"); em outros lugares, o novo substitui o antigo, e, se a linha antiga dizia mais, a Mnemai a reescreve preservando o restante. O que valia antes vai para o arquivo de fatos.
- "Nunca aprender algo assim" adiciona uma frase de bloqueio. Desfazer um registro aprendido no histórico significa "não": isso não volta mais.
- Não existe uma fila de "esperando por você": a Mnemai não acumula perguntas. Fica no máximo uma pergunta sobre memória por vez abaixo da conversa, e a próxima aparece depois que você responder.

## Feed de aprendizado e pergunta na conversa

O feed "Aprendendo com você" (engrenagem → "Feed") mostra o que a Mnemai leu, o que entendeu e por que decidiu assim, por exemplo "confiança de 90% com limite de 80%, não é pessoal — registrei por conta própria" ou "isso envolve dinheiro — registrei na parte oculta". Se a memória precisar da sua palavra, aparece abaixo da conversa um cartão "Preciso confirmar para a memória" com botões; a resposta é registrada na hora. Cada linha aprendida tem o "de onde eu sei isso": a fonte, as suas palavras, quantas vezes apareceu e por que foi registrada.

## Chat e modelos

Mnemai é um chat com qualquer modelo; todos os modelos são iguais. A seleção de modelo fica no canto superior esquerdo do chat; o menu tem dois grupos:

- Na nuvem — funcionam pela internet: por chave (Anthropic, OpenAI, Gemini, OpenRouter, DeepSeek, YandexGPT; a lista de modelos Mnemai obtém do provedor, e para o YandexGPT — do catálogo Yandex Cloud AI Studio) ou por assinatura (Claude Code);
- No computador — gratuito, sem internet, nada sai para fora: modelo integrado (llama.cpp), Ollama e Strata.

Ao conectar e ao usar "Verificar", Mnemai consulta cada modelo da lista do ChatGPT, Gemini, DeepSeek e YandexGPT com uma requisição curta e mantém apenas os que respondem no chat: modelos descontinuados (como o4-mini, gpt-4, o1), modelos para áudio, imagens e voz, e modelos exclusivos para outra API no catálogo padrão OpenAI (pro, codex) não entram na lista. Se o provedor descontinuar um modelo depois, na primeira falha ele sai da lista e o chat informa para escolher outro. DeepSeek se conecta com chave de platform.deepseek.com. YandexGPT — com chave de API da conta de serviço Yandex Cloud AI Studio (função ai.languageModels.user) e o ID do catálogo onde ela foi criada: na janela de conexão há dois campos. Modelos YandexGPT: Alice AI LLM, YandexGPT Pro 5.1, YandexGPT Pro 5, Alice AI LLM Flash, além de DeepSeek V4.1 Flash e Qwen3.6 35B do mesmo catálogo. Strata é um programa gratuito separado para modelos grandes (Qwen, DeepSeek) na sua placa de vídeo (github.com/Niko1221/Strata): instale, inicie o modelo com o comando `strata launch` — Mnemai encontra automaticamente o Strata rodando em 127.0.0.1:8080 ao iniciar; outro endereço — na janela de conexão do Strata.

Os mesmos dois grupos em "Configurações" → "IA e modelos". O limite de tamanho da resposta ("Configurações" → "Motor") é único para todos os modelos, inclusive para o Claude por assinatura.

A memória e suas regras se aplicam a cada mensagem; cada modelo recebe apenas o que tem permissão de ver. Cada conversa tem um título de 1 a 3 palavras. Para alterá-lo, use o lápis ao lado do título, clique duplo no título ou o menu da conversa na lista (Enter — salvar, Escape — cancelar). Em uma nova conversa, o título pode ser definido antes da primeira mensagem e será salvo junto com ela. Títulos renomeados manualmente o Mnemai não altera mais; a lista também exibe a hora da última modificação e os tokens gastos. A lista pode ser ordenada por data ou por tokens; o filtro "IA" exibe conversas com um único modelo.

O botão "Deixar o Mnemai começar" em uma conversa vazia: o modelo cumprimenta e sugere por onde começar, com base na memória. Eventos são chamados de recentes apenas se a data os indica assim; decisões com mais de um mês são apresentadas com sugestão de revisão.

## Sessões

O botão "Nova sessão" fica no cabeçalho da lista, abaixo de "Nova conversa". Uma sessão reúne todas as conversas iniciadas depois do último clique: "Nova conversa" abre uma conversa na sessão atual, e "Nova sessão" começa um novo grupo. Na lista, as conversas de uma mesma sessão são unidas por uma linha à esquerda, e cada grupo tem um rótulo com o número de conversas à direita: o de cima é "Sessão atual", e os anteriores aparecem como "Sessão · 24 out" (o dia da última conversa). Clicar no rótulo recolhe o grupo, e o estado recolhido fica salvo. Logo depois de "Nova sessão" não aparece uma linha vazia: o grupo de cima continua sendo a "Sessão atual" até que surja a primeira conversa no novo grupo. Ao lado do rótulo há o menu ⋮: "Renomear" (para dar um nome próprio ao grupo) e "Excluir" (a sessão é removida junto com as conversas dela; as fixadas permanecem, e o que foi aprendido continua na memória). As conversas iniciadas antes de as sessões existirem formam uma sessão separada no fim da lista, e as fixadas ficam no topo, fora dos grupos. Na busca, na ordenação por tokens e no agrupamento por dias, a lista aparece no formato normal, sem sessões.

Ao lado dos botões fica o "?": uma animação mostra por que ficar muito tempo numa mesma conversa sai caro e qual é a diferença entre uma nova conversa e uma nova sessão.

Cada conversa envia ao modelo apenas o próprio histórico. Por isso, a conversa de uma nova sessão começa com o contexto limpo: o modelo recebe a memória e as regras, mas não as mensagens das conversas anteriores. Uma conversa longa envia cada vez mais histórico a cada resposta, então vale mais a pena começar um novo assunto numa nova conversa ou numa nova sessão — o que importava do passado o Mnemai já registrou na memória.

Quando uma resposta custa o triplo da primeira resposta do mesmo modelo naquela conversa (tokens de entrada, incluindo o cache, mais a resposta), aparece abaixo dela o cartão "A conversa ficou cara" (para um modelo gratuito rodando no computador, ele não aparece). O cartão mostra duas barras, a da primeira e a da última resposta, e quantas vezes a segunda é mais cara. O botão "Atualizar a memória e começar uma nova sessão" primeiro aprende a conversa inteira, de uma só vez, e depois começa uma nova sessão com o contexto limpo. Uma mensagem que já tinha sido aprendida antes não é considerada repetida. Numa conversa sem aprendizado, o botão simplesmente começa uma nova sessão. "Não mostrar mais" desativa a dica por completo; para reativá-la, vá na engrenagem ("Dica sobre conversa cara"). O "x" no cartão o oculta apenas naquela conversa.

## Como ela responde

Configurações → "Como responde": nome, tratamento (informal ou formal), tamanho da resposta (curta, direta, detalhada), gênero — para a concordância (pronto ou pronta), e personalidade. Todas as escolhas são cards, e à direita fica o "Exemplo de resposta": a mesma pergunta sobre o piloto, e a resposta muda na hora junto com as configurações, o nome inclusive, enquanto você digita. As personalidades — Gentil, Profissional, Rigoroso com verificações — são medalhas com uma escala de verificações de uma a três. Abaixo ficam os conjuntos e as regras detalhadas por grupo.

## O que o modelo sabe em cada mensagem

Antes de responder, o modelo recebe:
- como trabalhar com você — as regras da seção "Como responde" (personalidade, forma de tratamento, suas palavras);
- a memória que este modelo tem permissão para ver (o início da memória e as linhas relacionadas à pergunta);
- informações sobre como a Mnemai está configurada no momento: onde ela aprende, em qual modo, com o que entende os textos, quantas entradas há na memória;
- a data de hoje;
- para perguntas sobre a própria Mnemai, as seções necessárias desta base de conhecimento.

O modelo responde como a Mnemai e, sobre suas capacidades, diz apenas o que a Mnemai sabe fazer. As capacidades do motor em que ela roda (por exemplo, as ferramentas do Claude Code) não fazem parte da Mnemai.

## Arquivos e documentos, incluindo PDF

Anexe um arquivo com o clipe de papel abaixo do campo de texto ou arrastando-o para a janela. Cada arquivo pode ter até 25 MB. A Mnemai salva o arquivo junto da conversa e extrai o texto por conta própria, no seu computador e de graça.

| Formato | O que a Mnemai faz |
|---|---|
| PDF com camada de texto | extrai o texto página por página (com os números das páginas) |
| PDF escaneado sem texto | reconhece o texto no computador (RapidOCR), até 40 páginas, e entrega esse texto a qualquer modelo. O alfabeto depende do idioma da interface: cirílico (e inglês) para russo, latino com diacríticos para idiomas europeus, chinês e inglês para chinês e japonês. Se não conseguir reconhecer nada, o arquivo vai inteiro para o modelo: só a Anthropic, por chave de API, consegue ler um arquivo assim |
| PDF protegido por senha | a Mnemai avisa que o arquivo tem senha e sugere removê-la ("Imprimir → Salvar como PDF") |
| Excel (xlsx, xls), CSV, TSV | tabela por planilha, até 2000 linhas por planilha |
| Word (docx), PowerPoint (pptx), OpenDocument, RTF, HTML | texto; as tabelas do Word saem em linhas, com as células separadas por « \| » |
| Arquivos de texto e código (txt, md, json, xml, py e outros) | texto como está |
| Imagens (png, jpg, gif, webp) | entrega ao modelo como imagem (enxergam a Anthropic, os modelos de provedores compatíveis com a OpenAI e o Ollama com suporte a imagens) e, além disso, reconhece no computador o texto que estiver na imagem, e esse texto vai para qualquer modelo |
| Outros formatos | o modelo recebe só o nome do arquivo |

O texto completo do documento fica guardado junto da conversa. Exceto no passo mais preciso de "Mais preciso ↔ Mais econômico", o modelo recebe o início do documento e os trechos que respondem à pergunta atual, não o arquivo inteiro. No passo mais preciso, o texto é inserido por inteiro, mas com no máximo 60.000 caracteres. Assim, com um PDF você pode: fazer um resumo, encontrar uma resposta no texto, extrair dados cadastrais e números, comparar dois documentos anexados, analisar tabelas.

Criar e editar arquivos, gerar PDF, Word e Excel, editar Word e Excel já prontos, juntar, cortar, girar e dividir PDF, ler arquivos pelo caminho: tudo isso são ações com arquivos (veja a seção abaixo). O que a Mnemai não faz com arquivos: não preenche formulários em PDF e não executa programas nem scripts.

## Internet

O botão "Internet" abaixo do campo de entrada permite a busca, mas não a ativa a cada mensagem. A Mnemai só pesquisa quando não dá para responder com certeza sem dados externos atualizados: preços, cotações, notícias, versões mais recentes, horários, "agora" e "hoje", e também quando você pede diretamente "pesquise" ou "procure". Em perguntas sobre a própria Mnemai, sobre você, sobre conhecimentos gerais ("o que é …") e em tarefas com um texto já fornecido, ela não acessa a internet. Um link na mensagem é sempre lido, mesmo com o botão desativado. As páginas de links e as assinaturas de VPN só abrem por endereços da internet: este computador, a rede doméstica ou do escritório e os endereços internos da Mnemai ficam bloqueados.

A busca é gratuita e não precisa de chaves: Bing e Yahoo pela biblioteca ddgs, depois DuckDuckGo, Bing, Yandex e Wikipédia diretamente. Resultados que não correspondem à maioria das palavras-chave da pergunta são descartados. As páginas são lidas e limpas no computador, o modelo recebe trechos numerados e faz referência a eles como [1], [2], e as fontes ficam visíveis abaixo da resposta. Se a internet estiver desativada e a pergunta exigir claramente dados atualizados, a Mnemai responde com o que sabe e sugere ativar a busca.

## Mais preciso ou mais econômico

Configurações → Motor → Ajuste fino → "Mais preciso ↔ Mais econômico" — um único controle deslizante com cinco passos, por padrão no meio. Mais preciso: mais memória e mais trechos do documento são comparados com a pergunta, o modelo pede esclarecimentos com mais frequência e a resposta sai mais cara. Mais econômico: menos disso, e o modelo só pede esclarecimentos quando não tem como evitar.

| Passo | Memória na requisição | Documento comparado | Conversa | Pede esclarecimentos |
|---|---|---|---|---|
| Mais econômico possível | 2.000 caracteres | até 3.500 | até 8.000 | só quando não tem como evitar |
| Mais econômico | 3.000 | até 5.000 | até 11.000 | só quando não tem como evitar |
| Equilíbrio (padrão) | 4.200 | até 7.000 | até 14.000 | quando necessário |
| Mais preciso | 8.000 | até 12.000 | até 20.000 | com mais frequência |
| O mais preciso possível | 16.000 | completo | completa | diante de qualquer dúvida |

Exceto no passo mais preciso, a memória entra com o início e com as linhas relacionadas à pergunta. As últimas 6 mensagens da conversa entram completas, e as mais antigas são encurtadas para 400 caracteres. Documentos e páginas da web entram em trechos relevantes. Abaixo da resposta você vê quantos tokens foram economizados (estimativa: cerca de 3,5 caracteres por token). Medição em um contrato de 153.000 caracteres: 29.643 tokens de entrada sem economia contra 6.159 com ela, e só a variante com economia deu a resposta correta.

## Perguntas em botões, segunda passada, citação

Quando precisa de um esclarecimento, a IA faz uma pergunta em um cartão: a pergunta em si, em uma linha o motivo de estar perguntando, e de 2 a 4 opções em coluna, em ordem, cada uma com uma breve explicação do que acontece se for escolhida. Você escolhe a opção clicando ou pressionando o número no teclado, e na parte de baixo do cartão dá para responder com suas próprias palavras. Depois da resposta, a opção escolhida fica marcada com um check. A engrenagem no cartão controla: se as perguntas aparecem como opções, se as opções vêm com explicação e se ela só pergunta quando for realmente necessário. A "Segunda passada" (nas configurações) faz o modelo revisar o rascunho com base nas suas regras e na sua memória antes de você vê-lo. Um trecho selecionado da resposta pode ser citado na mensagem seguinte. O botão "Útil" abaixo da resposta é um sinal de qual formato de resposta funciona para você: o modelo usa as respostas marcadas como exemplo de formato.

## Tarefas recorrentes

Na segunda tarefa parecida (ou em todas, ou nunca — nas configurações), o Mnemai sugere salvar uma receita para que da próxima vez você não precise explicar tudo de novo nem gastar tokens com esclarecimentos. A receita — objetivo, dados de entrada, passos, formato do resultado, verificações e o que não fazer — fica em 90 System/Recipes. O próximo pedido parecido é executado por ela automaticamente, e abaixo da resposta aparece "por receita «…»". O Mnemai identifica a semelhança no seu computador, pela correspondência dos radicais das palavras.

## Dicas para termos

Com as "Dicas" ativadas (no menu "+" abaixo do campo de entrada), o modelo adiciona à resposta um pequeno glossário: termos pouco claros e todos os nomes que aparecem na resposta — pessoas, empresas, produtos, serviços, comunidades (por exemplo, Show HN), exceto você e as pessoas sobre as quais você mesmo contou. O Mnemai separa o glossário do restante, sublinha essas palavras na resposta e mostra a explicação ao passar o mouse.

## Consórcio

"Debater com outras IAs" aparece embaixo de qualquer resposta: primeiro abre a janela "Com quem debater?" — todos os modelos conectados, exceto o autor, com os melhores já marcados, até três oponentes, e o primeiro marcado fecha o debate com o resultado final. O autor da resposta a defende, os oponentes procuram onde ela está errada, incompleta ou onde existe uma opção melhor, e no final vem o veredito: se a resposta se sustenta ou não e o que fazer. Se só uma IA estiver conectada, os modelos dela debatem entre si (por exemplo, Sonnet com Opus). É um consórcio comum no formato de debate, e você pode continuar, parar ou encerrar.

O botão "Consórcio" abaixo do campo de entrada inicia uma discussão entre 2 e 4 IAs (quaisquer modelos conectados, inclusive o integrado) de 1 a 20 rodadas. Elas falam por turnos, veem umas às outras e se chamam pelo nome, e a última fecha com o resultado: no que concordam, no que discordam, o que recomendam. Acima das mensagens fica a mesa redonda: quem está falando, quem é o próximo, e os botões "Pausar", "Continuar", "Encerrar", "Discutir de novo". "Parar" (o botão de envio enquanto uma resposta está em andamento) interrompe o orador atual na hora: o que já foi dito permanece com a marca "interrompido", e os demais aguardam "Continuar". A composição e o número de rodadas podem ser alterados durante a discussão. Cada participante recebe a conversa inteira: as últimas 16 mensagens completas, as anteriores resumidas, os documentos anexados em trechos relevantes para a pergunta, o texto extraído das imagens, as próprias imagens e PDFs. Formatos: conselho, debate, brainstorming, red team e roast (criticam a ideia, o currículo ou o texto sem dó, e o resultado começa com a nota "N/10"). Abaixo do resultado há "Compartilhar": um cartão em imagem com o resultado. Se você escrever durante a discussão, o orador atual para e a conversa continua a partir da sua mensagem; o orador que ainda não disse nada (o serviço travou) é removido na hora. O participante cuja chave não funcionou ou ficou sem saldo avisa isso uma vez e não participa mais da discussão; nesse caso, outro fecha com o resultado. Cada participante recebe a memória de acordo com as próprias permissões de acesso. O consórcio pode ser conectado a uma conversa que já está em andamento.


A janela do consórcio começa simples: quem chamar para o conselho (2–4 IAs, o número no cartão indica a ordem), o formato da discussão e a mesa ao vivo com os participantes escolhidos e a ordem das falas. O botão "Configuração avançada" abre todo o resto — rodadas, papéis, quem fecha com o resultado, tamanho das respostas, verificação de fatos e plano das rodadas, e cada seção tem seu próprio "?" com uma explicação. "Simplificar" volta para a visualização simples.

Verificação de fatos (ativada por padrão): se um participante se apoia em um fato, número, data ou informação recente, ele mesmo pesquisa na internet — até duas consultas por turno — e responde com links [1], [2]. As fontes aparecem abaixo da resposta dele. Para opiniões e conselhos, ele não pesquisa. Um turno com pesquisa é mais longo: o modelo responde duas vezes, antes e depois da pesquisa. Dá para desativar na configuração avançada: "Pesquisar na internet".

A engrenagem no botão "Consórcio" abre as mesmas configurações:

| Configuração | Opções |
|---|---|
| Formato | Conselho: resposta própria → revisão → melhoria → pontos de divergência → resposta comum. Debate: os participantes se alternam a favor e contra, posições → objeções → veredito. Brainstorming: ideias sem críticas → desenvolvimento das ideias dos outros → as três melhores (por quê, primeiro passo, risco). Red team: ataque ao seu plano → como fechar as brechas → lista de riscos e o que fazer |
| Papéis | para cada participante: sem papel, cético, pragmático, financista, jurista, criativo, analista, cliente |
| Quem fecha o resultado | o último da fila ou um participante escolhido: na última rodada, ele fala por último |
| Respostas | curtas (até 80 palavras, resultado até 120), normais (150 e 180), detalhadas (300 e 350) |

Na parte de baixo da janela fica o esquema: a mesa com os participantes na ordem das falas, o lado de cada um no debate, a taça para quem fecha o resultado e o plano das rodadas do formato escolhido. O formato, o tamanho e os papéis ficam salvos para o próximo conselho.

## Ações no computador

O modelo no chat pode trabalhar com arquivos: ler um arquivo (incluindo PDF, Word, Excel, PowerPoint; digitalizações e imagens são reconhecidas no computador), ver uma pasta, encontrar arquivos por palavras, criar ou reescrever um arquivo de texto (.md, .txt, .csv, .json, .html), alterar um trecho do arquivo, criar um documento PDF, Word ou Excel a partir de texto com títulos, listas e tabelas, gravar uma linha na memória. Funciona com qualquer modelo, na nuvem ou no computador.

Documentos prontos:

| O que | Como |
|---|---|
| Word (.docx) | substituição de texto preservando a formatação: a frase é encontrada mesmo que tenha uma palavra em negrito ou esteja dividida em pedaços dentro do arquivo; o novo texto recebe a formatação do local onde a frase antiga começava. Cabeçalhos, rodapés e notas de rodapé também |
| Excel (.xlsx, .xlsm) | valores e fórmulas nas células ("Planilha1!B3 = 1500", "C7 = =SUM(C1:C6)"), substituição de texto nas células; as outras planilhas, formatos e fórmulas permanecem. Uma pasta de trabalho com gráficos, imagens ou tabelas dinâmicas o Mnemai não edita — ao salvar, eles seriam perdidos |
| PDF | juntar vários arquivos, manter as páginas necessárias na ordem desejada (também pode recortar, excluir, reorganizar), girar páginas em 90, 180 ou 270, dividir em partes. O arquivo original não é alterado, o novo não sobrescreve um existente |

### Comandos rápidos, sem modelo

Comandos inequívocos são executados imediatamente, sem chamar a IA, igualmente em qualquer modelo: "abra o terminal/chrome/firefox/link", "abra a wikipédia com a palavra …", "abra no youtube …", "abra o google", "abra o yandex", "abra o habr", "abra o arquivo …", "leia o arquivo …", "o que tem na pasta …" (incluindo "o que tem nos downloads"), "encontre … nos arquivos", "encontre … na memória", "mostre a memória", "execute …" (ou `!comando`), "lembre …", "crie o arquivo … com o texto: …", "faça pdf/word/excel … de: …", "que horas são", "quanta memória/núcleos/espaço em disco". Sites conhecidos (Wikipédia, Google, Yandex, YouTube, GitHub, Habr, Stack Overflow, Kinopoisk) são abertos imediatamente, com busca pela consulta mencionada. A instalação também é imediata: "instale aircrack" — sem janela, senha no chat. O resto — através do modelo selecionado.

### Apenas ferramentas do Mnemai

Os modelos não têm suas próprias ferramentas: Claude Code, DeepSeek Harness e modelos na nuvem não executam nada por conta própria. Qualquer ação — leitura e gravação de arquivos, documentos, terminal, abertura de programas, memória — passa pela camada MCP do Mnemai (a mesma que Claude Desktop, Claude Code e Cursor veem via MCP). Portanto, todos os modelos têm os mesmos direitos, o mesmo registro e as mesmas limitações.

### Terminal e controle do computador

Se o acesso ao computador estiver habilitado (por padrão — sim), o modelo pode executar um comando no terminal: ver processos, hardware, rede e disco, iniciar um programa, instalar um pacote, trabalhar com git, ler ou modificar um arquivo fora das pastas de memória — tudo o que o terminal consegue fazer. Um comando por vez, com timeout (por padrão 120 segundos, máximo 900 — para instalação e scripts). A janela do terminal não abre: o comando vai dentro do chat, sua saída aparece na resposta durante a execução, e o código de retorno e a saída completa permanecem na linha de ação; a execução é registrada no histórico "Memória" → "Histórico". Várias ações seguidas o Mnemai executa em uma resposta, cada uma em uma linha curta no chat, e qualquer uma pode ser interrompida com o botão. Abrir um programa ou link pode ser feito com uma ação `open_app name="chrome"` (ou `name="https://…"`): o Mnemai encontra o programa instalado e avisa se ele não estiver lá. O modelo sabe desse acesso e o utiliza quando a tarefa não pode ser resolvida com arquivos. Senhas, chaves e tokens não são exibidos na resposta; comandos destrutivos não são executados sem pedido direto. sudo é permitido: o Mnemai pedirá a senha de administrador diretamente no chat, uma vez, e ela não vai para a conversa nem para o modelo.

Por padrão, o Mnemai executa a ação imediatamente. Se em Configurações → Programa → "Ações no computador" ativar "Pedir permissão para cada ação", aparece um card "Mnemai quer" abaixo da resposta — o que exatamente e com qual arquivo ou comando, botões "Sim", "Sim para esta conversa" (as mesmas ações nesta conversa não serão mais perguntadas) e "Não". Após a ação, fica uma linha "Criou o arquivo …" na conversa com o botão "Mostrar na pasta", e o modelo continua a resposta. Nada vai para a internet.

Onde pode: arquivos — pasta de memória e pastas de trabalho que você adicionou em Configurações → Programa → "Ações no computador"; terminal — em todo o computador. No mesmo lugar as ações são desativadas completamente, e o botão "Terminal e controle do computador" desativa apenas comandos. A pasta de serviço .mnema está fechada. Uma nota da memória o modelo lê com seus próprios direitos: tópicos ocultos permanecem ocultos. O documento nunca sobrescreve um existente — o novo recebe o nome "relatório (2).pdf". Qualquer gravação pode ser revertida: "Memória" → "Histórico" — tanto na memória quanto nas pastas de trabalho. O PDF é montado através do navegador Edge, Chrome ou Chromium sem sua janela: Edge está em qualquer Windows 10 e 11, no macOS e Linux é necessário um deles.

## Senha do administrador

Quando um comando ou instalação de pacote exige privilégios de administrador, o Mnemai solicita a senha diretamente no chat — em um cartão com o comando e um campo mascarado, uma única vez. A senha é verificada pelo próprio sudo; ela não vai para a conversa, nem para o log, nem para o modelo, e fica salva para os próximos comandos. Para sudo e instalação de pacotes, nenhuma janela de terminal é aberta: o comando é executado sem janela, o andamento e o resultado aparecem no chat, e a instalação recebe por padrão 300 segundos. A janela de terminal visível fica reservada apenas para programas interativos que precisam de uma tela. No Windows não há sudo — o cartão não aparece.

## Conversa sem aprendizado

O interruptor "Sem aprendizado" fica embaixo do campo de entrada: essa conversa não ensina nada à memória, desde a primeira mensagem. O modelo continua enxergando a memória, mas nada de novo da conversa é gravado, e a marcação "Útil" nela também não ensina nada.

## Voz e reuniões

O microfone fica embaixo do campo de texto: use-o para dizer um comando ou gravar uma reunião. O comando é gravado pelo microfone, reconhecido no computador e enviado como mensagem, e o áudio é apagado. A gravação de reunião captura o microfone e o som do computador em dois canais, por isso a transcrição mostra quem está falando. Você também pode simplesmente arrastar um áudio ou vídeo para o chat (inclusive .mov do iPhone, .mp4, .avi, .3gp, .m4v). Se o modelo de reconhecimento ainda não estiver instalado, é preciso baixá-lo uma vez (cerca de 0,5 GB, com internet) — a Mnemai avisa quando for o caso. O reconhecimento usa o faster-whisper no computador (modelo small ou medium, se estiver baixado). Também dá para usar o Whisper na nuvem com a chave da OpenAI: custa US$ 0,006 por minuto, cerca de US$ 0,36 por hora. O modo "Decidir sozinho" (padrão) mede a velocidade do computador no primeiro minuto e, se não der tempo de terminar dentro da duração da reunião ou de 10 minutos, pergunta se você quer usar a nuvem. O áudio e o arquivo Расшифровка.md ficam em 80 Meetings; no chat chegam a transcrição e um resumo curto, e as suas falas entram no aprendizado. Na janela de gravação da reunião, no canto superior direito, há o botão "Configurar", que leva a Configurações → Gravações de reuniões. Lá o caminho da reunião aparece em quatro etapas: Gravação (guardar ou não o áudio), Transcrição (onde e com qual precisão), Resumo (qual modelo faz o resumo), Memória (aprende com as suas falas). Clique em uma etapa e embaixo aparecem a descrição e as configurações dela. Na parte de cima ficam as predefinições: "Privado" (tudo no computador, o áudio é apagado), "Equilibrado" (decide sozinha), "Rápido" (Whisper na nuvem). O modelo do resumo também pode ser escolhido na própria janela de gravação.

## Modelo integrado no computador

O Mnemai tem um servidor llama.cpp embutido. Você pode escolher entre 13 modelos GGUF do Hugging Face, divididos em cinco grupos: leves (Gemma 3 1B, Qwen2.5 1.5B, Llama 3.2 3B), equilibrados (Gemma 3 4B — recomendado, Qwen3 4B, Phi-4 mini), inteligentes (Qwen2.5 7B, Llama 3.1 8B, YandexGPT 5 Lite 8B), especiais (Qwen3 4B Thinking, Qwen2.5 Coder 7B) e grandes (Gemma 3 12B, Mistral Small 3.2 24B). Para cada um, o app mostra para que serve, o tamanho, a memória necessária e o tempo de download na sua conexão. O download pode ser pausado e retomado de onde parou. Os modelos ficam em ~/.mnema/models. Funciona sem internet e de graça, mas é mais fraco que os modelos na nuvem.

Enquanto um modelo local está selecionado, o cabeçalho do chat exibe um termômetro: carga do processador, parcela usada pelo modelo, memória e temperatura, se o sistema informar esse dado (no Windows nem sempre, no Linux geralmente, no macOS não). Se o modelo deixar o computador esquentando por um minuto, o Mnemai reduz a prioridade dele automaticamente e avisa você. Há os botões "Reduzir carga" e "Parar modelo".

## Mecanismo: tokens e carga

Configurações → Mecanismo, três modos:

| Modo | Mais preciso ↔ Mais econômico | Tamanho da resposta | Núcleos | Contexto | Aprendizado |
|---|---|---|---|---|---|
| Econômico | mais econômico (3.000 caracteres de memória) | até 1.000 tokens | um quarto | 4.096 | a cada 2 horas |
| Equilibrado (padrão) | equilibrado (4.200) | 3.000 | metade | 8.192 | a cada 30 minutos |
| Máximo | o mais preciso possível (16.000, sem cortes) | 8.000 | todos, menos um | 16.384 | a cada 10 minutos |

O ajuste fino é uma coluna só: "Mais preciso ↔ Mais econômico", a resposta mais longa, o limite mensal, os núcleos do processador, quanto ela mantém na cabeça. Qualquer controle deslizante movido manualmente muda o modo para "personalizado". O limite mensal conta os tokens da nuvem; quando ele acaba, as solicitações à nuvem são interrompidas com uma mensagem clara, e o modelo no computador continua funcionando. Não é possível limitar o tamanho da resposta do Claude pela assinatura.

Logo abaixo há um bloco separado, "Em segundo plano": "Não atrapalhar o trabalho" reduz a prioridade do modelo no computador, e "Aprendizado em segundo plano" define com que frequência o Mnemai verifica as fontes de aprendizado.

## Quem dos IAs vê o quê

Configurações → Segurança → "Quem dos IAs vê o quê" — uma tabela: IAs nas colunas, partes da memória nas linhas, bloco de tópicos privados (Dinheiro, Saúde, Pessoal — removidos até das partes permitidas). As alterações são salvas imediatamente; o botão abaixo da coluna desativa aquele IA completamente. Por padrão nada está oculto, e qualquer IA pode adicionar itens novos à caixa de entrada:

| IA | Vê | Pode adicionar |
|---|---|---|
| Modelo local (integrado, Ollama, Strata) | tudo | caixa de entrada |
| Claude, Claude Code | tudo | caixa de entrada, decisões, projetos, cartões, pessoas, regras |
| ChatGPT | perfil, regras, projetos, cartões, decisões | caixa de entrada |
| OpenRouter, DeepSeek, YandexGPT | perfil, regras, projetos, cartões, decisões | caixa de entrada |
| Gemini | perfil, regras, cartões | caixa de entrada |
| Cursor | regras, projetos | caixa de entrada |

O modelo local vê tudo porque nada sai do computador. Dinheiro, saúde e pessoal ficam visíveis por padrão para todos os IAs que têm acesso aos Cartões: para ocultar um tópico de algum deles, clique em "visível" na coluna correspondente — vai aparecer "oculto". Via MCP um comando demorado não bloqueia a resposta: o cliente recebe o progresso e pode cancelá-lo; sudo via MCP só é executado após digitar a senha no chat do Mnemai, e o MCP não abre janela de terminal.

Uma tag oculta no título (por exemplo, `## Dinheiro #money`) esconde esse título e tudo abaixo dele. Uma tag no nome `# Dinheiro #money` ou nas propriedades do arquivo (tags) esconde o arquivo inteiro. Tags em português também funcionam — #dinheiro, #saúde, #pessoal — em qualquer capitalização, assim como propriedades no formato que o Obsidian usa (tags em lista). Mudanças de status em um cartão oculto aparecem no feed de eventos com a mesma tag e, portanto, também ficam ocultas.

## O que sai do computador

Antes de qualquer requisição a uma IA na nuvem (chat, consórcio, segunda passada, títulos de conversas, cérebro de aprendizado, retrato) e antes de uma requisição a mecanismos de busca, números de cartão (com verificação de Luhn), senhas, PINs e CVV, chaves de API, tokens e chaves de VPN, telefones, passaporte, SNILS, INN e números de conta são substituídos por marcadores como [TELEFONE-1]. A resposta volta com os valores reais já no seu computador. Para ativar, vá em "Configurações" → "Segurança". O cérebro de aprendizado em uma nuvem de terceiros recebe a memória pelas mesmas regras que a IA do chat: temas ocultos não são enviados a ele. Cada requisição para fora vira uma linha no registro: quando, para quem, para quê (resposta no chat, aprendizado, retrato, título de conversa, busca na internet), quantos caracteres, quanto da memória disponível foi enviado e o que foi ocultado (apenas a quantidade, não os valores). Uma requisição que não saiu (sem programa, sem chave, sem conexão) não é gravada no registro. "Saiu na semana" no card "Memória", embaixo à esquerda, mostra o relatório dos últimos 7 dias.

## Criptografia da memória com senha

Configurações → Segurança → "Criptografar a memória com senha", no Windows, macOS e Linux. A mesma opção aparece na primeira vez que você abre o app, na etapa "Proteger a memória com senha?": por padrão fica sem senha, e você pode digitar a sua ou tocar em "Gerar uma senha forte". Na sincronização com Google Drive, Dropbox, uma pasta sua ou uma estação, a memória criptografada envia apenas arquivos criptografados; uma cópia com outra senha não é aceita e não sobrescreve a sua. A Mnemai criptografa por conta própria as notas e os arquivos de serviço com o que você disse e fez: conversas, texto dos anexos, o diário e seus snapshots para reverter, os rastros de aprendizado, o relatório do que saiu para fora, o retrato. Sem a senha, não dá para ler esses arquivos, nem copiando a pasta.

| | |
|---|---|
| Como funciona | uma chave aleatória da memória (AES-256-GCM) criptografa os arquivos, e a senha, via scrypt, criptografa essa chave; as duas ficam em .mnema/crypto.json |
| Senha | no mínimo 8 caracteres, e não dá para recuperá-la: se você esquecer, a memória não volta. Dá para trocar a qualquer momento, sem reescrever os arquivos |
| Lembrar neste computador | a chave fica guardada no armazenamento seguro do sistema (Windows — DPAPI, macOS — Chaveiro, Linux — gerenciador de senhas, se houver, senão um arquivo na pasta pessoal, acessível só para você): a Mnemai abre sem pedir a senha. Se estiver desativado, a senha é pedida a cada inicialização, e até lá a Mnemai não mostra nada e não aprende |
| O que não é criptografado | arquivos binários (PDF, Word, imagens, gravações de reuniões), porque outros programas os abrem; configurações necessárias antes da senha (idioma, modelos, permissões de acesso da IA); pastas de outros programas (.obsidian e similares) |
| Contrapartida | o Obsidian e outros editores não conseguem abrir as notas criptografadas. Uma nota gravada na pasta por outro programa será criptografada pela Mnemai na próxima vez que ela abrir |
| Falha no meio do processo | os arquivos são criptografados um a um: cada um é gravado ao lado, confere-se que ele é lido de volta igual, e só então substitui o antigo. Se o computador for desligado no meio, parte dos arquivos continuará aberta, mas todos continuam legíveis, e na próxima abertura a Mnemai criptografa o restante |
| Claude Code, Cursor (MCP) | recebem a memória como antes, se a Mnemai estiver aberta ou a senha estiver lembrada neste computador |

"Remover a criptografia" (o mesmo interruptor, exige a senha) devolve os arquivos ao formato normal.

No Windows também existe a criptografia do próprio sistema (EFS): ela é transparente para você, para a Mnemai e para outros programas, a chave é a sua conta do Windows, e não está disponível no Windows Home.

## Histórico e reversão

Toda gravação na memória vai para um registro: quem gravou, o quê e quando. Seção "Memória" → "Histórico": qualquer alteração pode ser revertida com um só botão. Se o arquivo foi alterado depois, a reversão remove apenas as linhas dessa gravação e mantém as edições mais recentes; ela só se recusa a agir se a própria linha já tiver sido editada à mão. Antes da primeira edição de um arquivo no dia, o Mnemai coloca uma cópia em 95 Saves, e as duas mais recentes são mantidas. As gravações do chat, do aprendizado e de outras IAs são feitas uma por vez, então gravações simultâneas não se perdem umas às outras. Se o arquivo no editor do Mnemai mudou enquanto você o editava, o Mnemai não vai sobrescrevê-lo e pedirá que você o abra novamente.

Se uma regra for dita com outras palavras ("Faz o resumo da conversa curto" e "Deixa os resumos curtos"), o Mnemai não adiciona uma segunda linha, mas reescreve a anterior com as novas palavras.

## Conectar outras IAs

- Claude Code, Claude Desktop, Cursor: Configurações → "IA e modelos" → "Memória em outras IAs" → "Conectar" no card. Conexão via MCP: memory_context, memory_search, memory_remember, memory_stale, memory_journal, memory_undo. O contexto é dividido em partes de até 9.000 caracteres. Cursor recebe apenas regras e projetos e não escreve nada. O card mostra se já está conectado.
- ChatGPT: por chave OpenAI através do card OpenAI ou por assinatura ChatGPT através de Sign in with ChatGPT separado; para respostas é necessário ter o Codex CLI App Server instalado. Gemini conecta com sua própria chave do Google AI Studio. Não há extensão de navegador: tudo que as próprias IAs não fazem, Mnemai faz no seu computador.
- Via MCP cada IA vê no diário apenas registros do que pode ler, e desfaz apenas seus próprios registros. Após atualizar de versão portátil, a conexão em Claude e Cursor migra automaticamente para o novo programa.
- Modelos: Configurações → "IA e modelos". No topo — "Respondendo agora": medalha do modelo padrão e sua seleção. Abaixo — "Modelos" em duas seções: "Pagos" (subseção "Por assinatura" — Claude e ChatGPT por assinatura; subseção "Por chave API" — Claude · chave API, ChatGPT · chave API, DeepSeek, Gemini, OpenRouter, OpenCode Go, YandexGPT; API paga separadamente, OpenCode Go — por chave de assinatura) e "Gratuitos" (modelo integrado, Ollama e Strata, neste computador). O menu de modelos no canto superior esquerdo e a etapa "Com qual IA conversar?" na primeira execução têm a mesma divisão. Cards — medalhas iguais nas cores do fornecedor: integrado, Claude por assinatura, Claude · chave API (Anthropic), ChatGPT por assinatura (Sign in with ChatGPT oficial + Codex App Server), ChatGPT · chave API, OpenCode Go, Gemini, OpenRouter, Ollama. ChatGPT pode ser conectado de duas formas: chave API OpenAI paga separadamente por uso, e assinatura ChatGPT conecta através da janela oficial Sign in with ChatGPT e consentimento separado para uso do limite do plano. Mnemai armazena seus próprios tokens OAuth no armazenamento do sistema e não lê o login do Codex CLI; para geração é necessário ter o Codex App Server instalado. Assinatura Gemini Advanced não fornece chave do Google AI Studio: API paga separadamente. Conectado — colorido, com status "conectado", desconectado — cinza. No card um botão: "Indicar chave" → campo de chave abre direto no card → "Salvar e encontrar modelos" ou "Cancelar", para Ollama — endereço, para integrado — "Selecionar e baixar". Claude por assinatura aparece sozinho se há Claude Code no computador: Mnemai busca não só nos caminhos de pesquisa de programas, mas também onde os instaladores o colocam (oficial, npm, WinGet, Volta, bun, Homebrew), e dentro do aplicativo Claude Desktop. Se Claude Code foi encontrado mas login na conta não foi feito, no card botão "Entrar": abrirá janela do Claude Code, lá login por assinatura, depois "Verificar novamente". Se não foi encontrado — "Como instalar". Cada IA conectada tem botão "Desligar": ela sai de todas as listas de modelos (chat, consórcio, "Com memória e sem"), chave e configurações permanecem, "Ligar" restaura. Se IA está conectada mas não responde por causa da conta — limite ou assinatura Claude acabou, sem dinheiro na conta, login no Claude Code expirou, chave não aceita — card indica "não funciona" e o motivo, e a própria IA sai das listas, e a próxima funcional responde. Botão "Verificar novamente" faz uma pequena solicitação real. Menu de modelos no canto superior esquerdo organizado igual para todas IAs: cada conectada tem três melhores modelos (mais novos tamanho completo, depois leves mini e flash) e link "Todos os modelos" com contador. Em "Todos os modelos" primeiro modelos funcionais, abaixo sob linha "Antigos e de serviço": gerações passadas (gpt-3.5, gpt-4, Claude 3), cópias datadas, modelos para imagens, voz e busca. Modelo selecionado visível no menu, mesmo que não esteja entre os três melhores. Chave e verificação recolhidas abaixo da lista. Limite esgotado Mnemai tenta novamente sozinha em meia hora. Chave verificada imediatamente ao salvar: chave incorreta não conta como conectada. Em "Memória em outras IAs" no card conectado pela linha Mnemai → programa corre um ponto.
- Modelo integrado: Configurações → "IA e modelos" → "Modelo local".

## Proxy e VPN

Tudo o que vai para a internet (modelos, busca, download de modelos) passa por um único proxy: o configurado no Mnemai (na primeira execução, no menu da bandeja "Proxy…", em Configurações → Programa → "VPN e proxy"); se não houver, o proxy do sistema (Windows; macOS — Ajustes do Sistema → Rede; Linux — as variáveis https_proxy e a configuração do GNOME); se também não houver, a conexão é direta. Há suporte a HTTP e SOCKS5 com login e senha, e a senha fica no armazenamento seguro do sistema. VPN por chave: cole um link vless://, vmess://, trojan://, ss:// ou uma assinatura https://, e o Mnemai sobe o Xray só para ela mesma ("Importar chave" da área de transferência ou "Inserir chave manualmente"). Também dá para usar um cliente de VPN que já esteja em execução. "Testar" chega até a Anthropic pelo proxy e diz o que está errado. O modelo integrado não usa o proxy.

## Janela, bandeja do sistema e instalação

Na primeira execução — uma apresentação rápida: seis casos com uma ideia por tela (não precisa explicar de novo, uma memória em todos os IAs, menos tokens em qualquer IA, reunião → tarefas, lembra decisões e prazos, seus segredos ficam com você) e a escolha do IA. O caso sobre tokens mostra uma medição da seção "Economia de tokens": uma pergunta sobre um contrato de 153.000 caracteres, 29.643 tokens de entrada com o texto completo contra 6.159 com o Mnemai. "Pular" fecha a apresentação imediatamente.

Fechar a janela a recolhe para a bandeja do sistema e o aprendizado continua; na primeira vez o Mnemai pergunta "recolher para a bandeja ou sair" e memoriza a resposta. "Sair" no menu da bandeja encerra tudo. No menu da bandeja: "Abrir o Mnemai", "Aprender agora", "Pausar aprendizado", "Proxy…" e inicialização automática ("Iniciar com o Windows", no macOS "Abrir ao iniciar sessão no macOS", no Linux "Iniciar ao entrar no sistema"). Abrir o programa novamente não abre uma segunda cópia, mas exibe a janela da primeira instância. No Windows, o próprio Mnemai remove os ícones de processos encerrados da bandeja ao iniciar. Se o ambiente de trabalho do Linux não exibir a bandeja, fechar a janela encerra o programa.

O Mnemai verifica atualizações automaticamente: em segundo plano, a cada seis horas, sem janelas nem perguntas. Quando uma nova versão é lançada, um botão discreto "Atualizar" com o número da versão aparece ao lado da engrenagem. Ele baixa o arquivo adequado para o sistema e atualiza o programa: no Windows o instalador é executado ao sair, no Linux o novo arquivo substitui o programa e ele é reiniciado, no macOS uma imagem .dmg é aberta — basta arrastar o Mnemai para "Aplicativos". "Mais tarde" adia o lembrete até a próxima versão, e é possível verificar manualmente na engrenagem com o botão "Verificar". As verificações em segundo plano podem ser desativadas no config.json: `"auto_update": false`, ou iniciando com `MNEMA_NO_UPDATE=1`.

O instalador instala o Mnemai sem privilégios de administrador em `%LOCALAPPDATA%\Programs\Mnemai`, encontra versões antigas e remove apenas os arquivos do programa: tudo mais nessa pasta (por exemplo, a memória criada junto com o programa) é mantido. Desinstalar o programa também não apaga a memória. Há também uma versão portátil em arquivo compactado. O instalador ainda não possui assinatura digital: o Windows exibirá "O Windows protegeu seu computador" — clique em "Mais informações" → "Executar assim mesmo". Em um Windows 10 limpo, o Mnemai instala automaticamente o componente Microsoft WebView2 (a internet é necessária apenas uma vez). macOS: imagem .dmg, arraste o Mnemai para "Aplicativos". O programa não possui assinatura Apple, portanto na primeira vez abra-o com o botão direito → "Abrir" (ou Preferências do Sistema → Privacidade e Segurança → "Abrir assim mesmo"). Linux: um único arquivo .AppImage (torne-o executável e execute-o) ou um arquivo .tar.gz com uma pasta. A janela no Linux é renderizada com Qt; se ela não abrir, os pacotes `libxcb-cursor0` e `libfuse2` (para AppImage) são necessários.

Se ao iniciar a pasta de memória não estiver no lugar esperado (foi movida, renomeada ou o disco externo não está conectado), o Mnemai informa isso e oferece a opção de indicar onde ela está agora, verificar novamente ou começar uma nova memória. As primeiras telas são exibidas no idioma do sistema. Erros de serviços o Mnemai explica em palavras: o que aconteceu e o que fazer; o erro permanece na conversa, a resposta interrompida é marcada e "Parar" libera a conversa imediatamente.

## Engrenagem, tema, idioma, conquistas

A engrenagem fica no canto superior direito: aprendizado (no topo — o estado; com a memória ativada, ali também fica o botão de pausar o aprendizado; com a memória desativada, só o aviso "Memória desativada"; modo, feed), tema, idioma, conquistas (dá para desativar), "Como a Mnemai funciona" (tour), "Como a memória funciona" (guia) e "Manual da Mnemai". As dicas desativadas voltam por aqui mesmo: "Tutorial em novas conversas" e "Aviso de conversa cara". O "x" de qualquer janela é um círculo transparente com uma cruz fina, do tamanho do símbolo "?"; a tecla Escape também fecha. Em uma conversa sem aprendizado, o ponto na engrenagem fica laranja; fora dela, volta a refletir o estado do aprendizado. O ponto na engrenagem mostra o estado: verde — aprendendo, amarelo — memória desativada ou aprendizado pausado, cinza — aprende só o que é dito explicitamente ou está desativado. O status do aprendizado aparece na barra de entrada: "A Mnemai está aprendendo · memória atualizada há N min". Se não há um modelo para analisar a fala, ali aparece "A Mnemai só memoriza o que você diz diretamente": só é registrado o que é explícito ("lembre que …", correções, decisões).

São nove idiomas de interface: russo, inglês, chinês, espanhol, hindi, português, francês, alemão, japonês. O modelo responde no idioma escolhido. As conversas e a memória não são traduzidas.

Conquistas: 99 prêmios em cinco grupos (domínio, crescimento da memória, economia e hábito, privacidade, raras); a maioria das raras fica oculta até ser conquistada. A experiência ganha com os prêmios (10, 25, 50, 100) dá níveis, de "Novato" a "Memória Eterna".

Na engrenagem há o "Manual da Mnemai" — o manual dentro do programa: seções à esquerda, busca no topo, e o que for encontrado fica destacado. As configurações sempre abrem na primeira seção, "IA e modelos". Ao iniciar, a Mnemai mostra por um segundo uma tela de abertura: logotipo, nome e a legenda "Free Memory AI Interface". A engrenagem da barra de entrada é pequena, fica no canto superior direito, ao lado do "?", e abre as configurações da barra de entrada.

## Várias memórias

Em "Configurações", à esquerda, abaixo das seções, fica o bloco "Memória": todas as memórias deste computador, com a que está aberta marcada com um ✓. Clique em outra para abri-la. "Nova memória" leva à primeira tela, e a atual continua na lista. No menu ⋮ de cada memória há "Renomear" — muda o nome na lista (a pasta no disco mantém o dela) — e "Excluir". A exclusão pede confirmação duas vezes: na segunda janela, "Excluir mesmo …?", aparece o que será apagado (perfil, fatos, conversas, histórico), e o botão "Excluir" só é liberado após 10 segundos — embaixo dele, uma barra vermelha diminui e a contagem regressiva corre. A pasta vai para a lixeira, e você pode restaurá-la de lá. Se a memória estiver aberta, o Mnemai primeiro a fecha e passa para a próxima da lista; se não houver outras, volta para a primeira tela.

## Telegram

"Configurações" → "Aprendizado" → "Telegram". O Mnemai lê o Telegram pela API dele e só lê: o cliente do Telegram dentro do Mnemai faz apenas login e leitura, e qualquer outro comando (enviar, apagar, marcar como lido, entrar, reagir) é recusado pelo próprio programa antes de ser enviado. O login funciona como no Telegram Desktop: api_id e api_hash de my.telegram.org (API development tools), número de telefone, código do Telegram e senha na nuvem, se você tiver uma. Logo abaixo fica "Chats para ler": "Adicionar chats" abre a lista dos seus chats pessoais e grupos, com busca, e você marca os que quiser. Enquanto nenhum chat estiver selecionado, o Mnemai não lê nada. Canais e bots não podem ser selecionados. Nos chats selecionados, a conversa é lida por inteiro: as suas mensagens ficam marcadas como "Eu", e as das outras pessoas com o nome de quem escreveu, e assim o Mnemai conhece você e as pessoas ao seu redor. O login fica guardado criptografado no armazenamento seguro do sistema, e a lista de chats e o que foi aprendido ficam na pasta da memória; o Mnemai não tem servidores próprios. "Desconectar" apaga o login; no Telegram, a sessão continua em "Dispositivos" até você encerrá-la lá.

## Cartão "Memória" no canto inferior esquerdo

São duas linhas, e cada uma abre uma prova: "Memória local no PC" abre a pasta da memória, e "Configurações de acesso" abre a tabela "Quem vê o quê entre as IAs". A engrenagem do cartão leva às configurações de proteção, e o "?" verde ao lado abre o guia "Como a memória funciona", com 12 capítulos: o sumário fica à esquerda, e à direita ficam a cena, a explicação, um exemplo (o que você diz e o que acontece na memória) e o botão "Experimentar", que leva a um lugar real do programa. Os capítulos são: a pasta no computador, como a pasta da memória é organizada, a data do fato (quando você disse aquilo), aprendizado a partir das conversas, salvar na hora ou perguntar (limites de 60% e 80%), correções viram regras, seleção do que importa antes de responder, permissões das IAs, segredos, o que está desatualizado é perguntado de novo, histórico com reversão e o modelo no computador. No final vem o "Confira você mesmo": a pasta, quem vê o quê e o que saiu para fora.

Experimentar (menu "+" abaixo do campo de entrada e página "Memória"):
- "Primeiros passos" — sete perguntas curtas: quem você é, onde mora, o que é mais importante agora, projetos, pessoas ao seu redor, como falar com você e o que a IA não deve fazer. As respostas entram na memória como fatos comuns e não apagam nada.
- "O quanto a Mnemai conhece você" — um quiz com dez fatos da memória: "Correto" (o status recebe a data de hoje), "Mudou" (você escreve como é agora, e o antigo vai para o arquivo de fatos), "Falso" (o fato vai para o arquivo). No final, você vê a pontuação.
- "Com memória e sem" — uma pergunta para as IAs conectadas (até três); cada uma responde duas vezes: como um chat comum sem memória e pela Mnemai. As respostas aparecem lado a lado.
- "Roast" — o consórcio no formato de roast.

Qualquer resultado pode virar um cartão de imagem ("Compartilhar"): você pode copiar, salvar em "Imagens/Mnemai" ou copiar o texto pronto de um post com o link. A imagem mostra apenas o que está visível na janela antes do envio.

## O que o Mnemai não faz

- Não executa programas nem scripts. Ela trabalha com arquivos apenas por meio de ações: na pasta da memória e nas pastas de trabalho, e cada ação fica registrada no histórico, com possibilidade de desfazer.
- A criptografia pelos recursos do sistema (EFS) existe só no Windows; a criptografia com senha do Mnemai funciona em qualquer sistema.
- Em um scan longo, só reconhece as 40 primeiras páginas.
- Sem internet, os modelos na nuvem e a busca não funcionam. Se a rede cair no meio da conversa, quem responde é o modelo no computador (se ele estiver baixado), e isso é avisado em uma linha acima da resposta.
- Não lê e-mail nem agenda até você informar o endereço e a senha ou um link.
