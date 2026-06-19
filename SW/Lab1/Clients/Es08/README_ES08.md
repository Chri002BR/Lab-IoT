# Esercizio 08

## Note di Progettazione

## 1. Registrazione
Il client si registra al catalog tramite MQTT, per mantenere la registrazione, un thread in background rinnova l'operazione ogni 60 secondi.

## 2. Query
La richiesta di query avviene tramite un topic apposito ed è rivolta al bridge MQTT del catalog, nel payload è presente il topic su cui il bridge dovrà inviare la risposta. 