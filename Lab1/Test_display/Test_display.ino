#include <Wire.h>
#include <LiquidCrystal_PCF8574.h>

LiquidCrystal_PCF8574 lcd(0x27);

void setup() {
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

}







