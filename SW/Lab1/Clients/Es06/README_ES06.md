# Esercizio 09 -  MQTT Temperature Publisher

## Configurazione e Prerequisiti

Il client (`Es06.py`) recupera l'URI necessario per connettersi al Catalog dal file di configurazione `config-uri-client.json`, che deve trovarsi nella stessa cartella dello script.

Il file JSON deve contenere la chiave `uri_catalog` valorizzata con l'indirizzo IP e la porta del Catalog.

**Esempio di `config-uri-client.json`:**
```json
{
  "uri_catalog": "http://localhost:9093/catalog"
}
```

Il client non utilizza il protocollo MQTT.