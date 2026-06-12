#include "MBED_RPi_Pico_TimerInterrupt.h"

MBED_RPI_PICO_Timer ITimer1(1);
const unsigned long timeout_pir = 30UL * 1000UL * 1000UL;//30UL * 60UL * 1000UL * 1000UL; //microseconds
volatile bool room_occupied_pir = false;

// ISR executed when the timer expires, when no movement has been detected for a time interval equal to timeout_pir
void timeoutHandler(uint alarm_num) {
  room_occupied_pir = false;
  ITimer1.stopTimer();
}

// ISR executed when motion is detected, i.e. when the PIR PIN changes from 0 to 1
void checkPresencePir(){
  room_occupied_pir = true;
  ITimer1.stopTimer(); 
  ITimer1.attachInterruptInterval(timeout_pir, timeoutHandler);
}
