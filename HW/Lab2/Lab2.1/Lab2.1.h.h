
void updateSetPoint(int id, float val) {
  switch (id) {
    case 0:
      min_range_dc_pd = val;
      Serial.print("Set-point 0 aggiornato a: ");
      break;
    case 1:
      max_range_dc_pd = val;
      Serial.print("Set-point 1 aggiornato a: ");
      break;
    case 2:
      min_range_led_pd = val;
      Serial.print("Set-point 2 aggiornato a: ");
      break;
    case 3:
      max_range_led_pd = val;
      Serial.print("Set-point 3 aggiornato a: ");
      break;
    case 4:
      min_range_dc_nd = val;
      Serial.print("Set-point 0 aggiornato a: ");
      break;
    case 5:
      max_range_dc_nd = val;
      Serial.print("Set-point 1 aggiornato a: ");
      break;
    case 6:
      min_range_led_nd = val;
      Serial.print("Set-point 2 aggiornato a: ");
      break;
    case 7:
      max_range_led_nd = val;
      Serial.print("Set-point 3 aggiornato a: ");
      break;
    default:
      Serial.println("Errore: Indice non valido (usa 0, 1, 2 o 3).");
      return;
  }
  Serial.println(val);
}

void printSpiegazione(){
  Serial.println("P = Person detected");
  Serial.println("N = Person not detected");
  Serial.println("0 = min AC temp");
  Serial.println("1 = MAX AC temp");
  Serial.println("2 = min HT temp");
  Serial.println("3 = MAX HT temp");
}

