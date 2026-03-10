int pirPin = 4;      // Il pin a cui hai collegato l'OUT del sensore
int ledPin = 5;     // Luce led per la rilevazione del movimento 
int statoPIR = 0;    // Variabile per salvare lo stato del sensore

void setup() {
  Serial.begin(9600);
  pinMode(pirPin, INPUT); // Impostiamo il pin del PIR come INPUT
  pinMode(pirPin, OUTPUT); 
  Serial.println("Inizializzazione sensore in corso...");
  delay(30000); // Il PIR ha bisogno di qualche secondo all'avvio per calibrarsi con la stanza
  Serial.println("Sensore pronto!");
}

void loop() {
  statoPIR = digitalRead(pirPin); // Leggiamo cosa dice il sensore

  if (statoPIR == HIGH) {
    Serial.println("Movimento rilevato!");
    digitalWrite(ledPin, HIGH);
    delay(1000); // Pausa per non intasare il monitor seriale
  } else {
    // Se è LOW, non c'è movimento
    Serial.println("Nessun movimento...");
    digitalWrite(ledPin, LOW);
    delay(1000);
  }
}