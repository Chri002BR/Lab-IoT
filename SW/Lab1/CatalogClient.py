import requests

#TODO il indirizzo_catalog non è localhost, ma l'ip del server
#TODO gestire in modo alternativo libreria requests se necessario
#TODO rivedere commenti generati AI

# Configurazione del logging per stampare i warning in caso di errore di connessione
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CatalogClient:
    def __init__(self, indirizzo_catalog="http://localhost:9093"):
        # Rimuove l'eventuale slash finale per evitare doppi slash negli URL
        #self.indirizzo_catalog = indirizzo_catalog.rstrip('/') #TODO non è necessario, basta assicurarsi che l'indirizzo passato sia senza slash finale
        self.indirizzo_catalog = indirizzo_catalog


    # ── GET METHODS ──────────────────────────────────────────────────────────

    def get_catalog(self):
        #Ottiene l'intero catalogo (broker + devices + services)
        try:
            pathRichiesta= f"{self.indirizzo_catalog}/catalog"
            risp = requests.get(pathRichiesta)
            risp.raise_for_status()  #Solleva un'eccezione per codici di stato HTTP 4xx/5xx
            return risp.json()
        except Exception as ex:
            print(f"Operazione get_catalog non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503 #Codice errore 

    def get_broker(self):
        #Ottiene le informazioni del broker MQTT
        try:
            pathRichiesta= f"{self.indirizzo_catalog}/catalog/broker"
            risp = requests.get(pathRichiesta)
            
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione get_broker non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503 #Codice errore 

    def get_devices(self):
        #Ottiene la lista di tutti i device registrati
        try:
            risp = requests.get(f"{self.indirizzo_catalog}/catalog/devices")
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione get_devices non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503 #Codice errore 

    def get_device(self, id):
        #Ottiene un singolo device tramite il suo ID
        try:
            risp = requests.get(f"{self.indirizzo_catalog}/catalog/devices/{id}")
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione get_device non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503 #Codice errore 

    # ── POST / REGISTRATION METHODS ──────────────────────────────────────────

    def register_device(self, payload):
        #Registra un nuovo device (o aggiorna se già esistente
        try:
            risp = requests.post(f"{self.indirizzo_catalog}/catalog/devices", json=payload)
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione register_device non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503 #Codice errore 

    def register_service(self, payload):
        #Registra un nuovo servizio (o aggiorna se già esistente)
        try:
            risp = requests.post(f"{self.indirizzo_catalog}/catalog/services", json=payload)
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione register_service non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503 #Codice errore

    # ── PUT / REFRESH METHODS (Con gestione degli errori per i Thread) ────────

    def refresh_device(self, id):
        #Invia un keep-alive PUT per mantenere attivo un device
        try:
            risp = requests.put(f"{self.indirizzo_catalog}/catalog/devices/{id}")
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            # Requisito 5: Gestione aggraziata dell'errore (Warning log e retry al prossimo ciclo)
            print(f"Impossibile fare il refresh del device '{id}': {ex}. Verrà riprovato al prossimo ciclo.")
            if('risp' in locals()):
                return risp.status_code
            return 503 #Codice errore

    def refresh_service(self, idService):
        #Invia un keep-alive PUT per mantenere attivo un servizio
        try:
            risp = requests.put(f"{self.indirizzo_catalog}/catalog/services/{idService}")
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            # Requisito 5: Gestione aggraziata dell'errore (Warning log e retry al prossimo ciclo)
            print(f"Impossibile fare il refresh del servizio '{idService}': {ex}. Verrà riprovato al prossimo ciclo.")
            if('risp' in locals()):
                return risp.status_code
            return 503 #Codice errore

