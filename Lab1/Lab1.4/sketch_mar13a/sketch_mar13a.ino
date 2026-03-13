
int pinMotore = 16;
float step = 25.5;
float speed = 0;
char carattere;

void setup() {
  Serial.begin(9600);


  pinMode(pinMotore, OUTPUT);
  analogWrite(pinMotore, (int) speed);
}

void loop(){
  if(Serial.available() > 0){
    carattere = Serial.read();
    
    switch (carattere){
      case '+':
      if(speed + step > 255){
        Serial.println("Alrady at max speed");
      }else{
        speed += step;
        Serial.println("Increasing speed: ");
        Serial.println(speed);
      }

      break;
      case '-':
        if(speed <= 0){
          Serial.println("Alrady at min speed");
        }else{
          speed -= step;
          Serial.println("Decreasing speed: ");
          Serial.println(speed);
        }
      break;
      default:
      Serial.println("Errore di input");
    }
    analogWrite(pinMotore, (int) speed);
    } 
}








