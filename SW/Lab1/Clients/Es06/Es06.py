from SW.Lab1.CatalogClient import CatalogClient

# ── DEMO DI FUNZIONAMENTO (Requisito 1 & 2: Demonstrate all APIs) ────────────
if __name__ == "__main__":
    print("=== Test di CatalogClient ===")
    client = CatalogClient("http://localhost:9093")

    # 1. Test di registrazione di un finto device
    mock_device = {
        "id": "mock-sensor-01",
        "description": "Sensore di test per CatalogClient",
        "resources": ["temperature"],
        "endpoint": "http://localhost:9090/sensors"
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