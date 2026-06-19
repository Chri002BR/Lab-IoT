# Esercizi 13-14 (Smart Home Controller)

## Configurazione

Il controllore centrale (`SmartHomeController`, avviato tramite il relativo file `main.py`) recupera l'URI necessario per connettersi al Catalog dal file di configurazione `config-uri-server.json`, che deve trovarsi nella stessa cartella degli script. 

All'avvio, il servizio effettua una registrazione REST verso il Catalog e, successivamente, gestisce la logica di automazione (ventilatore e led, quest'ultimo simula il funzionamento di un termostato) interfacciandosi con i sensori e gli attuatori tramite protocollo MQTT.

Il file JSON deve contenere la seguente chiave, valorizzata appropriatamente:
- `uri_catalog`: URL del server che gestisce il CATALOG, nella forma `http://IP:PORT/catalog`

**Esempio di `config-uri-server.json`:**
```json
{
  "uri_catalog": "http://localhost:9093/catalog"
}
```

## Note di Progettazione 

### 1. Gestione della Concorrenza e Prevenzione dei Deadlock
La logica di automazione si basa su eventi asincroni generati dai sensori dell'arduino e inviati tramite MQTT e su timer di timeout gestiti in background. Per garantire la stabilità del sistema, è stato implementato un `threading.Lock()` (`self.timer_lock`) che protegge le letture e le scritture delle variabili di stato. 

### 2. Gestione degli Endpoint REST e Scansione Dinamica
Il servizio non memorizza in modo statico i topic degli attuatori. Ogni 60 secondi il controllore interroga il Catalog per aggiornare i topic MQTT dei dispositivi presenti, garantendo la modularità del sistema.

### 3. Temperature di soglia
Le temperature di soglia sono modificabili da terminale. si tratta di soglie minima e massima per ognuno dei due attuatori in uso(ventilatore e led), per ciascuno dei 2 stati possibili(stanza occupata o no), più una soglia che serve a generare l'allarme, da specifica dell'esercizio 13.

## 4. Registrazione
La registrazione al catalog avviene tramite REST, ed è rinnovata ogni 60 secondi da un thread in background