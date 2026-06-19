# Laboratorio Hardware - Gruppo 14
## Configurazioni iniziali
Ogni client e ogni server che ne necessitano hanno, all'interno della stessa cartella che contiente l'eseguibile, un file `.json` per inserire le informazioni necessarie. In caso non fossero presenti nel file o mancanti, verranno utilizzate configurazioni di default.

## Server
Ogni server utilizza una porta differente, in modo che possano essere eseguiti sulla stessa macchina. In particolare:
- `9090`: sensors
- `9091`: actuators
- `9092`: log
- `9093`: catalog

## Sequenza di avvio
Per ogni client o server che forniscono informazioini al server di log, è necessario avviare lo stesso prima di eseguire il codice in oggetto. Il catalog dovrebbe essere "up and running" durante tutto il tempo in cui anche solo una parte del progetto è in esecuzione.

## Specifiche varie
Dettagli relativi a ogni esercizio possono essere trovati nei file `README` relativi ai singoli esercizi.

Nelle cartelle di esercizi dove è disponibile il file `main.py` oltre che il file relativo all'esercizio, per avviare lo stesso è necessario eseguire il file `main.py`.

Il file `CatalogClient.py` si riferisce all'esercizio 06. E' all'esterno delle cartelle di esercizio in quanto viene richiamato in puù esercizi.

## Librerie utilizzate

Il seguente frammento di codice racchiude tutte le librerie utilizzate:

```python
from pathlib import Path
import sys
import os
import json
import paho.mqtt.client as mqtt
import cherrypy
import random
import time
import requests
import threading
```
