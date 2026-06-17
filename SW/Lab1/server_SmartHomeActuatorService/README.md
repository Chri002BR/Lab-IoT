# Esercizi 03 (E SUCCESSIVE MODIFICHE)

## Configurazione

Il server (`Es03.py`, avviato tramite il relativo file `main.py`) recupera l'URI necessario per connettersi al Catalog e al Log dal file di configurazione `config-uri-client.json`, che deve trovarsi nella stessa cartella degli script.

Il file JSON deve contenere le seguenti chiavi, valorizzate appropriatamente:
- `server_address`: indirizzo IP del server stesso
- `server_port`: porta del server stesso
- `url_log`: URL del server che gestisce i LOG, nella forma `IP:PORT/ENDPOINT`
- `url_catalog`: URL del server che gestisce il CATALOG, nella forma `IP:PORT/ENDPOINT`

**Esempio di `config-uri-client.json`:**
```json
{
  "server_address": "0.0.0.0",
  "server_port": "9090",
  "url_log": "http://127.0.0.1:9092/log/",
  "url_catalog": "http://localhost:9093/catalog/"
}
```

Il server non utilizza il protovollo MQTT.