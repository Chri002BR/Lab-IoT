#include <Wire.h>
#include <LiquidCrystal_PCF8574.h>

LiquidCrystal_PCF8574 lcd(0x27);

const int TEMP_PIN = A2;
const int B = 4275;
const int R0 = 100000;
float temperatura;
float temperaturaK;
float temperaturaC;
float R = 0;
float VCC = 1023.0;
float T0 = 298.15;


void setup() {
  pinMode(TEMP_PIN, INPUT);
  Serial.begin(9600);

  Wire.begin();
  lcd.begin(16, 2);      // LCD 16 colonne, 2 righe
  lcd.setBacklight(255); // accende la retroilluminazione

  lcd.setCursor(0, 0);   // colonna 0, riga 0
  lcd.print("Ciao!");

  lcd.setCursor(0, 1);   // colonna 0, riga 1
  lcd.print("Arduino LCD");

} 

void loop() {
  temperatura = analogRead(TEMP_PIN);
  R =(VCC/(float)temperatura -1.0) * R0;
  temperaturaK = 1.0/( (log(R/R0)/B) + (1.0/T0));
  temperaturaC = temperaturaK - 273.15;

  Serial.print("temperature = ");
  Serial.println(temperaturaC);
  delay(1000);
}







