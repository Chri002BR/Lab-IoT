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

## Formato accettato

il catalog prevede di ricevere iscrizioni secondo questo formato:

{
            "id": "sensor-01",
            "description": "Living room temperature sensor",
            "endpoint": "http://localhost:9090/sensors", #OPZIONALE
            "mqtt": { # OPZIONALE
                "ip": "broker.hivemq.com",
                "port": 1883,
                "topic": "/tiot/group14/living_room/temperature"
                },
            "resources": ["temperature", "humidity"]
          }

# Esercizio 07

## Note di Progettazione

### 1. Thread-Safety Multicanale (REST + MQTT)
Poiché il Catalogo riceve contemporaneamente richieste asincrone sia dall'interfaccia REST( dall ES05) sia dall'interfaccia MQTT, l'integrità del database in memoria e del file JSON è garantita dall'uso di un meccanismo di mutua esclusione (`threading.Lock`), al fine di evitare conflitti per l'accesso al catalog.

### 2. Implementazione del Pattern Request/Response su MQTT
Per gestire le query del catalogo è stato implementato un pattern dinamico di Request/Response:
1. Il client invia la richiesta sul topic di ascolto del catalogo, allegando nel payload il proprio `response_topic`.
2. Il catalogo elabora la richiesta in modo isolato e risponde pubblicando il risultato direttamente sul topic privato indicato dal client.