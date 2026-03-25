#include <PDM.h>

// Creiamo una "scatola" (array) dove mettere i dati audio in arrivo.
// Il microfono ci manda i dati a blocchi, non uno per volta.
short sampleBuffer[256];
int valoreSoglia = 1500;

// Questa variabile tiene il conto di quanti campioni abbiamo effettivamente letto.
// È "volatile" perché viene modificata da una funzione che lavora in background.
volatile int samplesRead;

void setup() {
  // Avviamo la comunicazione con il computer per poter stampare i dati
  Serial.begin(9600);
  while (!Serial); // Aspetta che tu apra il Monitor Seriale

  Serial.println("Avvio microfono...");

  // 1. PDM.onReceive(): Diciamo ad Arduino COSA FARE quando arriva l'audio.
  // In pratica: "Ehi Arduino, ogni volta che il microfono ha dei dati pronti, 
  // molla tutto e vai a eseguire la funzione chiamata 'leggiAudio'."
  PDM.onReceive(leggiAudio);

  // 2. PDM.begin(): Accendiamo fisicamente il microfono.
  // I numeri significano: 1 canale (mono), 16000 Hz (velocità di ascolto).
  if (!PDM.begin(1, 16000)) {
    Serial.println("Errore: Microfono non trovato!");
    while (1); // Se fallisce, blocca tutto qui all'infinito
  }
}

void loop() {
  // Se la funzione in background ha riempito la scatola con dei campioni...
  if (samplesRead > 0) {
    
    int volumeMassimo = 0; // Partiamo da un volume zero

    // Esaminiamo tutti i campioni che abbiamo appena letto
    for (int i = 0; i < samplesRead; i++) {
      
      // I suoni sono onde, quindi hanno valori positivi e negativi.
      // Usiamo abs() per trasformare tutto in positivo (es. -50 diventa 50)
      // così è più facile capire quanto è forte il rumore.
      int valoreAttuale = abs(sampleBuffer[i]);
      
      // Se troviamo un rumore più forte di quello massimo registrato finora, lo salviamo
      // if (valoreAttuale > volumeMassimo) {
      if (valoreAttuale > valoreSoglia) {
        volumeMassimo = valoreAttuale;
        Serial.print("Livello volume: ");
        Serial.println(volumeMassimo);
        break;
      }
    }

    // Stampiamo SOLO il rumore più forte di questo blocco di tempo


    // Diciamo ad Arduino che abbiamo finito di leggere questi dati,
    // così è pronto a riceverne di nuovi
    samplesRead = 0;
    
    // Mettiamo in pausa il programma per un decimo di secondo (100 millisecondi)
    // Questo rende la lettura sul Monitor Seriale lenta e comoda per l'occhio umano!
    delay(100); 
  }
}

// Questa è la funzione "in background" che viene chiamata in automatico
// grazie a PDM.onReceive() che abbiamo impostato nel setup.
void leggiAudio() {
  // 3. PDM.available(): Chiediamo "quanti byte di audio sono pronti da leggere?"
  int bytesDisponibili = PDM.available();

  // 4. PDM.read(): Travasiamo i dati dal microfono alla nostra variabile 'sampleBuffer'
  PDM.read(sampleBuffer, bytesDisponibili);

  // Calcoliamo quanti campioni interi abbiamo letto.
  // Un "byte" è un pezzettino di memoria. Il nostro buffer usa variabili "short"
  // che occupano 2 byte ciascuna. Quindi dividiamo per 2.
  samplesRead = bytesDisponibili / 2;
}