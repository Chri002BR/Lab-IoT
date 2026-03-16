#include <Scheduler.h>

char carattere;
int redLed=0;
int greenLed = 0;


void printLedStat(int value){
  if(value==1){
    Serial.println("HIGH");
  }else{
    Serial.println("LOW");
  }
}


void setup(){
  Serial.begin(9600);

  pinMode(2, OUTPUT);
  pinMode(3, OUTPUT);

  Scheduler.startLoop(loop2);
  Scheduler.startLoop(loop3);


  while(!Serial);
  Serial.println("Welcome");
}

void loop(){
  if(Serial.available() > 0){
    carattere = Serial.read();
    if(carattere != 'r' && carattere != 'l'){
        Serial.println("Errore !!!!");
      }else{
        if(carattere == 'r'){
          Serial.print("Red LED status: ");
          printLedStat(redLed);
        }else{
          Serial.print("Green LED status: ");
          printLedStat(greenLed);
        }
      }
  }
}


void loop2(){ // GREEN
  digitalWrite(2, LOW);
  greenLed=0;
  delay(8000);
  digitalWrite(2, HIGH);
  greenLed=1;
  delay(8000);
}


void loop3(){ // RED
  digitalWrite(3, LOW);
  redLed=0;
  delay(4000);  
  digitalWrite(3, HIGH);
  redLed=1;   
  delay(4000);   
}

