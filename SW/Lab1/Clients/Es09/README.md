# Esercizio 09 -  MQTT Temperature Publisher

## Configurazione e Prerequisiti

Il client (`Es09.py`) recupera l'URI necessario per connettersi al Catalog dal file di configurazione `config-uri-client.json`, che deve trovarsi nella stessa cartella dello script.

Il file JSON deve contenere la chiave `uri_catalog` valorizzata con l'indirizzo IP e la porta del Catalog.

**Esempio di `config-uri-client.json`:**
```json
{
  "uri_catalog": "http://localhost:9093/catalog"
}
```

## Topic MQTT 

Il client interagisce con il broker MQTT utilizzando i seguenti topic:
- **pub_topic** (topic su cui pubblica le rilevazioni della temperatura): `"/tiot/group14/gruppo14_Temp/temperature"`
- **cmd_topic** (topic da cui riceve configurazioni dinamiche): `"/tiot/group14/gruppo14_Temp/commands"`

**Esempi topic MQTT:**
- Rilevazione inviata su `pub_topic`: temperature:
```json
{"bn": "gruppo14_Temp/", "bt": 1781732653, "e": [{"n": "temperature", "v": 22.87, "u": "Cel"}]}
```
- Configurazione ricevuta su `cmd_topic`: 
```json
{"pub_interval": 60}
```