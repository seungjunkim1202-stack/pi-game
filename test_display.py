import time
import board, digitalio
from PIL import Image, ImageDraw
from adafruit_rgb_display import st7789

# 핀 설정: DC(명령/데이터 구분), 백라이트(화면 켜기)
dc_pin = digitalio.DigitalInOut(board.D25)
backlight = digitalio.DigitalInOut(board.D26)
backlight.switch_to_output()
backlight.value = True

# LCD 준비 (Pi 5에서 확인한 설정)
spi = board.SPI()
disp = st7789.ST7789(
    spi, height=240, y_offset=80, rotation=180,
    cs=None, dc=dc_pin, rst=None, baudrate=24000000,
)

# 그림을 만들어서 색을 바꿔가며 LCD에 보내기
img = Image.new("RGB", (240, 240))
draw = ImageDraw.Draw(img)

for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]:
    draw.rectangle((0, 0, 239, 239), fill=color)
    disp.image(img)
    print("color", color)
    time.sleep(0.6)

draw.rectangle((0, 0, 239, 239), fill=(0, 0, 0))
draw.text((20, 110), "READY", fill=(0, 255, 0))
disp.image(img)
print("done")