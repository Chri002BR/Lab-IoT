float min_range_led = 20.0;
float max_range_led = 25.0;
float htPerc = 0;

// This function, given the pin to which the LED is connected (which emulates a resistive heater), the detected temperature,
// and the operating range (in Celsius), controls the LED and returns its brightness (values ​​between 0 and 255).
// The brightness increases as the temperature decreases.
float tempToLed(int pin, float temp, float minRange, float maxRange){
  float t = temp - minRange;
  float bright;
  if(t <= 0){
    bright = 255.0;
  }
  else if (t >= (maxRange - minRange)){
    bright = 0;
  }
  else{
    bright = 255.0 - ((255.0 / (maxRange - minRange)) * t);
  }
  analogWrite(pin, (int) bright);
  return bright;
}
