// Receive hardware trigger signals from equipment or test electronic switches and transmit RS232 signals to the Lighting Controller. The Software Part.
// 장비 또는 테스트용 전자스위치로부터 하드웨어 트리거 신호를 받아 조명 컨트롤러로 RS232 신호 전송. 솔루션에 사용되는 소프트웨어 파트.

const DATAIN_PIN = 21 // Interrupt Support Pin base on MEGA 2560
const DATAOUT_PIN = 3 // PWM Digital Pin

volatile boolean current;

void setup() {
  // Initialize serial port
  Serial.begin(9600);
  while (!Serial)
  {
    delay(50);
    continue;
  }
  attachInterrupt(DATAIN_PIN, fn, RISING);
  pinMode(DATAOUT_PIN, OUTPUT);
  Serial.println("Init Complete.");
}
void loop() {
  delay(1000);
}
void fn() {
  delay(1); // Debouncing support. 디바운싱 고려.
  current = digitalRead(DATAIN_PIN);
  Serial.print(current);
  Serial.println(" Read.");
  analogWrite(DATAOUT_PIN, 255);
  Serial.println("PWM 255 Value Set to OUTPUT PIN.");
}
