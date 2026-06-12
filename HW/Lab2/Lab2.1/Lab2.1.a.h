float min_range_dc = 25.0;
float max_range_dc = 30.0;
float temp = 0;
float acPerc = 0;

// Function that, given the pin to which the DC Motor is connected, the detected temperature and the operating range (in Celsius),
// controls the DC Motor and returns its speed (values ​​between 0 and 255). The speed increases as the temperature increases.
float tempToFan(int pin, float temp, float minRange, float maxRange){
  float t = temp - minRange;
  float vel;
  if(t <= 0){
    vel = 0;
  }
  else if (t >= (maxRange - minRange)){
    vel = 255;
  }
  else{
    vel = (255 / (maxRange - minRange)) * t;
  }
  analogWrite(pin, (int) vel);
  return vel;
}

// Function that, given the pin to which the temperature detector is connected, returns, in the form of a float, the detected value in Celsius
float readCelsiusTemperature(int pin){
  int B = 4275;
  int R0 = 100000;
  float Vs;
  float tempK;
  float R = 0;
  float VCC = 1023.0;
  float T0 = 298.15;

  Vs = analogRead(pin);
  R =(VCC/(float)Vs -1.0) * R0;
  tempK = 1.0 / ( (log(R / R0) / B) + (1.0 / T0));
  return tempK - 273.15;
}
