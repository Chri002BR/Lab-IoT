from pathlib import Path
import sys
import json

# Aggiungo il percorso del progetto alla variabile di ambiente per poter importare il CatalogClient
root_path = Path(__file__).resolve().parents
sys.path.append(str(root_path))

from SW.Lab1.CatalogClient import CatalogClient

## QUESTO SCRIPT HA LA FUNZIONE DI TEST PER IL CATALOG-CLIENT

if __name__ == "__main__":

    # Leggo l'uri del catalog dal file di config
    uri_path = Path(__file__).parent / "config-uri-client.json"
        
    # Recupero l'URL del catalogo dal file di configurazione, prendo il default se non lo trovato
    try:
        with open(uri_path, "r") as f:
            config = json.load(f)
        url_catalog = config.get("uri_catalog", "http://localhost:9093/catalog")
        print(f"Catalog URL: {url_catalog}")
    except Exception: #se non trova su config, usa il default:
        url_catalog = "http://localhost:9093/catalog"
        print(f"Impossibile leggere {uri_path}, uso default {url_catalog}")

    client = CatalogClient(url_catalog)

    disp_prova = {
        "id": "test-sensor-group-14",
        "description": "Sensore di test per CatalogClient (es. 06)",
        "resources": ["temperature"],
    }

    print("\nRegistrazione device (POST):")
    print(client.register_device(disp_prova)) # Test di registrazione di un finto device

    print("\nIntero Catalogo (GET):")
    print(client.get_catalog()) # Test del catalogo e del broker

    print("\nInfo Broker MQTT (GET):")
    print(client.get_broker()) # Test GET del broker

    print("\nStampa tutti i Devices (GET):")
    print(client.get_devices()) #Test prende tutti i dispositivi registrati sul broker

    print("\nSingolo Device (test-sensor-group-14 in GET):")
    print(client.get_device("test-sensor-group-14"))# Testsingolo dispositivo

    print("\nRefresh del Device (PUT):")
    print(client.refresh_device("test-sensor-group-14")) #Test del refresh dispositivo