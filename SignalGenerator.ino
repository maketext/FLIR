// 장비에서 나오는 신호를 가상으로 만든 디지털 펄스 신호 생성기 입니다.
// A digital pulse signal generator that virtualizes signals from the equipment.

const int TRIGGER_PIN = 10;

void setup() {
  // Initialize serial port
  Serial.begin(9600);
  while (!Serial)
  {
    delay(50);
    continue;
  }
  pinMode(TRIGGER_PIN, OUTPUT);
  Serial.println("Init Complete.");

}
void loop() {
  analogWrite(TRIGGER_PIN, 255);
  delay(100);
  analogWrite(TRIGGER_PIN, 0);
  delay(3000);
}
