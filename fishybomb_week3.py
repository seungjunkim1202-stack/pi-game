import time                                    
import os                                      # 이미지 폴더 경로를 만들기 위해 사용
import math                                    # ★출렁임(사인 곡선) 계산에 사용 (수학 함수)
import random                                  # ★2주차 추가: 물고기 종류/위치를 무작위로 고르기 위해 사용
import board                                   
import digitalio                               
from PIL import Image, ImageDraw, ImageFont    # ★ImageFont 추가: 점수/시간 글씨용 (TICK TOCK에서 쓰던 방식)
from adafruit_rgb_display import st7789        

cs_pin = None                                  
dc_pin = digitalio.DigitalInOut(board.D25)     
rst_pin = digitalio.DigitalInOut(board.D24)    
backlight = digitalio.DigitalInOut(board.D26)  
backlight.switch_to_output()                  
backlight.value = True                         
spi = board.SPI()                              
disp = st7789.ST7789(spi, cs=cs_pin, dc=dc_pin, rst=rst_pin, width=240, height=240, y_offset=80, rotation=180, baudrate=24000000)          

def btn(pin):                                  
    d = digitalio.DigitalInOut(pin)            
    d.switch_to_input(pull=digitalio.Pull.UP)  
    return d                                   

UP, DOWN = btn(board.D17), btn(board.D22)      
RIGHT, LEFT = btn(board.D23), btn(board.D27)   
BTN_A = btn(board.D5)                          # 전면 버튼 A: 이번 주차부터 '낚기' 버튼으로 사용

def pressed(b):                                
    return not b.value                         

IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")  # 이 파일 옆 images 폴더 경로

def load(name):                                # 이미지 한 장을 불러오는 함수
    return Image.open(os.path.join(IMG_DIR, name)).convert("RGBA")  # 투명 배경(RGBA)으로 불러오기

bg = load("bg.png").convert("RGB")             # 배경은 RGB로 변환
boat = load("boat.png")                        # 배
hook = load("hook.png")                        # 낚시바늘

# ---------------- 물고기 종류 정보 (★2주차 추가) ----------------
KINDS = {                                      # 물고기 종류별 정보를 사전으로 모아둠
    "small": {"pts": 10,  "y": (70, 110),  "speed": 3},   # 작은 물고기: 10점, 얕은 곳, 보통 속도
    "mid":   {"pts": 30,  "y": (105, 150), "speed": 3},   # 중간 물고기: 30점, 중간 깊이
    "big":   {"pts": 50,  "y": (145, 180), "speed": 2},   # 큰 물고기: 50점, 깊은 곳, 조금 느림
    "gold":  {"pts": 100, "y": (70, 185),  "speed": 5},   # 황금 물고기: 100점, 어디서나, 빠름
    "bomb":  {"pts": 0,   "y": (70, 185),  "speed": 3},   # 폭탄 물고기: 점수 없음(낚으면 폭발)
}

sprites = {}                                   # 물고기 이미지를 담을 사전 (종류 -> 방향/꼬리 -> 이미지)
LOOKS = ["small", "mid", "big"]                # ★폭탄 물고기가 흉내 낼 수 있는 일반 물고기 모양
BOMB_PAD = 12                                  # ★폭탄 물고기 이미지는 심지 때문에 위쪽 여백이 이만큼 더 큼
names = [k for k in KINDS if k != "bomb"] + ["bomb_" + k for k in LOOKS]   # ★불러올 이미지 이름: 일반 4종 + 폭탄 3종
for kind in names:                             # 이름을 하나씩 꺼내서
    sprites[kind] = {}                         # 그 이름용 빈 사전을 만들고
    for dr in ("R", "L"):                      # 오른쪽/왼쪽 방향마다
        for t in (0, 1):                       # 꼬리 위(0)/아래(1)마다
            sprites[kind][(dr, t)] = load(f"fish_{kind}_{dr}_{t}.png")   # 파일 이름을 만들어서 불러오기

explosion = [load(f"explosion_{i}.png") for i in range(4)]   # 폭발 이미지 4장을 리스트로 불러오기

# ---------------- 폰트 (TICK TOCK 코드와 같은 방식) ----------------
try:                                           # 글꼴 파일이 있으면
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)   # 작은 글씨 (점수/시간)
    BIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)    # 큰 글씨 (게임 종료 화면)
    TITLE = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)  # ★3주차 추가: 시작 화면 제목용 아주 큰 글씨
except OSError:                                # 글꼴 파일이 없으면
    FONT = BIG = TITLE = ImageFont.load_default()   # 기본 글꼴 사용 (★TITLE도 같이 지정)

# 게임 상수
FPS = 20                                       # 1초에 20번 화면 갱신
BOAT_Y = 18                                    # 배 위치
BOAT_SPEED = 7                                 # 배가 한 번에 움직이는 픽셀 크기 (★폭탄 물고기의 최고 속도(약 5)보다 빠르게 해서 피할 수 있게 함)
HOOK_SPEED = 5                                 # 바늘이 한 번에 움직이는 픽셀 크기 (★폭탄 물고기가 위아래로 출렁이는 속도보다 충분히 빠르게)
HOOK_MIN = 60                                  # 바늘이 올라올 수 있는 가장 높은 위치
HOOK_MAX = 215                                 # 바늘이 내려갈 수 있는 가장 낮은 위치
LINE_TOP = BOAT_Y + 30                         # 낚싯줄이 시작되는 위치
TAIL_TIME = 0.2                                # 꼬리 모양을 바꾸는 간격
NUM_FISH = 6                                   # ★바다에 항상 떠 있는 물고기 수
GAME_TIME = 60                                 # ★제한 시간 (초)
BOMB_PENALTY = 50                              # ★폭탄 물고기를 낚았을 때 깎이는 점수
BOOM_FRAME = 0.12                              # ★폭발 이미지 한 장을 보여주는 시간 (초)
HIT_MARGIN = 4                                 # ★바늘 판정 범위를 사방으로 넓혀주는 픽셀 (너무 어렵지 않게)
LEVEL_TIME = 10                                # ★몇 초마다 난이도가 올라가는지
MAX_LEVEL = 5                                  # ★난이도 최대 단계
BOMB_FREE_TIME = 6                              # ★게임을 시작하고 이 시간(초) 동안은 폭탄 물고기가 나오지 않음
BOMB_CAP = 3                                   # ★바다에 동시에 있을 수 있는 폭탄 물고기 수 (3마리에서 시작, 3단계마다 1마리씩 늘어남)
IDLE_TIME = 3                                  # ★이 시간(초) 동안 아무것도 못 낚으면 감점
IDLE_PENALTY = 10                              # ★못 낚은 채 IDLE_TIME이 지날 때마다 깎이는 점수
WOBBLE = 12                                    # ★물고기가 위아래로 출렁이는 폭(픽셀). 0이면 출렁임 없음

# ---------------- 3주차 추가: 최고 기록 파일 ----------------
HS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fishy_highscore.txt")   # ★최고 기록을 저장할 파일 경로 (이 코드 파일 옆)

def load_best():                               # ★저장된 최고 기록을 읽어오는 함수
    try:                                       # ★파일이 없거나 이상해도 게임이 멈추지 않게 일단 시도해 보고
        with open(HS_FILE) as fp:              # ★파일을 읽기 모드로 열기 (with: 다 쓰면 자동으로 닫아줌)
            return int(fp.read().strip())      # ★파일 내용(글자)을 정수로 바꿔서 돌려주기
    except (OSError, ValueError):              # ★파일이 없거나 숫자가 아니면
        return 0                               # ★최고 기록은 0점으로 시작

def save_best(value):                          # ★새 최고 기록을 파일에 저장하는 함수
    with open(HS_FILE, "w") as fp:             # ★파일을 쓰기 모드로 열기 (기존 내용은 지워짐)
        fp.write(str(value))                   # ★점수를 글자로 바꿔서 파일에 쓰기

# ---------------- 3주차 추가: 버튼 기다리기와 글자 쓰기 ----------------
def wait_a():                                  # ★A버튼을 한 번 누르고 뗄 때까지 기다리는 함수
    while pressed(BTN_A):                      # ★이미 눌려 있으면 (앞 화면에서 누른 것이 이어지는 경우)
        time.sleep(0.02)                       # ★잠깐 쉬면서 뗄 때까지 기다리기
    while not pressed(BTN_A):                  # ★아직 안 눌렀으면
        time.sleep(0.02)                       # ★잠깐 쉬면서 누를 때까지 기다리기
    while pressed(BTN_A):                      # ★눌렀으면
        time.sleep(0.02)                       # ★뗄 때까지 기다리기 (게임 시작할 때 A가 낚기로 인식되는 것 방지)

def text_c(d, y, msg, font, color):            # ★글자를 가로 가운데(x=120)에 테두리와 함께 쓰는 함수
    d.text((120, y), msg, font=font, fill=color, anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))   # ★anchor="mm": 가운데 기준, 검은 테두리

# ---------------- 3주차 추가: 시작 화면 ----------------
def show_start(best):                          # ★시작 화면을 그려서 LCD로 보내는 함수
    img = bg.copy()                            # ★배경을 복사해서 그 위에 그리기
    img.paste(boat, (120 - boat.width // 2, BOAT_Y), boat)   # ★배를 화면 가운데 위쪽에 붙이기
    for key, x, y in (("small", 14, 150), ("gold", 170, 135), ("bomb_mid", 20, 188), ("big", 172, 176)):   # ★장식으로 넣을 물고기 (이미지 이름, x, y)
        s = sprites[key][("R", 0)]             # ★그 물고기의 오른쪽을 보는 이미지
        img.paste(s, (x, y), s)                # ★투명 처리하며 붙이기
    d = ImageDraw.Draw(img)                    # ★글자를 쓸 도구
    text_c(d, 78, "FISHY", TITLE, (255, 255, 255))         # ★제목 윗줄
    text_c(d, 114, "BOMB", TITLE, (255, 90, 60))           # ★제목 아랫줄 (빨간색)
    text_c(d, 150, f"BEST {best}", FONT, (255, 240, 80))   # ★지금까지의 최고 기록
    text_c(d, 206, "PRESS #5", FONT, (255, 255, 255))       # ★시작 안내
    disp.image(img)                            # ★완성된 화면을 LCD로 전송

# ---------------- 3주차 추가: 결과 화면 ----------------
def show_result(score, caught, best, is_new):  # ★결과 화면을 그려서 LCD로 보내는 함수 (점수, 낚은 수, 최고 기록, 신기록 여부)
    img = bg.copy()                            # ★배경을 복사해서 그 위에 그리기
    d = ImageDraw.Draw(img)                    # ★글자를 쓸 도구
    text_c(d, 50, "TIME UP!", BIG, (255, 255, 255))           # ★종료 문구
    text_c(d, 95, f"SCORE {score}", BIG, (255, 240, 80))      # ★최종 점수
    text_c(d, 133, f"FISH {caught}", FONT, (255, 255, 255))   # ★낚은 물고기 수
    if is_new:                                 # ★이번 점수가 최고 기록이면
        text_c(d, 168, "NEW RECORD!", FONT, (255, 90, 60))    # ★신기록 문구
    else:                                      # ★아니면
        text_c(d, 168, f"BEST {best}", FONT, (200, 220, 255)) # ★기존 최고 기록 표시
    text_c(d, 206, "PRESS #5", FONT, (255, 255, 255))          # ★다시 하기 안내
    disp.image(img)                            # ★완성된 화면을 LCD로 전송

def get_level():                               # ★지금 난이도 단계를 계산하는 함수
    elapsed = time.monotonic() - game_start    # 게임 시작 후 지난 시간
    return min(MAX_LEVEL, int(elapsed // LEVEL_TIME))   # 10초마다 1단계, 최대 5단계

def make_fish():                               # ★물고기 한 마리를 새로 만드는 함수
    level = get_level()                        # 난이도 단계
    weights = [40, 25, 15, 5, 25 + 5 * level]  # 종류별 나올 확률 (마지막=폭탄, 처음 약 23%에서 단계가 오를수록 늘어남)
    kind = random.choices(list(KINDS), weights)[0]   # 확률에 따라 종류 하나 고르기
    bombs = sum(1 for f in fishes if f["kind"] == "bomb")   # ★지금 바다에 있는 폭탄 물고기 수
    too_early = time.monotonic() - game_start < BOMB_FREE_TIME   # ★게임 시작한 지 얼마 안 됐는지 (폭탄 없는 시간 안인지)
    if kind == "bomb" and (bombs >= BOMB_CAP + level // 3 or too_early):   # ★폭탄이 허용 수 이상이거나 아직 너무 이른 시간이면 (바다가 폭탄으로 가득 차는 것 방지)
        kind = random.choices(list(KINDS)[:4], weights[:4])[0]   # ★폭탄 말고 다른 물고기로 다시 고르기
    look = random.choice(LOOKS) if kind == "bomb" else kind   # ★폭탄이면 일반 물고기 중 하나의 모습으로 위장
    key = "bomb_" + look if kind == "bomb" else kind          # ★사용할 이미지 이름
    pad = BOMB_PAD if kind == "bomb" else 0    # ★폭탄 이미지의 위쪽 여백 (그림 위치 보정용)
    w, h = sprites[look][("R", 0)].size        # ★판정에 쓰는 가로/세로는 흉내 내는 일반 물고기 크기
    dr = random.choice(["R", "L"])             # 헤엄칠 방향을 무작위로
    x = 0 if dr == "R" else 240 - w            # 오른쪽으로 가면 왼쪽 끝에서, 왼쪽으로 가면 오른쪽 끝에서 시작
    y = random.randint(*KINDS[look]["y"])      # ★흉내 내는 물고기가 사는 깊이 안에서 무작위 높이
    return {"kind": kind, "x": x, "y": y, "y0": y, "look": look, "key": key, "pad": pad, "ph": random.uniform(0, 6.28), "dir": dr, "w": w, "h": h}   # 물고기 정보 (y0=기준 높이, ph=출렁임 시작 위치)

def hit(f, margin=HIT_MARGIN):                 # ★바늘이 물고기 f와 겹쳤는지 알려주는 함수 (★margin: 판정 범위를 넓혀주는 픽셀, 안 적으면 HIT_MARGIN)
    hx0 = boat_x - hook.width // 2 - margin            # 바늘 판정 영역의 왼쪽
    hx1 = boat_x + hook.width // 2 + margin            # 바늘 판정 영역의 오른쪽
    hy0 = hook_y - margin                              # 바늘 판정 영역의 위쪽
    hy1 = hook_y + hook.height + margin                # 바늘 판정 영역의 아래쪽
    return hx0 < f["x"] + f["w"] and hx1 > f["x"] and hy0 < f["y"] + f["h"] and hy1 > f["y"]   # 두 사각형이 겹치면 True

def draw_frame():                              # 한 프레임을 그려서 LCD로 보내는 함수
    now = time.monotonic()                     # 지금 시각
    img = bg.copy()                            # 배경을 복사해서 그 위에 그림 (원본 배경은 보존)
    for f in fishes:                           # ★물고기를 하나씩 꺼내서
        s = sprites[f["key"]][(f["dir"], tail)]            # ★이미지 이름/방향/꼬리 모양에 맞는 이미지 고르기
        img.paste(s, (int(f["x"]), f["y"] - f["pad"]), s)  # ★물고기 붙이기 (폭탄은 여백만큼 위로 올려서 몸 위치를 맞춤)
    d = ImageDraw.Draw(img)                    # 선을 그리기 위한 도구
    d.line([(boat_x, LINE_TOP), (boat_x, hook_y)], fill=(235, 235, 235), width=1)  # 배에서 바늘까지 낚싯줄
    img.paste(hook, (boat_x - hook.width // 2, hook_y), hook)   # 바늘 붙이기
    img.paste(boat, (boat_x - boat.width // 2, BOAT_Y), boat)   # 배 붙이기
    idx = int((now - boom_t) / BOOM_FRAME)     # ★폭발이 시작된 뒤 몇 번째 이미지를 보여줄지
    if 0 <= idx < len(explosion):              # ★폭발 이미지 범위 안이면
        e = explosion[idx]                     # 해당 폭발 이미지
        img.paste(e, (boom_pos[0] - e.width // 2, boom_pos[1] - e.height // 2), e)   # 폭발 위치 가운데에 붙이기
    left = max(0, GAME_TIME - int(now - game_start))   # ★남은 시간(초)
    d.text((4, 2), f"SCORE {score}", font=FONT, fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))   # ★왼쪽 위에 점수
    d.text((236, 2), f"{left}s", font=FONT, fill=(255, 255, 255), anchor="ra", stroke_width=1, stroke_fill=(0, 0, 0))   # ★오른쪽 위에 남은 시간
    if now < popup_until:                      # ★점수 글자를 보여줄 시간이면
        d.text(popup_pos, popup_text, font=FONT, fill=(255, 240, 80), anchor="mm", stroke_width=1, stroke_fill=(0, 0, 0))   # ★바늘 근처에 +30 같은 글자
    disp.image(img)                            # 완성된 그림을 LCD로 전송



# ---------------- 3주차 추가: 전체 흐름 (시작 화면 -> 게임 -> 결과 화면 -> 반복) ----------------
try:                                           # ★Ctrl+C로 멈추면 에러 대신 깔끔하게 끝내기 위해 일단 시도해 보고
    while True:                                # ★게임을 계속 다시 할 수 있도록 전체를 반복
        best = load_best()                     # ★파일에서 최고 기록 읽기
        show_start(best)                       # ★시작 화면 보여주기
        wait_a()                               # ★A버튼을 누를 때까지 기다리기

        # 게임 상태 (★이제 게임을 시작할 때마다 새로 초기화한다)
        boat_x = 120                                   # 배의 가운데 x 위치
        hook_y = 100                                   # 바늘의 현재 깊이
        tail = 0                                       # 꼬리 모양 번호
        tail_t = time.monotonic()                      # 마지막으로 꼬리를 바꾼 시각
        game_start = time.monotonic()                  # ★게임 시작 시각 (남은 시간/난이도 계산용)
        score = 0                                      # ★현재 점수
        a_prev = False                                 # ★이전 프레임에서 A버튼이 눌려 있었는지 (한 번 누름만 인식하려고)
        boom_t = -100.0                                # ★폭발이 시작된 시각 (-100: 아직 폭발 없음)
        boom_pos = (0, 0)                              # ★폭발이 그려질 중심 위치
        popup_text = ""                                # ★점수 변화 글자 ("+30" 등)
        popup_pos = (0, 0)                             # ★점수 글자가 나타날 위치
        popup_until = 0.0                              # ★이 시각까지 점수 글자 표시
        idle_t = time.monotonic()                      # ★마지막으로 낚은 시각 (게임 시작 시각에서 출발)
        caught = 0                             # ★낚은 물고기 수 (결과 화면용)
        fishes = []                            # ★바다의 물고기들을 담을 리스트 (매 판 새로 비움)
        for _ in range(NUM_FISH):              # ★물고기 수만큼 반복해서
            f = make_fish()                    # ★물고기를 만들고
            f["x"] = random.randint(0, 240 - f["w"])   # ★시작할 때는 화면 아무 곳에나 놓기
            fishes.append(f)                   # ★리스트에 넣기

        while True:                            # ★한 판의 게임 반복 (제한 시간이 끝나면 break로 빠져나감)
            start = time.monotonic()                  
            now = start                                # ★이번 프레임의 현재 시각
            level = get_level()                        # ★현재 난이도 단계

            if now - game_start >= GAME_TIME:          # ★제한 시간이 끝났으면
                break                                  # ★게임 반복을 끝내기

            if pressed(LEFT):                      
                boat_x -= BOAT_SPEED                   
            if pressed(RIGHT):                         
                boat_x += BOAT_SPEED                   
            boat_x = max(boat.width // 2, min(240 - boat.width // 2, boat_x))  

            if pressed(UP):                            
                hook_y -= HOOK_SPEED                   
            if pressed(DOWN):                          
                hook_y += HOOK_SPEED                   
            hook_y = max(HOOK_MIN, min(HOOK_MAX, hook_y))  

            a_now = pressed(BTN_A)                     # ★A버튼이 지금 눌려 있는지
            if a_now and not a_prev:                   # ★방금 새로 눌렀으면 '낚기' 시도
                for f in fishes:                       # ★물고기를 하나씩 확인해서
                    if f["kind"] != "bomb" and hit(f): # ★폭탄이 아닌 물고기 중 바늘과 겹친 게 있으면 (★폭탄 물고기는 A버튼으로 낚지 않고 닿으면 터진다)
                        pts = KINDS[f["kind"]]["pts"]           # ★그 종류의 점수
                        score += pts                            # ★점수 더하기
                        caught += 1                             # ★낚은 물고기 수 +1 (결과 화면에서 보여줄 용도)
                        popup_text = f"+{pts}"                  # ★표시할 글자
                        popup_pos = (boat_x, max(30, hook_y - 12))  # ★글자 위치는 바늘 위쪽
                        popup_until = now + 0.6                 # ★0.6초 동안 표시
                        idle_t = now                            # ★지금부터 3초를 센다
                        fishes.remove(f)               # ★낚은 물고기는 바다에서 없애고
                        fishes.append(make_fish())     # ★새 물고기를 하나 채워 넣기
                        break                          # ★한 번에 한 마리만 낚기
            a_prev = a_now                             # ★이번 A버튼 상태를 기억

            if now - idle_t >= IDLE_TIME:              # ★IDLE_TIME(3초) 동안 아무것도 못 낚았으면
                idle_t = now                           # ★다시 3초를 새로 센다 (그래서 3초마다 한 번씩 깎임)
                if score > 0:                          # ★깎을 점수가 있을 때만
                    score = max(0, score - IDLE_PENALTY)   # ★10점 깎기 (0점 아래로는 안 내려감)
                    popup_text = f"-{IDLE_PENALTY}"    # ★화면에 보여줄 글자
                    popup_pos = (boat_x, max(30, hook_y - 12))   # ★글자 위치는 바늘 위쪽
                    popup_until = now + 0.6            # ★0.6초 동안 표시

            for f in fishes:                           # ★모든 물고기를 움직이기
                sp = KINDS[f["look"]]["speed"] * (1 + 0.15 * level)    # ★흉내 내는 물고기의 속도 x 난이도 (속도로도 폭탄을 구분 못 하게)
                f["x"] += sp if f["dir"] == "R" else -sp               # ★현재 방향으로 이동
                if f["x"] + f["w"] >= 240:             # ★오른쪽 끝에 닿으면
                    f["x"] = 240 - f["w"]              # ★화면 안으로 되돌리고
                    f["dir"] = "L"                     # ★왼쪽으로 방향 전환
                if f["x"] <= 0:                        # ★왼쪽 끝에 닿으면
                    f["x"] = 0                         # ★화면 안으로 되돌리고
                    f["dir"] = "R"                     # ★오른쪽으로 방향 전환
                wy = f["y0"] + WOBBLE * math.sin(now * 2 + f["ph"])    # ★기준 높이에서 사인 곡선만큼 위아래로 흔들린 높이
                f["y"] = int(max(64, min(222 - f["h"], wy)))           # ★바다(수면~모래) 밖으로 안 나가게 제한해서 저장

            for f in fishes:                       # ★물고기를 하나씩 확인해서
                if f["kind"] == "bomb" and hit(f, 0):   # ★폭탄 물고기에 낚싯줄 끝(바늘)이 닿았으면 (★A버튼과 상관없이, 판정 범위를 넓히지 않고 margin 0)
                    score = max(0, score - BOMB_PENALTY)    # ★50점 깎기 (0점 아래로는 안 내려감)
                    boom_t = now                            # ★폭발 시작 시각 기록
                    boom_pos = (boat_x, hook_y + hook.height // 2)   # ★폭발 위치는 바늘 근처
                    popup_text = f"-{BOMB_PENALTY}"         # ★표시할 글자
                    popup_pos = (boat_x, max(30, hook_y - 12))   # ★글자 위치는 바늘 위쪽
                    popup_until = now + 0.6                 # ★0.6초 동안 표시
                    idle_t = now                            # ★터졌으니 지금부터 3초를 센다
                    fishes.remove(f)               # ★터진 폭탄 물고기는 바다에서 없애고
                    fishes.append(make_fish())     # ★새 물고기를 하나 채워 넣기
                    break                          # ★한 번에 한 마리만 처리하기

            if time.monotonic() - tail_t >= TAIL_TIME: # 꼬리 바꿀 시간이 되었으면
                tail = 1 - tail                       
                tail_t = time.monotonic()              

            draw_frame()                               # 화면 그리기

            wait = 1 / FPS - (time.monotonic() - start)  # 남은 시간 계산
            if wait > 0:                               
                time.sleep(wait)

        is_new = score > best                  # ★이번 점수가 기존 최고 기록보다 높은지
        if is_new:                             # ★신기록이면
            save_best(score)                   # ★파일에 저장 (껐다 켜도 남음)
        show_result(score, caught, best, is_new)   # ★결과 화면 보여주기
        time.sleep(1.0)                        # ★마지막 순간에 누르던 A가 바로 넘어가지 않게 1초 쉬기
        wait_a()                               # ★A버튼을 누르면 시작 화면으로 돌아가기
except KeyboardInterrupt:                      # ★Ctrl+C로 멈췄을 때
    disp.image(Image.new("RGB", (240, 240), (0, 0, 0)))   # ★검은 화면 이미지를 만들어 LCD를 지우고
    backlight.value = False                    # ★백라이트도 끄기
    print("게임을 종료했습니다.")                # ★터미널에 안내 글자 출력