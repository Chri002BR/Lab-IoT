#include <Scheduler.h>

#include "Lab2.1.a.h"
#include "Lab2.1.b.h"
#include "Lab2.1.c.h"
#include "Lab2.1.d.h"
#include "Lab2.1.e.h"
#include "Lab2.1.f.h"
#include "Lab2.1.g.h"
#include "Lab2.1.h.h"

// defining the const used for PINS 
const int TEMP_PIN = A2;
const int DC_PIN = 5;
const int LED_PIN = 2;
const int PIR_PIN = 4;

// All constants used in the sketch are defined in .h files that implement the required specification
const int execDelay = 1000;

void setup() {
  Serial.begin(9600);

  while(!Serial);
  
  pinMode(TEMP_PIN, INPUT);
  pinMode(DC_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);

  //2.1.c 
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), checkPresencePir, RISING);

  //2.1.d
  PDM.onReceive(onPDMdata);
  if (!PDM.begin(1, 16000)) { // 1 channel (mono), 16 kHz
    Serial.println("Error initializing PDM!");
    while (1);
  }
  Init_eventLog();

  //2.1.g
  //setting the LCD
  lcd.begin(16, 2);
  lcd.setBacklight(255);

  printSpiegazione();

  //Scheduler.startLoop(loopPrintSerial);
  Scheduler.startLoop(loopPrintDisplay);
  Scheduler.startLoop(loopSerielInput);

}

void loop() {
  //2.1.a
  temp = readCelsiusTemperature(TEMP_PIN);
  acPerc = tempToFan(DC_PIN, temp, min_range_dc, max_range_dc);
  acPerc = (acPerc / 255.0) * 100.0;

  //2.1.b
  htPerc = tempToLed(LED_PIN, temp, min_range_led, max_range_led);
  htPerc = (htPerc / 255.0) * 100.0;

  //2.1.e
  combined_room_occupied = room_occupied_sound || room_occupied_pir;

  //2.1.f
  if(combined_room_occupied == true){
    min_range_dc = min_range_dc_pd;
    max_range_dc = max_range_dc_pd;
    min_range_led = min_range_led_pd;
    max_range_led = max_range_led_pd;
  }
  else{
    min_range_dc = min_range_dc_nd;
    max_range_dc = max_range_dc_nd;
    min_range_led = min_range_led_nd;
    max_range_led = max_range_led_nd;
  }

  delay(execDelay);
}

void loopPrintSerial(){
    //2.1.a
  Serial.print("STEP A - T: ");
  Serial.print(temp);
  Serial.print(" - VEL: ");
  Serial.print(acPerc);
  Serial.println("%");

  //2.1.b
  Serial.print("STEP B - BRIGHT: ");
  Serial.print(htPerc);
  Serial.println("%");

  //2.1.c
  Serial.print("STEP C - ROOM OCCUPIED (PIR): ");
  Serial.println(room_occupied_pir == true ? "TRUE" : "FALSE");

  //2.1.d
  Serial.print("STEP D - ROOM OCCUPIED (MIC): ");
  Serial.println(room_occupied_sound == true ? "TRUE" : "FALSE");

  //2.1.e
  Serial.print("STEP E - ROOM OCCUPIED (COMBO): ");
  Serial.println(combined_room_occupied == true ? "TRUE" : "FALSE");

  //2.1.f
  Serial.print("STEP F - ACm: ");
  Serial.print(min_range_dc);
  Serial.print("; ACM: ");
  Serial.print(max_range_dc);
    Serial.print("; HTm: ");
  Serial.print(min_range_led);
    Serial.print("; HTM: ");
  Serial.print(max_range_led);
  Serial.println();

  //2.1.g
  //not necessary
  
  delay(1000);
}

void loopPrintDisplay(){
  displayInfo();
}

void loopSerielInput(){

  if (Serial.available() > 0) {
    // Legge la stringa fino al carattere di nuova riga
    String input = Serial.readStringUntil('\n');
    input.trim(); // Rimuove eventuali spazi bianchi o \r

    // Analizza il comando (deve iniziare con 'P')
    if (input.startsWith("P")) {
      // Estrae l'indice (il carattere dopo la 'P')
      int index = input.substring(1, 2).toInt();
      
      // Estrae il valore (tutto ciò che segue dopo lo spazio)
      float value = input.substring(2).toFloat();

      // Aggiorna la variabile globale corrispondente
      updateSetPoint(index, value);
    } else if (input.startsWith("N")){
      // Estrae l'indice (il carattere dopo la 'P')
      int index = input.substring(1, 2).toInt() + 4;
      
      // Estrae il valore (tutto ciò che segue dopo lo spazio)
      float value = input.substring(2).toFloat();

      // Aggiorna la variabile globale corrispondente
      updateSetPoint(index , value);
    }else {
      Serial.println("Errore: Formato non riconosciuto. Usa P0, P1, P2 o P3.");
    }

    printSpiegazione();
  }



}


