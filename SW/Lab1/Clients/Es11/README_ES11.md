# Esercizio 11 

## Configurazione

Il publisher/client (`ActuatorPublisher`, avviato tramite il relativo file principale) recupera l'URI necessario per connettersi al Catalog dal file di configurazione `config-uri-client.json`, che deve trovarsi nella stessa cartella degli script.

Il file JSON deve contenere la seguente chiave, valorizzata appropriatamente:
- `uri_catalog`: URL del server che gestisce il CATALOGO IoT, nella forma `http://IP:PORTA/ENDPOINT`

**Esempio di `config-uri-client.json`:**
```json
{
  "uri_catalog": "http://localhost:9093/catalog"
}

## Note di Progettazione

### 1. Log
I comandi inviati verso Actuator Service vengono salvati nel log tramite REST
