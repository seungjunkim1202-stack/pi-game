import time
import random
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7789

# ---------- LCD 설정 (Pi 5용: cs=None) ----------
spi = board.SPI()
dc = digitalio.DigitalInOut(board.D25)
disp = st7789.ST7789(spi, width=240, height=240, y_offset=80, rotation=180,
                     cs=None, dc=dc, rst=None, baudrate=24000000)
backlight = digitalio.DigitalInOut(board.D26)
backlight.switch_to_output(value=True)

# ---------- 조이스틱 ----------
def make_button(pin):
    b = digitalio.DigitalInOut(pin)
    b.switch_to_input(pull=digitalio.Pull.UP)
    return b

UP = make_button(board.D17)
DOWN = make_button(board.D22)
LEFT = make_button(board.D27)
RIGHT = make_button(board.D23)
CENTER = make_button(board.D4)

# ---------- 글꼴 ----------
try:
    BIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    MID = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
except OSError:
    BIG = MID = ImageFont.load_default()

DIRS = ["UP", "DOWN", "LEFT", "RIGHT"]

# 위쪽 화살표 모양 (중심 기준 좌표). 다른 방향은 이걸 돌려서 만들어요.
ARROW_UP = [(0, -70), (50, -10), (18, -10), (18, 60), (-18, 60), (-18, -10), (-50, -10)]


def rotate(point, direction):
    x, y = point
    if direction == "UP":
        return (x, y)
    if direction == "RIGHT":
        return (-y, x)
    if direction == "DOWN":
        return (-x, -y)
    return (y, -x)  # LEFT


def draw_arrow(direction):
    img = Image.new("RGB", (240, 240), (25, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(120 + rotate(p, direction)[0], 120 + rotate(p, direction)[1]) for p in ARROW_UP]
    d.polygon(pts, fill=(255, 200, 0))
    disp.image(img)


def draw_text(text, color=(255, 255, 255), font=None):
    img = Image.new("RGB", (240, 240), (25, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((120, 120), text, font=font or BIG, fill=color, anchor="mm")
    disp.image(img)


def draw_input(i, n, remaining):
    # 몇 번째 입력인지(i/n)와 남은 시간을 보여줘요
    img = Image.new("RGB", (240, 240), (25, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((120, 90), f"{i}/{n}", font=BIG, fill=(255, 255, 255), anchor="mm")
    color = (255, 200, 0) if remaining > 3 else (255, 60, 60)
    d.text((120, 160), f"TIME {remaining}", font=MID, fill=color, anchor="mm")
    disp.image(img)


def make_sequence(length):
    return [random.choice(DIRS) for _ in range(length)]


def show_sequence(seq, show_time):
    for direction in seq:
        draw_arrow(direction)
        time.sleep(show_time)
        draw_text("")        # 화살표 사이에 잠깐 비워요
        time.sleep(0.2)


def read_dir():
    # 눌린 방향 이름을 돌려주고, 아무것도 안 눌렸으면 None
    if not UP.value:
        return "UP"
    if not DOWN.value:
        return "DOWN"
    if not LEFT.value:
        return "LEFT"
    if not RIGHT.value:
        return "RIGHT"
    if not CENTER.value:
        return "CENTER"
    return None


def wait_release():
    while read_dir() is not None:   # 손을 뗄 때까지 기다려요
        time.sleep(0.02)


MAX_LEVEL = 5


def level_settings(level):
    length = 3 + level                           # 레벨 1: 4개 ... 레벨 5: 8개
    show_time = max(0.3, 0.9 - 0.12 * (level - 1))  # 화살표가 보이는 시간
    input_time = 4 + 1.5 * length                # 입력 제한 시간(초)
    return length, show_time, input_time


def get_input(i, n, deadline):
    # 방향 하나가 눌릴 때까지 기다려요. 시간이 끝나면 None을 돌려줘요.
    wait_release()
    shown = None
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            return None
        sec = int(left) + 1
        if sec != shown:            # 초가 바뀔 때만 화면을 다시 그려요
            draw_input(i, n, sec)
            shown = sec
        d = read_dir()
        if d in DIRS:
            return d
        time.sleep(0.02)


def play_round(seq, input_time):
    # 한 라운드를 진행하고 "SAFE" / "WRONG" / "TIMEOUT" 중 하나를 돌려줘요
    deadline = time.monotonic() + input_time
    for i, answer in enumerate(seq):
        pressed = get_input(i + 1, len(seq), deadline)
        if pressed is None:
            return "TIMEOUT"
        print("입력:", pressed, "정답:", answer)
        if pressed != answer:
            return "WRONG"
    return "SAFE"


while True:
    draw_text("READY")
    while CENTER.value:      # 가운데를 누를 때까지 기다려요
        time.sleep(0.02)
    wait_release()

    level = 1
    while level <= MAX_LEVEL:
        length, show_time, input_time = level_settings(level)
        draw_text(f"LEVEL {level}", (255, 200, 0), MID)
        time.sleep(1.2)

        seq = make_sequence(length)
        print("레벨", level, "순서:", seq)   # 터미널에서도 정답을 확인할 수 있어요
        show_sequence(seq, show_time)

        result = play_round(seq, input_time)
        if result != "SAFE":
            if result == "TIMEOUT":
                draw_text("TIME UP", (255, 60, 60), MID)
                time.sleep(1)
            draw_text("BOOM!", (255, 60, 60))
            time.sleep(1.5)
            draw_text(f"GAME OVER  LV {level}", (255, 255, 255), MID)
            time.sleep(2.5)
            break

        draw_text("SAFE!", (0, 255, 120))
        time.sleep(1.2)
        level += 1
    else:
        # break 없이 반복이 끝났다 = 모든 레벨 성공
        draw_text("DEFUSED!", (0, 255, 120))
        time.sleep(3)