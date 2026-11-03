import time
import board, digitalio

# 입력 이름과 연결된 핀 번호
PINS = {
    "UP": board.D17, "DOWN": board.D22,
    "LEFT": board.D27, "RIGHT": board.D23,
    "CENTER": board.D4,
    "BTN_A": board.D5, "BTN_B": board.D6,
}

# 각 핀을 입력으로 설정 (평소 HIGH, 누르면 LOW)
btns = {}
for name, pin in PINS.items():
    b = digitalio.DigitalInOut(pin)
    b.direction = digitalio.Direction.INPUT
    b.pull = digitalio.Pull.UP
    btns[name] = b

print("20초간 눌러보세요...")
end = time.time() + 20
while time.time() < end:
    pressed = [n for n, b in btns.items() if not b.value]
    if pressed:
        print("PRESSED:", pressed)
        time.sleep(0.2)
    time.sleep(0.01)
print("done")