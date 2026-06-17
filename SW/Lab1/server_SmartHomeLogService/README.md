# Esercizi 04

## Configurazione

Il server (`Es04.py`, avviato tramite il relativo file `main.py`) recupera l'URI necessario per connettersi al Catalog e al Log dal file di configurazione `config-uri-client.json`, che deve trovarsi nella stessa cartella degli script.

Il file JSON deve contenere le seguenti chiavi, valorizzate appropriatamente:
- `server_address`: indirizzo IP del server stesso
- `server_port`: porta del server stesso

**Esempio di `config-uri-client.json`:**
```json
{
  "server_address": "0.0.0.0",
  "server_port": "9092"
}
```

Il server non utilizza il protovollo MQTT.