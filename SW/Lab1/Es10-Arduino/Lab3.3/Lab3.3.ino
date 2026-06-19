#include <WiFiNINA.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "arduino_secrets.h" 
#include "connection_parameters.h"

#define LED_PIN 2
#define TEMP_PIN A2

#define FREQ_SEND 5000
#define REG_FREQ 60000

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;
int status = WL_IDLE_STATUS;

unsigned long lastPublishTime = 0;
unsigned long lastRegistrationTime = 0;

//topics MQTT
const String base_topic = "/tiot/group14";
const String registration_topic = "/tiot/group14/catalog/register";
const String temp_topic = "/tiot/group14/temperature";
const String led_topic = "/tiot/group14/led";
const String ACK_topic = "/tiot/group14/catalog/register/response/ArduinoGroup14_arduino_temp";
const String feedback_topic = "/tiot/group14/led/feedback";

// Documenti JSON globali per efficienza -- DEPRECATO --
//const int capacity = JSON_OBJECT_SIZE(2) + JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(4) + 100;
//DynamicJsonDocument doc_rec(capacity);
//DynamicJsonDocument doc_send(capacity);

JsonDocument doc_rec;
JsonDocument doc_snd;

WiFiClient wifiClient;
//PubSubClient mqttClient(broker_address.c_str(), broker_port, callback, wifiClient);
PubSubClient mqttClient(wifiClient);

void callback(char* topic, byte* payload, unsigned int len){
  Serial.print("\n[MQTT] Message received on [");
  Serial.print(topic);
  Serial.println("] ");

  doc_rec.clear();
  DeserializationError error = deserializeJson(doc_rec, (char*) payload);
  if (error) {
    Serial.print(F("deserializeJson() failed with code: "));
    Serial.println(error.c_str());
    return;
  }

  if(String(topic) == ACK_topic){
    Serial.println("\nACK ricevuto con successo");
    return;
  }

  // Lettura valore LED secondo formato SenML
  // Esempio: {"e": [{"n": "led", "v": 1}]}
  JsonObject elem = doc_rec["e"][0];
  if(elem["n"] == "led" && (elem["v"].as<int>() == 1 || elem["v"].as<int>() == 0)){
    digitalWrite(LED_PIN, elem["v"].as<int>());
      Serial.print("LED set to: ");
      Serial.println(elem["v"].as<int>());

      // Invio al broker del feedback
      String body = senMlEncode("led", elem["v"].as<float>(), "bool");
      if (mqttClient.publish(temp_topic.c_str(), body.c_str())) {
        Serial.print("[MQTT] Published feedback: ");
        Serial.println(body);
      } else {
        Serial.println("[MQTT] Publish failed!");
      }
  }
}

// Funzione di riconnessione
void reconnect() {
  while (mqttClient.state() != MQTT_CONNECTED) {
    Serial.print("Tentativo di connessione MQTT...");
    // Il ClientID deve essere unico
    if (mqttClient.connect("ArduinoGroup14")) { 
      Serial.println("connesso");
      // Iscrizione al topic per il controllo del LED
      mqttClient.subscribe(led_topic.c_str());
      mqttClient.subscribe(ACK_topic.c_str());
    } else {
      Serial.print("fallito, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" riprovo tra 5 secondi");
      delay(5000);
    }
  }
}

// Funzione REST per ottenere info dal Catalog
void getCatalogInfo() {
  WiFiClient restClient;
  Serial.println("\n[REST] Connessione al Catalog per ottenere le info...");

  if (restClient.connect(catalog_address, catalog_port)) {
    restClient.print("GET ");
    restClient.print(catalog_rest_endpoint);
    restClient.println(" HTTP/1.1");
    restClient.print("Host: ");
    restClient.println(catalog_address);
    restClient.println("Connection: close");
    restClient.println();

    //lettura della risposta
    while (restClient.connected()) {
      String line = restClient.readStringUntil('\n');
      if (line == "\r") { 
        break; // Header terminati
      }
    }
    doc_rec.clear(); 
    DeserializationError error = deserializeJson(doc_rec, restClient);

    
    if (!error) {
      Serial.println("[REST] JSON analizzato con successo!");
      broker_address = doc_rec["ip"].as<String>(); 
      broker_port = doc_rec["port"];

      Serial.print("[REST] IP Catalog: ");
      Serial.println(broker_address);
      Serial.print("[REST] PORT Catalog: ");
      Serial.println(broker_port);
    } else {
      Serial.print("[REST] Errore parsing JSON: ");
      Serial.print(error.c_str());
      Serial.println(". Utilizzo valori di default");
    }
    
    restClient.stop();
    Serial.println("[REST] Connessione terminata.\n");
  } else {
    Serial.println("[REST] Impossibile connettersi al Catalog.");
  }
}

// Funzione di Registrazione MQTT
void registerToCatalog() {
  JsonDocument doc_reg;
  doc_reg["type"] = "devices";
  doc_reg["id"] = "ArduinoGroup14_arduino_temp";
  doc_reg["description"] = "Temperature reading and LED driving";
  doc_reg["resources"].add("led");
  doc_reg["resources"].add("temperature");
  
  doc_reg["mqtt"]["ip"] = broker_address;
  doc_reg["mqtt"]["port"] = broker_port;
//CAMBIATO
  doc_reg["mqtt"]["topic"]["sensor_topic"] = temp_topic;
  doc_reg["mqtt"]["topic"]["command_topic"] = led_topic;
  doc_reg["mqtt"]["topic"]["feedback_topic"] = feedback_topic;

  String payload;
  serializeJson(doc_reg, payload);

  if (mqttClient.publish(registration_topic.c_str(), payload.c_str())) {
    Serial.print("[MQTT] Registrato al Catalog con successo: ");
    Serial.println(payload);
  } else {
    Serial.println("[MQTT] Registrazione al Catalog fallita!");
  }
}

void setup() {
  // defining pinmode
  pinMode(TEMP_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  
  // Initialize serial and wait for port to open:
  Serial.begin(9600);
  while (!Serial);

  // Check for the WiFi module:
  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Unable to communicate with WiFi module");
    while (true);
  }

  // Attempt to connect to WiFi network:
  while (status != WL_CONNECTED) {
    Serial.print("[WiFi] Trying to connect to: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);
    delay(10000);
  }

  // Connection successful
  Serial.print("[WiFi] Connected with IP Address: ");
  Serial.println(WiFi.localIP());

  getCatalogInfo();

  mqttClient.setBufferSize(2048);
  mqttClient.setServer(broker_address.c_str(), broker_port);
  mqttClient.setCallback(callback);

  reconnect();
  registerToCatalog();
}

void loop() {
  if(mqttClient.state() != MQTT_CONNECTED){
    reconnect();
  }

  unsigned long currentTime = millis();

  // --- TASK 3: Rinnovo della sottoscrizione ogni 1 minuto ---
  if (currentTime - lastRegistrationTime >= REG_FREQ) {
    lastRegistrationTime = currentTime;
    registerToCatalog();
  }
  
  if (currentTime - lastPublishTime >= FREQ_SEND) {
    lastPublishTime = currentTime;

    // Lettura e codifica dei dati
    float currentTemp = readCelsiusTemperature(TEMP_PIN);
    String body = senMlEncode("temp", currentTemp, "Cel");
    
    // Invio al broker
    if (mqttClient.publish(temp_topic.c_str(), body.c_str())) {
      Serial.print("[MQTT] Published: ");
      Serial.println(body);
    } else {
      Serial.println("[MQTT] Publish failed!");
    }
  }

  mqttClient.loop();
}


// -- Method that manually format the SenML JSON --
String senMlEncode(String res, float value, String unit) {
  doc_snd.clear();
  doc_snd["bn"] = "ArduinoGroup14";
  doc_snd["e"][0]["n"] = res;
  doc_snd["e"][0]["t"] = int(millis() / 1000);
  doc_snd["e"][0]["v"] = value;
  doc_snd["e"][0]["u"] = unit;

  String output;
  serializeJson(doc_snd, output);
  return output;
}

// -- Method that reads the temperature from the sensor at "pin" PIN --
float readCelsiusTemperature(int pin){
  int B = 4275;
  int R0 = 100000;
  float Vs;
  float tempK;
  float R = 0;
  float VCC = 1023.0;
  float T0 = 298.15;

  Vs = analogRead(pin);
  R =(VCC/(float)Vs -1.0) * R0;
  tempK = 1.0 / ( (log(R / R0) / B) + (1.0 / T0));
  return tempK - 273.15;
}
