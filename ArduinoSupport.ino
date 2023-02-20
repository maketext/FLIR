// Receive hardware trigger signals from equipment or test electronic switches and transmit RS232 signals to the Lighting Controller. The Software Part.
// 장비 또는 테스트용 전자스위치로부터 하드웨어 트리거 신호를 받아 조명 컨트롤러로 RS232 신호 전송. 솔루션에 사용되는 소프트웨어 파트.

#include <SoftwareSerial.h>

const int DATAIN_PIN = 2; // Interrupt Support Pin base on MEGA 2560. 2, 3, 21, 20, 19, 18 Digital Pin
const int DATAOUT_PIN = 3; // Serial TX Pin

volatile boolean current;

SoftwareSerial mySerial(10, DATAOUT_PIN); // RX, TX

void fn() {
  Serial.print("Rising Edge Detect: ");
  delayMicroseconds(1000); // Debouncing support. 디바운싱 고려.
  mySerial.write(255);
  Serial.println("Write");
}

void setup() {
  // Initialize serial port
  Serial.begin(9600);
  while (!Serial)
  {
    delay(50);
    continue;
  }
  pinMode(DATAIN_PIN, INPUT_PULLUP);
  pinMode(DATAOUT_PIN, OUTPUT);
  attachInterrupt(0, fn, RISING);
  Serial.println("Init Complete.");

  mySerial.begin(9600);
}
void loop() {
  /*
  int res = digitalRead(DATAIN_PIN);
  Serial.println(res);
  if(res == 1)
  {
    mySerial.write(255);
    Serial.println("255 Value Set to OUTPUT PIN.");
  }*/
  delay(1000);

}
