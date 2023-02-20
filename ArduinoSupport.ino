// Want to build a solution that receives a hardware trigger signal from an electronic switch for testing or equipment,
// send a TTL TX signal to a PC, and transmits an RS232 signal from the PC to the lighting controller via a USB jack converter.

// This source code is uploaded to Arduino, which act as the router receiving a 5V digital pulse signal from the electronic switch.

// 장비 또는 테스트용 전자스위치로부터 하드웨어 트리거 신호를 받아 PC로 TTL TX 신호를 인가한 뒤, PC에서 USB 잭 컨버터를 통해 조명 컨트롤러로 RS232 신호를 전송하는 솔루션을 제작하려고 하고 있습니다.
// 이 소스코드는 그 중 전자스위치로부터 5V 디지털 펄스 신호를 받는 라우터를 담당하는 아두이노에 업로드 됩니다.

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
