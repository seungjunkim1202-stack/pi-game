"""ZERO HOUR - 폭탄 해체 게임
Raspberry Pi + 240x240 LCD(ST7789) + 조이스틱으로 하는 방향 기억 게임
"""
import os
import time
import random
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7789

# ================= 하드웨어 설정 =================
# LCD (SPI). Pi 5에서는 cs=None으로 해야 에러가 나지 않아요.
spi = board.SPI()
dc = digitalio.DigitalInOut(board.D25)
disp = st7789.ST7789(spi, width=240, height=240, y_offset=80, rotation=180,
                     cs=None, dc=dc, rst=None, baudrate=24000000)
backlight = digitalio.DigitalInOut(board.D26)
backlight.switch_to_output(value=True)


# 조이스틱 (GPIO). 누르면 0(False)이 되는 풀업 방식이에요.
def make_button(pin):
    b = digitalio.DigitalInOut(pin)
    b.switch_to_input(pull=digitalio.Pull.UP)
    return b


UP = make_button(board.D17)
DOWN = make_button(board.D22)
LEFT = make_button(board.D27)
RIGHT = make_button(board.D23)
CENTER = make_button(board.D4)

# ================= 글꼴 =================
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
try:
    TITLE = ImageFont.truetype(FONT_PATH, 46)
    BIG = ImageFont.truetype(FONT_PATH, 40)
    MID = ImageFont.truetype(FONT_PATH, 24)
    SMALL = ImageFont.truetype(FONT_PATH, 16)
    TINY = ImageFont.truetype(FONT_PATH, 13)
except OSError:
    TITLE = BIG = MID = SMALL = TINY = ImageFont.load_default()

# ================= 게임 설정 =================
DIRS = ["UP", "DOWN", "LEFT", "RIGHT"]
MAX_LEVEL = 5
HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")

# 위쪽 화살표 모양(중심 기준 좌표). 다른 방향은 이걸 돌려서 만들어요.
ARROW_UP = [(0, -70), (50, -10), (18, -10), (18, 60), (-18, 60), (-18, -10), (-50, -10)]

YELLOW = (255, 200, 0)
RED = (255, 60, 60)
GREEN = (0, 255, 120)
WHITE = (255, 255, 255)


# ================= 최고 기록 =================
def load_best():
    # 파일에 저장된 최고 기록(깬 레벨 수)을 읽어요. 없거나 이상하면 0.
    try:
        with open(HIGHSCORE_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_best(value):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(value))
    except OSError:
        print("최고 기록을 저장하지 못했어요")


# ================= 입력 =================
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


# ================= 화면 그리기 =================
def rotate(point, direction):
    x, y = point
    if direction == "UP":
        return (x, y)
    if direction == "RIGHT":
        return (-y, x)
    if direction == "DOWN":
        return (-x, -y)
    return (y, -x)  # LEFT


def draw_arrow(direction, color=YELLOW):
    img = Image.new("RGB", (240, 240), (25, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(120 + rotate(p, direction)[0], 120 + rotate(p, direction)[1]) for p in ARROW_UP]
    d.polygon(pts, fill=color)
    disp.image(img)


def draw_text(text, color=WHITE, font=None):
    img = Image.new("RGB", (240, 240), (25, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((120, 120), text, font=font or BIG, fill=color, anchor="mm")
    disp.image(img)


def draw_input(i, n, remaining):
    # 몇 번째 입력인지(i/n)와 남은 시간을 보여줘요
    img = Image.new("RGB", (240, 240), (25, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((120, 90), f"{i}/{n}", font=BIG, fill=WHITE, anchor="mm")
    color = YELLOW if remaining > 3 else RED
    d.text((120, 160), f"TIME {remaining}", font=MID, fill=color, anchor="mm")
    disp.image(img)


def draw_result(title, color, cleared, new_record):
    # 게임 오버 / 해체 성공 화면. 깬 레벨 수와 신기록 표시
    img = Image.new("RGB", (240, 240), (25, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((120, 85), title, font=MID, fill=color, anchor="mm")
    d.text((120, 135), f"CLEARED {cleared}/{MAX_LEVEL}", font=SMALL, fill=WHITE, anchor="mm")
    if new_record:
        d.text((120, 180), "NEW RECORD!", font=MID, fill=YELLOW, anchor="mm")
    disp.image(img)


def make_title_bg(best):
    img = Image.new("RGB", (240, 240))
    d = ImageDraw.Draw(img)
    for y in range(240):                       # 위쪽이 붉은 어두운 그라데이션
        r = int(55 - 45 * y / 240)
        d.line((0, y, 240, y), fill=(r, 0, 0))
    for y in range(0, 240, 4):                 # 스캔라인(가로 줄무늬)
        d.line((0, y, 240, y), fill=(0, 0, 0))
    # 폭탄 몸통
    d.ellipse((80, 130, 160, 210), fill=(30, 30, 30), outline=(150, 150, 150), width=3)
    d.rectangle((110, 120, 130, 135), fill=(90, 90, 90))                   # 꼭지
    d.line((120, 120, 140, 105, 158, 108), fill=(200, 160, 80), width=3)   # 심지
    for dx, dy in [(0, -9), (0, 9), (-9, 0), (9, 0), (6, 6), (-6, -6), (6, -6), (-6, 6)]:
        d.line((158, 108, 158 + dx, 108 + dy), fill=YELLOW, width=2)       # 불꽃
    d.ellipse((154, 104, 162, 112), fill=WHITE)
    # 폭탄 위의 타이머와 최고 기록
    d.text((120, 162), "00:10", font=SMALL, fill=(255, 40, 40), anchor="mm")
    d.text((120, 186), f"BEST {best}", font=TINY, fill=YELLOW, anchor="mm")
    # 제목
    d.text((120, 32), "ZERO", font=TITLE, fill=(255, 50, 50), anchor="mm")
    d.text((120, 78), "HOUR", font=TITLE, fill=(255, 50, 50), anchor="mm")
    return img


def draw_title(bg, show_prompt):
    img = bg.copy()
    if show_prompt:
        d = ImageDraw.Draw(img)
        d.text((120, 224), "PRESS CENTER", font=SMALL, fill=WHITE, anchor="mm")
    disp.image(img)


def title_screen(best):
    # 가운데를 누를 때까지 안내 문구를 깜빡여요
    bg = make_title_bg(best)
    blink = True
    last = 0
    draw_title(bg, blink)
    while CENTER.value:
        now = time.monotonic()
        if now - last > 0.6:
            blink = not blink
            draw_title(bg, blink)
            last = now
        time.sleep(0.02)


# ================= 게임 로직 =================
def make_sequence(length):
    return [random.choice(DIRS) for _ in range(length)]


def show_sequence(seq, show_time):
    for direction in seq:
        draw_arrow(direction)
        time.sleep(show_time)
        draw_text("")        # 화살표 사이에 잠깐 비워요
        time.sleep(0.2)


def level_settings(level):
    length = 3 + level                              # 레벨 1: 4개 ... 레벨 5: 8개
    show_time = max(0.3, 0.9 - 0.12 * (level - 1))  # 화살표가 보이는 시간
    input_time = 4 + 1.5 * length                   # 입력 제한 시간(초)
    return length, show_time, input_time


def play_round(seq, input_time):
    # 한 라운드를 진행하고 "SAFE" / "WRONG" / "TIMEOUT" 중 하나를 돌려줘요
    deadline = time.monotonic() + input_time
    for i, answer in enumerate(seq):
        pressed = get_input(i + 1, len(seq), deadline)
        if pressed is None:
            return "TIMEOUT"
        print("입력:", pressed, "정답:", answer)
        if pressed != answer:
            draw_arrow(pressed, RED)      # 틀린 입력: 빨간 화살표
            time.sleep(0.5)
            return "WRONG"
        draw_arrow(pressed, GREEN)        # 맞은 입력: 초록 화살표
        time.sleep(0.25)
    return "SAFE"


def main():
    best = load_best()
    while True:
        title_screen(best)               # 가운데를 누를 때까지 시작 화면
        wait_release()

        level = 1
        cleared = 0                      # 성공한 레벨 수
        while level <= MAX_LEVEL:
            length, show_time, input_time = level_settings(level)
            draw_text(f"LEVEL {level}", YELLOW, MID)
            time.sleep(1.2)

            seq = make_sequence(length)
            print("레벨", level, "순서:", seq)   # 터미널에서도 정답을 확인할 수 있어요
            show_sequence(seq, show_time)

            result = play_round(seq, input_time)
            if result != "SAFE":
                if result == "TIMEOUT":
                    draw_text("TIME UP", RED, MID)
                    time.sleep(1)
                draw_text("BOOM!", RED)
                time.sleep(1.5)
                new_record = cleared > best
                draw_result("GAME OVER", RED, cleared, new_record)
                break

            draw_text("SAFE!", GREEN)
            time.sleep(1.2)
            cleared = level
            level += 1
        else:
            # break 없이 반복이 끝났다 = 모든 레벨 성공
            new_record = cleared > best
            draw_result("DEFUSED!", GREEN, cleared, new_record)

        if cleared > best:               # 최고 기록 갱신
            best = cleared
            save_best(best)
        time.sleep(3)


if __name__ == "__main__":
    main()