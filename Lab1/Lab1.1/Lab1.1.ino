// #include "MBED_RPi_Pico_TimerInterrupt.h"
// #include <WiFiNINA.h>
#include <Scheduler.h>

// MBED_RPI_PICO_Timer ITimer(0);
int i = 0;
int redStatus = LOW;
int greenStatus = LOW;

// void TimerHandler(unsigned int alarm_num){
//   digitalWrite(2, (PinStatus) !redStatus);
// }

void setup(){
  // pinMode(LEDG, OUTPUT);
  pinMode(2, OUTPUT);
  pinMode(3, OUTPUT);
  // ITimer.attachInterruptInterval(2000000, TimerHandler);
  // ITimer.attachInterruptInterval(5000000, TimerHandler_2);

  Scheduler.startLoop(loop2);
}

void loop(){
  digitalWrite(3, LOW);
  delay(3000);
  digitalWrite(3, HIGH);
  delay(3000);

}


void loop2(){
  digitalWrite(2, LOW);
  delay(7000);
  digitalWrite(2, HIGH);
  delay(7000);

}



