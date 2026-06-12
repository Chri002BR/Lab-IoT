#include <LiquidCrystal_PCF8574.h>
#include <Wire.h>

LiquidCrystal_PCF8574 lcd(0x20);

void displayInfo (){
  lcd.home();
  lcd.clear();
  
  lcd.setCursor(0, 0);
  lcd.print("T:");
  lcd.print(temp, 1);

  lcd.print(" P:");
  lcd.print(combined_room_occupied);

  lcd.setCursor(0, 1);
  lcd.print("AC:");
  lcd.print(acPerc, 0);

  lcd.print("% HT:");
  lcd.print(htPerc, 0);
  lcd.print("%");
  
  delay(5000);
  lcd.home();
  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("AC m:");
  lcd.print(min_range_dc, 1);

  lcd.print(" M:");
  lcd.print(max_range_dc, 1);

  lcd.setCursor(0, 1);
  lcd.print("HT m:");
  lcd.print(min_range_led, 1);

  lcd.print(" M:");
  lcd.print(max_range_led, 1);

  delay(5000);
}
