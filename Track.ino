// Определяем пины для цветов
const int redPin = 9;
const int greenPin = 10;
const int bluePin = 11;

void setup() {
  // Настраиваем пины на выход
  pinMode(redPin, OUTPUT);
  pinMode(greenPin, OUTPUT);
  pinMode(bluePin, OUTPUT);

  // Запускаем серийный порт на той же скорости, что в Python (9600)
  Serial.begin(9600);
  
  // Тестовое мигание при включении
  digitalWrite(redPin, HIGH); delay(200); digitalWrite(redPin, LOW);
  digitalWrite(greenPin, HIGH); delay(200); digitalWrite(greenPin, LOW);
  digitalWrite(bluePin, HIGH); delay(200); digitalWrite(bluePin, LOW);
  
  Serial.println("TrackDuino Ready!");
}

void loop() {
  // Проверяем, пришли ли данные от Python-клиента
  if (Serial.available() > 0) {
    // Читаем строку до символа переноса (\n)
    String command = Serial.readStringUntil('\n');
    command.trim(); // Убираем лишние пробелы или символы переноса

    // Логика переключения цветов
    if (command == "red") {
      setColor(HIGH, LOW, LOW);
    } 
    else if (command == "green") {
      setColor(LOW, HIGH, LOW);
    } 
    else if (command == "blue") {
      setColor(LOW, LOW, HIGH);
    } 
    else if (command == "off") {
      setColor(LOW, LOW, LOW);
    }
    else if (command == "white") {
      setColor(HIGH, HIGH, HIGH);
    }
  }
}

// Функция для удобного управления всеми цветами сразу
void setColor(int r, int g, int b) {
  digitalWrite(redPin, r);
  digitalWrite(greenPin, g);
  digitalWrite(bluePin, b);
}
