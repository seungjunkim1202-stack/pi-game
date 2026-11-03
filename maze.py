import time
import board, digitalio
from PIL import Image, ImageDraw
from adafruit_rgb_display import st7789

# ---------- 1. LCD 준비 (시험해서 확인한 설정) ----------
dc = digitalio.DigitalInOut(board.D25)
bl = digitalio.DigitalInOut(board.D26)
bl.switch_to_output()
bl.value = True

spi = board.SPI()
disp = st7789.ST7789(spi, height=240, y_offset=80, rotation=180,
                     cs=None, dc=dc, rst=None, baudrate=24000000)

# ---------- 2. 조이스틱 준비 ----------
def make_button(pin):
    b = digitalio.DigitalInOut(pin)
    b.direction = digitalio.Direction.INPUT
    b.pull = digitalio.Pull.UP
    return b

keys = {
    "up": make_button(board.D17),
    "down": make_button(board.D22),
    "left": make_button(board.D27),
    "right": make_button(board.D23),
}
move = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

# ---------- 3. 미로 지도 (#=벽, .=길, P=시작, E=출구) ----------
MAP = [
    "############",
    "#P.....#...#",
    "#.####.#.#.#",
    "#.#....#.#.#",
    "#.#.####.#.#",
    "#.#......#.#",
    "#.######.#.#",
    "#......#.#.#",
    "#.####.#.#.#",
    "#.#....#...#",
    "#.#.######E#",
    "############",
]
TILE = 20                       # 한 칸 크기(픽셀). 12칸 x 20 = 240

def find_start():
    for y, row in enumerate(MAP):
        for x, ch in enumerate(row):
            if ch == "P":
                return x, y

# ---------- 4. 그림 그리는 함수 ----------
img = Image.new("RGB", (240, 240))
draw = ImageDraw.Draw(img)

def draw_screen(px, py, message=""):
    draw.rectangle((0, 0, 240, 240), fill=(10, 10, 25))
    for y, row in enumerate(MAP):
        for x, ch in enumerate(row):
            x0, y0 = x * TILE, y * TILE
            if ch == "#":
                draw.rectangle((x0, y0, x0 + TILE - 1, y0 + TILE - 1), fill=(70, 70, 130))
            elif ch == "E":
                draw.rectangle((x0, y0, x0 + TILE - 1, y0 + TILE - 1), fill=(220, 60, 60))
    cx, cy = px * TILE + TILE // 2, py * TILE + TILE // 2
    draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(0, 220, 140))
    if message:
        draw.text((90, 110), message, fill=(255, 255, 255))
    disp.image(img)

# ---------- 5. 게임 시작 ----------
px, py = find_start()
was_pressed = {name: False for name in keys}
draw_screen(px, py)

while True:
    changed = False
    for name, button in keys.items():
        now = not button.value                  # 눌렸으면 True
        if now and not was_pressed[name]:       # 방금 새로 눌린 순간만
            dx, dy = move[name]
            nx, ny = px + dx, py + dy
            if MAP[ny][nx] != "#":              # 벽이 아니면 이동
                px, py = nx, ny
                changed = True
        was_pressed[name] = now

    if MAP[py][px] == "E":                      # 출구 도착
        draw_screen(px, py, "CLEAR!")
        time.sleep(2)
        px, py = find_start()
        changed = True

    if changed:
        draw_screen(px, py)
    time.sleep(0.02)