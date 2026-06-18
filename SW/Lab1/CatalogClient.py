import requests

#TODO gestire in modo alternativo libreria requests se necessario
#TODO: VENGONO GESTITE LE RICONNESSIONI ???????????? (NE AVEVAMO PARLATO MA NON RICORDO)

class CatalogClient:

    ## Costruttore che accetta l'indirizzo del Catalog Server
    def __init__(self, indirizzo_catalog="http://localhost:9093"):
        if indirizzo_catalog.endswith('/'):
            self.indirizzo_catalog = indirizzo_catalog.rstrip('/')
        else :
            self.indirizzo_catalog = indirizzo_catalog
        
        if self.indirizzo_catalog.endswith('/catalog'):
            self.indirizzo_catalog = self.indirizzo_catalog.rstrip('/catalog')

    ## Funzione che ottiene l'intero catalogo (broker + devices + services)
    def get_catalog(self):
        try:
            pathRichiesta= f"{self.indirizzo_catalog}/catalog"
            risp = requests.get(pathRichiesta)
            risp.raise_for_status()  #Solleva un'eccezione per codici di stato HTTP 4xx/5xx
            return risp.json()
        except Exception as ex:
            print(f"Operazione get_catalog non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503

    ## Funzione che ottiene le informazioni del broker MQTT
    def get_broker(self):
        try:
            pathRichiesta= f"{self.indirizzo_catalog}/catalog/broker"
            risp = requests.get(pathRichiesta)
            
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione get_broker non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503

    ## Funzione che ottiene la lista di tutti i device registrati
    def get_devices(self):
        try:
            risp = requests.get(f"{self.indirizzo_catalog}/catalog/devices")
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione get_devices non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503

    ## Funxione che ottiene un singolo device tramite il suo ID
    def get_device(self, id):
        try:
            risp = requests.get(f"{self.indirizzo_catalog}/catalog/devices/{id}")
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione get_device non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503

    ## Funzione che registra un nuovo device o aggiorna un device esistente
    def register_device(self, payload):
        try:
            risp = requests.post(f"{self.indirizzo_catalog}/catalog/devices", json=payload)
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione register_device non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503

    ## Funzione che registra un nuovo servizio o aggiorna un servizio esistente
    def register_service(self, payload):
        try:
            risp = requests.post(f"{self.indirizzo_catalog}/catalog/services", json=payload)
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Operazione register_service non andata a buon fine - {ex}")
            if('risp' in locals()):
                return risp.status_code
            return 503

    ## Funzione che invia un keep-alive PUT per mantenere attivo un device
    def refresh_device(self, id):
        try:
            risp = requests.put(f"{self.indirizzo_catalog}/catalog/devices/{id}")
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Impossibile fare il refresh del device '{id}': {ex}. Verrà riprovato al prossimo ciclo.")
            if('risp' in locals()):
                return risp.status_code
            return 503

    ## Funzione che invia un keep-alive PUT per mantenere attivo un servizio
    def refresh_service(self, idService):
        try:
            risp = requests.put(f"{self.indirizzo_catalog}/catalog/services/{idService}")
            risp.raise_for_status()
            return risp.json()
        except Exception as ex:
            print(f"Impossibile fare il refresh del servizio '{idService}': {ex}. Verrà riprovato al prossimo ciclo.")
            if('risp' in locals()):
                return risp.status_code
            return 503

