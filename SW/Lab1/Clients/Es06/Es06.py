import requests
import time
import threading
import logging

#TODO togliere i logging e sostituire con print.
#TODO il base_url non è localhost, ma l'ip del server

# Configurazione del logging per stampare i warning in caso di errore di connessione
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CatalogClient:
    def __init__(self, base_url="http://localhost:8080"):
        # Rimuove l'eventuale slash finale per evitare doppi slash negli URL
        self.base_url = base_url.rstrip('/')

    # ── GET METHODS ──────────────────────────────────────────────────────────

    def get_catalog(self):
        """Ottiene l'intero catalogo (broker + devices + services)"""
        try:
            response = requests.get(f"{self.base_url}/catalog")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Errore get_catalog: {e}")
            return None

    def get_broker(self):
        """Ottiene le informazioni del broker MQTT"""
        try:
            response = requests.get(f"{self.base_url}/catalog/broker")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Errore get_broker: {e}")
            return None

    def get_devices(self):
        """Ottiene la lista di tutti i device registrati"""
        try:
            response = requests.get(f"{self.base_url}/catalog/devices")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Errore get_devices: {e}")
            return None

    def get_device(self, device_id):
        """Ottiene un singolo device tramite il suo ID"""
        try:
            response = requests.get(f"{self.base_url}/catalog/devices/{device_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Errore get_device per '{device_id}': {e}")
            return None

    # ── POST / REGISTRATION METHODS ──────────────────────────────────────────

    def register_device(self, payload):
        """Registra un nuovo device (o aggiorna se già esistente)"""
        try:
            response = requests.post(f"{self.base_url}/catalog/devices", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Errore register_device: {e}")
            return None

    def register_service(self, payload):
        """Registra un nuovo servizio (o aggiorna se già esistente)"""
        try:
            response = requests.post(f"{self.base_url}/catalog/services", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Errore register_service: {e}")
            return None

    # ── PUT / REFRESH METHODS (Con gestione degli errori per i Thread) ────────

    def refresh_device(self, device_id):
        """Invia un keep-alive PUT per mantenere attivo un device"""
        try:
            response = requests.put(f"{self.base_url}/catalog/devices/{device_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Requisito 5: Gestione aggraziata dell'errore (Warning log e retry al prossimo ciclo)
            logging.warning(f"Impossibile fare il refresh del device '{device_id}': {e}. Verrà riprovato al prossimo ciclo.")
            return None

    def refresh_service(self, service_id):
        """Invia un keep-alive PUT per mantenere attivo un servizio"""
        try:
            response = requests.put(f"{self.base_url}/catalog/services/{service_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Requisito 5: Gestione aggraziata dell'errore (Warning log e retry al prossimo ciclo)
            logging.warning(f"Impossibile fare il refresh del servizio '{service_id}': {e}. Verrà riprovato al prossimo ciclo.")
            return None


# ── DEMO DI FUNZIONAMENTO (Requisito 1 & 2: Demonstrate all APIs) ────────────
if __name__ == "__main__":
    print("=== Test di CatalogClient ===")
    client = CatalogClient("http://localhost:8080")

    # 1. Test di registrazione di un finto device
    mock_device = {
        "id": "mock-sensor-01",
        "description": "Sensore di test per CatalogClient",
        "resources": ["temperature"],
        "endpoint": "http://localhost:9000/sensor"
    }
    print("\n[POST] Registrazione Device...")
    print(client.register_device(mock_device))

    # 2. Test GET del catalogo completo e del broker
    print("\n[GET] Intero Catalogo:")
    print(client.get_catalog())

    print("\n[GET] Informazioni Broker MQTT:")
    print(client.get_broker())

    # 3. Test GET dei dispositivi
    print("\n[GET] Tutti i Devices:")
    print(client.get_devices())

    print("\n[GET] Singolo Device (mock-sensor-01):")
    print(client.get_device("mock-sensor-01"))

    # 4. Test PUT di Refresh
    print("\n[PUT] Refresh del Device...")
    print(client.refresh_device("mock-sensor-01"))