# EserciziO 05

## Configurazione

Il server (`Es05.py`, avviato tramite il relativo file `main.py`) recupera il proprio IP e porta, dal file di configurazione `config-uri-client.json`, che deve trovarsi nella stessa cartella degli script.

Il file JSON deve contenere le seguenti chiavi, valorizzate appropriatamente:
- `server_address`: indirizzo IP del server stesso
- `server_port`: porta del server stesso

**Esempio di `config-uri-client.json`:**
```json
{
  "server_address": "0.0.0.0",
  "server_port": "9093"
}
```

Il server non utilizza il protovollo MQTT.