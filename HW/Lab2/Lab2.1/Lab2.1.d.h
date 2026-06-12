#include <PDM.h>
#include "MBED_RPi_Pico_TimerInterrupt.h"

MBED_RPI_PICO_Timer ITimer2(2);
const int n_sound_events = 10;
const int n_sample_per_event = 20;
const int sound_threshold = 1500;
const unsigned long sound_interval = 10UL * 1000UL;//10UL * 60UL * 1000UL; //10 minutes in milliseconds
const int timeout_sound = 20UL * 1000UL * 1000UL;//60UL * 60UL * 1000UL * 1000UL; //60 minutes in microseconds

volatile bool room_occupied_sound = false;
volatile unsigned long eventLog[n_sound_events];
volatile long int last_pos = 0;

// ISR executed when the timer expires, when no sounds has been detected for a time interval equal to timeout_sound
void timeoutHandlerSound(uint alarm_num) {
  room_occupied_sound = false;
  ITimer2.stopTimer();
}

// Function that adds a new event to eventLog and updates the pointer to the latest event
void addEvent(unsigned long ts) {
 last_pos++;
 eventLog[last_pos % n_sound_events] = ts;
}

// Function that checks whether the last n_sound_events occurred within the sound_interval time frame
void checkPresenceSound() {
  if(eventLog[(last_pos + 1) % n_sound_events] != 0 && eventLog[last_pos % n_sound_events] - eventLog[(last_pos + 1) % n_sound_events] < sound_interval){
    room_occupied_sound = true;
    ITimer2.stopTimer(); 
    ITimer2.attachInterruptInterval(timeout_sound, timeoutHandlerSound);
  }
}

// ISR executed every PDM.onReceive(). Inside this ISR all the checks and operations that allow the presence detection take place.
void onPDMdata() {
  int bytesAvailable = PDM.available();
  short sampleBuffer[256];
  int samplesRead;
  PDM.read(sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2;

  int i = 0, cont = 0;
  while (i < samplesRead && cont < n_sample_per_event){
    if (abs(sampleBuffer[i]) >= sound_threshold)
      cont++;
    i++;
  }

  if(cont >= n_sample_per_event){
    addEvent(millis());
    checkPresenceSound();
  }
}

void Init_eventLog(){
  for(int i = 0; i < n_sound_events; i++){
    eventLog[i] = 0;
  }
}
