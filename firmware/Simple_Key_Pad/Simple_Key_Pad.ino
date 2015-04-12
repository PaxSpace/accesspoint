#include <Keypad.h>
#include <EEPROM.h>

String adminPin = "";      // Set the Admin Password here!

const byte ROWS = 4; //four rows
const byte COLS = 3; //three columns
const char keys[ROWS][COLS] = {
	{'1','2','3'},
	{'4','5','6'},
	{'7','8','9'},
	{'*','0','#'}
	};
byte rowPins[ROWS] = {9,8,7,6}; //connect to the row pinouts of the keypad
byte colPins[COLS] = {5,4,3}; //connect to the column pinouts of the keypad
	
Keypad keypad = Keypad( makeKeymap(keys), rowPins, colPins, ROWS, COLS );
const byte musicPin = 10;
#define NOTE_C7  2093
#define NOTE_E7  2637
#define NOTE_G7  3136

const byte doorPin = 11;
const int timeToOpen=5000;

String defaultPin = "1234";
String userPin = "";
String enteredPin = "";
int begPw = 0;

const int NORMALSTATE = 0;
const int CHANGESTATE = 1;
int deviceState = 0;

void setup(){
  Serial.begin(9600);
  pinMode(doorPin,OUTPUT);  
  digitalWrite(doorPin,LOW);
  keypad.addEventListener(keypadEvent); //add an event listener for this keypad
  
  int sizePin = EEPROM.read(begPw);
  Serial.println(sizePin);
  if (sizePin == 0 || sizePin == 255) 
  {
    userPin = defaultPin;
  } else
  {
    for (int i = 0; i < sizePin; ++i)
    {
        userPin += char(EEPROM.read(begPw + 1 + i));
    }
  }
  
  Serial.println(userPin);
}
  
void loop(){
  char key = keypad.getKey();
  
  if (key) {
    Serial.println(key);
    switch(deviceState)
    {
      case NORMALSTATE:
        switch (key)
        {
          case '#':
            if (enteredPin == userPin)
            {
                playE(timeToOpen);
                openDoor();
            } else if (enteredPin == adminPin)
            {
              playG(250);
              delay(250);
              playE(250);
              delay(250);
              playC(250);
              delay(250);
              deviceState = 1;
            } else
            {
              playG(250);
              delay(250);
              playC(250);
              delay(250);
            }
            
            enteredPin = "";
            break;
          default:
            enteredPin += key;
            break;
        }
        break;
       
      case CHANGESTATE:
        switch (key)
        {
          case '#':
            storeNewUserPin(enteredPin);
            playC(250);
            delay(250);
            playE(250);
            delay(250);
            playC(250);
            delay(250);
            deviceState = 0;
            enteredPin = "";
            break;
          default:
              enteredPin += key;
            break;
        }
        break;
    }
    
  }
}

void openDoor()
{
  digitalWrite(doorPin,HIGH);
  delay(timeToOpen);
  digitalWrite(doorPin,LOW);
}

void playC(int time)
{
  playNote(NOTE_C7,time);
}

void playE(int time)
{
  playNote(NOTE_E7,time);
}

void playG(int time)
{
  playNote(NOTE_G7,time);
}

void playNote(int note,int time)
{
  tone(musicPin,note,time);
}

//take care of some special events
void keypadEvent(KeypadEvent key){
  switch (keypad.getState()){
    case PRESSED:
      switch (key){
        case '#': 
          playG(250);
          break;
        default:
          playC(250);
          break;
      }
    break;
  }
}

void storeNewUserPin(String pin)
{
  EEPROM.write(begPw,pin.length());
  Serial.println(pin.length());
 
  for (int i = 0; i < pin.length(); ++i)
  {
    EEPROM.write(begPw + i + 1,pin[i]);
    Serial.println(pin[i]);
  }
  
  userPin = pin;
}
