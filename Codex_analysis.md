## Esito sintetico

Il progetto è piccolo, leggibile e con una responsabilità ben definita: tradurre eventi e comandi tra Mopidy e MQTT. L’architettura di base è sensata, ma la classificazione “Production/Stable” appare ottimistica rispetto alla robustezza attuale.

I rischi principali sono:

1. payload MQTT non validati che possono generare eccezioni nel thread MQTT;
2. caricamento playlist distruttivo in caso di errore;
3. chiamate al frontend Pykka da un thread esterno all’actor;
4. assenza di TLS e affidabilità MQTT configurabile;
5. test quasi esclusivamente “smoke”;
6. packaging che dichiara erroneamente compatibilità Python 2.

Non ho modificato alcun file. Il working tree finale è ancora pulito e `main` risulta allineato a `origin/main`.

## Stato del progetto

- Versione: `1.2.1`
- Linguaggio: Python
- Integrazioni principali: Mopidy, Pykka, Paho MQTT
- Codice Python: circa 610 righe, di cui solo 43 nei test
- Test presenti: 2
- Branch: `main`
- Ultima attività rilevata: giugno 2026
- Licenza: Apache 2.0
- Artefatti locali già presenti: wheel e source distribution `1.2.1`

La separazione dei moduli è appropriata:

- [mopiqtt/__init__.py](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/__init__.py>): registrazione estensione e configurazione;
- [mqtt.py](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/mqtt.py>): trasporto MQTT;
- [frontend.py](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/frontend.py>): adattamento Mopidy/MQTT;
- [utils.py](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/utils.py>): formattazione metadati e artwork.

## Criticità ad alta priorità

### 1. Payload MQTT non protetti da una barriera di validazione

Il callback MQTT decodifica il payload e invoca direttamente il relativo handler:

[mqtt.py:81](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/mqtt.py:81>)

Non vengono gestiti:

- payload non UTF-8;
- eccezioni sollevate dall’handler;
- JSON malformato;
- campi JSON mancanti;
- tipi diversi da quelli attesi;
- risposte Mopidy vuote o parziali.

Il caso più evidente è la ricerca:

[frontend.py:303](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/frontend.py:303>)

`json.loads()`, gli accessi `value["search"]`, `value["uri_schemes"]`, `ret[0]` e `ret[0].tracks` assumono tutti input e risposta perfetti. Un singolo messaggio errato può far propagare un’eccezione nel callback MQTT, compromettendo la successiva elaborazione dei messaggi.

Raccomandazione: validare ogni comando, intercettare le eccezioni al confine del callback e pubblicare eventualmente un topic di errore o almeno un log strutturato.

### 2. Caricamento playlist distruttivo prima della validazione

Sia `pload` sia `ploadshfl` cancellano la coda prima di verificare che la playlist sia valida e leggibile:

[frontend.py:223](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/frontend.py:223>)  
[frontend.py:241](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/frontend.py:241>)

Se `get_items()` fallisce o restituisce dati inutilizzabili, la coda precedente è già stata persa.

Lo stesso rischio, in forma simile, esiste per `pstream`: la coda viene cancellata prima di sapere se l’URI può essere aggiunto.

Raccomandazione: risolvere e validare prima tutti gli URI; modificare la tracklist solo dopo aver ottenuto un risultato valido.

### 3. Violazione potenziale del modello actor

`MopiqttFrontend` è un `pykka.ThreadingActor`, ma Paho usa un proprio thread di rete. Il callback Paho chiama direttamente i metodi `on_action_*` dell’istanza frontend, senza passare dalla mailbox Pykka.

Questo crea due contesti concorrenti:

- thread dell’actor Mopidy/Pykka;
- thread di rete Paho MQTT.

Al momento lo stato locale è limitato, quindi il problema può non manifestarsi frequentemente, ma l’isolamento garantito dall’actor viene aggirato. Future modifiche potrebbero introdurre race condition difficili da riprodurre.

Raccomandazione: inoltrare i comandi MQTT alla mailbox dell’actor e processarli nel suo thread.

### 4. Sicurezza MQTT limitata

La configurazione supporta host, porta, topic, username e password, ma non:

- TLS;
- certificati CA/client;
- verifica hostname;
- QoS;
- ACL o separazione per istanza;
- Last Will;
- configurazione della riconnessione.

Il canale comandi permette di controllare riproduzione, volume e coda. Su una rete non completamente fidata, MQTT in chiaro sulla porta 1883 espone credenziali e comandi.

Inoltre, l’autenticazione viene impostata solo quando sono presenti sia username sia password:

[mqtt.py:42](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/mqtt.py:42>)

Un broker che accetta username senza password non è gestito.

## Affidabilità MQTT

### Stato non retained e QoS predefinito

Tutte le pubblicazioni usano implicitamente QoS 0 e `retain=False`:

[mqtt.py:94](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/mqtt.py:94>)

Conseguenze:

- un subscriber che si collega dopo un evento non conosce volume, stato o traccia corrente;
- un messaggio può essere perso durante una disconnessione;
- una dashboard Node-RED riavviata rimane incompleta fino al prossimo cambiamento.

Per un’interfaccia di stato sarebbe utile rendere configurabili QoS e retain, usando retained message almeno per gli stati idempotenti.

### Risultato della connessione interpretato sempre come successo

`_on_connect()` scrive sempre “Successfully connected”, indipendentemente dal codice di risultato:

[mqtt.py:61](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/mqtt.py:61>)

Il callback dovrebbe distinguere esplicitamente successo, autenticazione negata, broker non disponibile e altri errori.

### Arresto incompleto del loop

`stop()` chiama `disconnect()` ma non `loop_stop()`:

[mqtt.py:54](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/mqtt.py:54>)

È opportuno assicurare esplicitamente la terminazione del thread Paho e definire cosa succede in caso di arresto mentre il broker è irraggiungibile.

### Client ID con spazio ridotto

Il client ID contiene un numero casuale tra 1000 e 9999. La probabilità di collisione è bassa per installazioni domestiche, ma non trascurabile con più istanze o riavvii ravvicinati. Il client ID dovrebbe essere configurabile o derivato da un identificatore persistente dell’istanza.

## Robustezza funzionale

### Artwork

`get_track_artwork()` presume che la risposta contenga sempre la chiave `track.uri`:

[utils.py:48](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/utils.py:48>)

Possibili problemi:

- URI assente o `None`;
- chiave mancante nella risposta;
- eccezione del backend;
- immagine con URI non HTTP ma diverso da `/local`.

La riga `return image` è inoltre codice morto e fa riferimento a una variabile inesistente:

[utils.py:56](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/mopiqtt/utils.py:56>)

Attualmente non è raggiungibile, ma segnala che il ramo non è stato ripulito o testato.

### Parsing dei titoli stream

`describe_stream()` divide il titolo su tutti i trattini ma conserva soltanto i primi due elementi. Un titolo come `Artist - Song - Live` perde `Live`. Anche un valore `None` provocherebbe un errore.

### Indice della traccia

Durante `track_playback_started`, il codice calcola `curr + 1` assumendo che `tracklist.index()` restituisca sempre un intero. Un risultato assente o inatteso produrrebbe un errore proprio durante un evento centrale di playback.

### Gestione asincrona poco osservabile

Molte chiamate al core Mopidy restituiscono future ma non vengono attese né controllate. L’ordine verso lo stesso actor può essere conservato, ma eventuali errori di `clear`, `add`, `shuffle` o `play` non vengono riportati né al chiamante MQTT né chiaramente nei log.

## Test e qualità

I test presenti verificano solamente:

- creazione dello schema dell’estensione;
- lettura della configurazione;
- costruzione del frontend.

[test_smoke.py](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/tests/test_smoke.py>)

Non sono testati:

- tutti gli handler `on_action_*`;
- routing dei topic;
- connessione, riconnessione e disconnessione;
- autenticazione;
- payload errati;
- eventi Mopidy;
- serializzazione JSON;
- artwork;
- limiti volume;
- playlist non valide;
- compatibilità con differenti versioni di Mopidy/Paho/Pykka;
- concorrenza tra thread.

I test non hanno potuto essere eseguiti nell’ambiente corrente perché Mopidy e pytest non sono installati. Non ho installato dipendenze. Il parsing AST di tutti i file Python è invece riuscito.

Il lint non è stato eseguito perché `flake8` non è installato. Da ispezione statica risultano comunque:

- uso di `log.warn()`, deprecato a favore di `log.warning()`;
- import inutilizzati (`Track`, `Artist`, `Album`, `pkg_resources`);
- nomi non idiomatici come `defaultImage` e `imageUri`;
- inizializzazioni ridondanti di `item = {}`;
- assenza di annotazioni coerenti e controlli statici.

## Packaging

### Wheel erroneamente compatibile con Python 2

[setup.cfg:5](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/setup.cfg:5>) contiene:

```ini
[wheel]
universal = 1
```

L’artefatto risultante si chiama `mopiqtt-1.2.1-py2.py3-none-any.whl`, ma il codice contiene sintassi esclusiva di Python 3, per esempio una variable annotation in `frontend.py`.

Questa è una dichiarazione di compatibilità oggettivamente errata.

### Nessun `python_requires`

[setup.py](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/setup.py>) non specifica la versione minima o massima di Python. Pip può quindi tentare l’installazione su interpreti incompatibili.

### Configurazione di test datata e non riproducibile

[tox.ini](</Users/fabio/Library/CloudStorage/GoogleDrive-marzoccafabio@gmail.com/Il mio Drive/codice/GitHub/Mopiqtt/tox.ini>) presenta diversi punti deboli:

- testa solamente Python 3.7;
- installa Mopidy direttamente dal branch `develop` di GitHub;
- usa `sitepackages = true`;
- usa il vecchio comando `py.test`;
- non definisce una matrice di versioni supportate.

Il branch `develop` è una dipendenza mutevole: la stessa revisione del progetto può passare oggi e fallire domani.

### Dipendenze senza limite superiore

`Mopidy >= 3.0`, `Paho >= 2.0` e `Pykka >= 2.0` permettono automaticamente qualsiasi futura major release. Questo espone a rotture API imprevedibili.

`setuptools` è inoltre dichiarato come dipendenza runtime, anche se il solo uso di `pkg_resources` è un import inutilizzato nel file di setup.

### Build legacy

La configurazione moderna in `pyproject.toml` si limita al backend, mentre tutti i metadati rimangono in `setup.py`. Funziona, ma rende più difficile definire chiaramente:

- versioni Python supportate;
- dipendenze opzionali di sviluppo;
- URL del progetto;
- strumenti di test/lint;
- metadati moderni della licenza.

## Documentazione

La documentazione è sufficiente per iniziare, ma presenta discrepanze operative.

La tabella README descrive la traccia come:

```text
artist - title - album
```

Il codice pubblica invece:

```text
title;artist;album
```

Questo è particolarmente importante perché il formato è parte del protocollo consumato da Node-RED.

Altri punti:

- il link agli esempi punta al branch `Development`, mentre il branch principale è `main`;
- anche un’immagine nel README Node-RED punta a `Development`;
- gli esempi sono immagini, non flow Node-RED importabili;
- non è documentato QoS/retain;
- non sono documentati timeout, riconnessione o semantica degli errori;
- non è descritto il modello di sicurezza consigliato;
- il changelog contiene `ploadshf`, mentre il codice usa `ploadshfl`;
- sono presenti refusi come `paho-mqqt` e `Added Added`;
- il link nei crediti per `magcode` contiene un carattere `>` errato.

## Aspetti positivi

- Obiettivo molto chiaro e scope contenuto.
- Buona separazione tra trasporto MQTT e logica Mopidy.
- Registrazione dell’estensione Mopidy semplice e corretta.
- Password configurata come `config.Secret`, evitando esposizione involontaria nei log/config dump.
- Uso esplicito della callback API Paho v2.
- Mapping automatico tra `on_action_*` e topic MQTT elegante ed estendibile.
- Volume limitato correttamente all’intervallo 0–100.
- Playlist, tracklist e risultati di ricerca pubblicati come JSON strutturato.
- Distribuzione include correttamente `ext.conf` e licenza.
- Artefatti `1.2.1` presenti localmente coerenti con i sorgenti corrispondenti.
- Licenza e changelog sono presenti.

## Piano di intervento consigliato

Ordine suggerito:

1. Mettere una barriera di validazione/eccezioni nel callback MQTT.
2. Rendere non distruttivo il caricamento di playlist e stream.
3. Inoltrare i comandi attraverso la mailbox Pykka.
4. Aggiungere test unitari per tutti gli handler e i casi di input errato.
5. Correggere packaging: eliminare universal wheel, aggiungere `python_requires` e matrice Python reale.
6. Rendere configurabili TLS, QoS, retain, client ID e riconnessione.
7. Pubblicare uno snapshot iniziale dello stato al collegamento MQTT.
8. Allineare README e protocollo effettivo.
9. Modernizzare test e build, con dipendenze riproducibili e CI.
10. Pulire codice morto, import inutilizzati e API deprecate.

Nel complesso, la base è valida per un progetto personale o domestico controllato. Per un uso realmente “Production/Stable”, servono soprattutto isolamento degli errori, test comportamentali, sicurezza MQTT e maggiore disciplina nel packaging.