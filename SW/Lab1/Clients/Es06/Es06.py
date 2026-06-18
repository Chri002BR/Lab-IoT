from SW.Lab1.CatalogClient import CatalogClient
from pathlib import Path

#TODO: TESTARE!!!!!!!!!!!!!! NON è MAI STATO PROVATO

if __name__ == "__main__":

    # Leggo l'uri del catalog dal file di config
    uri_path = Path(__file__).parent / "config-uri-client.json"
        
    # Recupero l'URL del catalogo dal file di configurazione, con fallback al default se non trovato
    try:
        with open(uri_path, "r") as f:
            config = json.load(f)
        self.CATALOG_BASE_URL = config.get("uri_catalog", "http://localhost:9093/catalog")
        print(f"Catalog URL: {self.CATALOG_BASE_URL}")
    except Exception: #se non trova su config, usa il default:
        self.CATALOG_BASE_URL = "http://localhost:9093/catalog"
        print(f"Impossibile leggere {uri_path}, uso default {self.CATALOG_BASE_URL}")

    client = CatalogClient(self.CATALOG_BASE_URL)

    disp_prova = {
        "id": "test-sensor-01",
        "description": "Sensore di test per CatalogClient (es. 06)",
        "resources": ["temperature"],
    }

    # Test di registrazione di un finto device
    print("\n[POST] Registrazione Device...")
    print(client.register_device(disp_prova))

    # Test GET del catalogo completo e del broker
    print("\n[GET] Intero Catalogo:")
    print(client.get_catalog())

    # Test GET del broker
    print("\n[GET] Informazioni Broker MQTT:")
    print(client.get_broker())

    # Test GET dei dispositivi
    print("\n[GET] Tutti i Devices:")
    print(client.get_devices())

    # Test GET di un singolo dispositivo
    print("\n[GET] Singolo Device (test-sensor-01):")
    print(client.get_device("test-sensor-01"))

    # Test PUT di Refresh
    print("\n[PUT] Refresh del Device...")
    print(client.refresh_device("test-sensor-01"))