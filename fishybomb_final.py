import time                                    
import os                                      # 이미지 폴더 경로를 만들기 위해 사용
import math                                    # 출렁임 표현 (sin 함수)
import random                                  
import board                                   
import digitalio                               
from PIL import Image, ImageDraw, ImageFont    
from adafruit_rgb_display import st7789        

cs_pin = None                                  
dc_pin = digitalio.DigitalInOut(board.D25)     
rst_pin = digitalio.DigitalInOut(board.D24)    
backlight = digitalio.DigitalInOut(board.D26)  
backlight.switch_to_output()                   
backlight.value = True                         
spi = board.SPI()                              
disp = st7789.ST7789(spi, cs=cs_pin, dc=dc_pin, rst=rst_pin, width=240, height=240, y_offset=80, rotation=180, baudrate=24000000)   

def btn(pin):                                  # 버튼 만들기
    d = digitalio.DigitalInOut(pin)            
    d.switch_to_input(pull=digitalio.Pull.UP)  
    return d                                   

UP = btn(board.D17)                            
DOWN = btn(board.D22)                          
RIGHT = btn(board.D23)                        
LEFT = btn(board.D27)                          
BTN_5 = btn(board.D5)                          

def pressed(b):                                # 눌렸는지 True/False로 알려주는 함수
    return not b.value                         # 풀업이라 눌리면 False -> 뒤집어서 True

this_file = os.path.abspath(__file__)          # 이 코드 파일의 전체 경로
this_folder = os.path.dirname(this_file)       # 이 코드 파일이 들어 있는 폴더
IMG_DIR = os.path.join(this_folder, "images")  # 그 폴더 안의 images 폴더 경로

def load(name):                                # 이미지 한 장을 불러오는 함수
    path = os.path.join(IMG_DIR, name)         # 폴더 경로 + 파일 이름
    picture = Image.open(path)                 # 파일 열기
    picture = picture.convert("RGBA")          # 투명 배경으로 바꾸기
    return picture                             # 불러온 그림 돌려주기

bg = load("bg.png").convert("RGB")             # 배경은 투명이 필요 없어서 RGB로 변환
boat = load("boat.png")                        # 배
hook = load("hook.png")                        # 낚시바늘

# 물고기 종류
KINDS = {                                     
    "small": {"pts": 10,  "y": (70, 185),  "speed": 3},   # 작은 물고기
    "mid":   {"pts": 30,  "y": (70, 185), "speed": 2},   # 중간 물고기
    "big":   {"pts": 50,  "y": (70, 185), "speed": 1},   # 큰 물고기
    "gold":  {"pts": 100, "y": (70, 185),  "speed": 5},   # 황금 물고기
    "bomb":  {"pts": 0,   "y": (70, 185),  "speed": 4},   # 폭탄 물고기
}

LOOKS = ["small", "mid", "big"]                # 폭탄 물고기가 흉내 낼 수 있는 일반 물고기 모양
BOMB_PAD = 12                                  # 폭탄 물고기 이미지는 심지 때문에 위쪽 여백이 이만큼 더 큼

names = []                                     # 불러올 이미지 이름 목록
for k in KINDS:                                # 물고기 종류 이름을 하나씩 꺼내서
    if k != "bomb":                            # 폭탄이 아니면 목록에 넣기
        names.append(k)                        
for k in LOOKS:                                # small, mid, big을 하나씩 꺼내서
    names.append("bomb_" + k)                  # 앞에 "bomb_"를 붙여서 목록에 넣기 (bomb_small, bomb_mid, bomb_big)

sprites = {}                                   # 물고기 이미지를 담을 dictionary (이름 -> 방향/꼬리 -> 이미지)
for kind in names:                             # 이름을 하나씩 꺼내서
    sprites[kind] = {}                         # 그 이름용 빈 사전을 만들고
    for dr in ("R", "L"):                      # 오른쪽/왼쪽 방향마다
        for t in (0, 1):                       # 꼬리 위(0)/아래(1)마다
            sprites[kind][(dr, t)] = load(f"fish_{kind}_{dr}_{t}.png")   # 파일 이름을 만들어서 불러오기

explosion = []                                 # 폭발 이미지를 하나씩 불러와서 list에 넣기
for i in range(4):                             
    explosion.append(load(f"explosion_{i}.png"))   

# 폰트
try:                                           
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)  
    BIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)    
    TITLE = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)  
except OSError:                                
    FONT = ImageFont.load_default()            
    BIG = ImageFont.load_default()             
    TITLE = ImageFont.load_default()           

# 게임 상수
FPS = 20                                       # 1초에 20번 화면 갱신
BOAT_Y = 18                                    # 배 위치
BOAT_SPEED = 7                                 # 배가 한 번에 움직이는 픽셀 크기
HOOK_SPEED = 5                                 # 바늘이 한 번에 움직이는 픽셀 크기
HOOK_MIN = 60                                  # 바늘이 올라올 수 있는 가장 높은 위치
HOOK_MAX = 215                                 # 바늘이 내려갈 수 있는 가장 낮은 위치
LINE_TOP = BOAT_Y + 30                         # 낚싯줄이 시작되는 위치
TAIL_TIME = 0.2                                # 꼬리 모양을 바꾸는 간격
NUM_FISH = 6                                   # 바다에 항상 떠 있는 물고기 수
GAME_TIME = 60                                 # 제한 시간 (초)
BOMB_PENALTY = 50                              # 폭탄 물고기가 터졌을 때 깎이는 점수
BOOM_FRAME = 0.12                              # 폭발 이미지 한 장을 보여주는 시간 (초)
HIT_FISH = 4                                 # 바늘 판정 범위를 사방으로 넓혀주는 픽셀
LEVEL_TIME = 10                                # 몇 초마다 난이도가 올라가는지
MAX_LEVEL = 5                                  # 난이도 최대 단계
BOMB_FREE_TIME = 3                             # 게임을 시작하고 이 시간(초) 동안은 폭탄 물고기가 나오지 않음
BOMB_CAP = 3                                   # 바다에 동시에 있을 수 있는 폭탄 물고기 수 (3마리에서 시작, 3단계마다 1마리씩 늘어남)
IDLE_TIME = 5                                  # 이 시간(초) 동안 아무것도 못 낚으면 감점
IDLE_PENALTY = 10                              # 못 낚은 채 IDLE_TIME이 지날 때마다 깎이는 점수
WOBBLE = 12                                    # 물고기가 위아래로 출렁이는 폭(픽셀). 0이면 출렁임 없음

# 최고 기록
HS_FILE = os.path.join(this_folder, "fishy_highscore.txt")   # this_folder 재사용

def load_best():                               # 저장된 최고 기록을 읽어오는 함수
    try:                                       # 파일이 없거나 이상해도 게임이 멈추지 않게 일단 시도해 보고
        with open(HS_FILE) as fp:              # 파일을 읽기 모드로 열기 (with: 다 쓰면 자동으로 닫아줌)
            text = fp.read()                   # 파일 내용을 읽고
            text = text.strip()                # 앞뒤 공백/줄바꿈을 없애고
            return int(text)                   # 정수로 바꿔서 돌려주기
    except (OSError, ValueError):              # 파일이 없거나 숫자가 아니면 0점으로 시작
        return 0                               

def save_best(value):                          # 새 최고 기록을 파일에 저장하는 함수
    with open(HS_FILE, "w") as fp:             # 파일을 쓰기 모드로 열기
        fp.write(str(value))                   # 점수를 글자로 바꿔서 파일에 쓰기

# 버튼 인식
def wait_5():                                  # 버튼(#5)을 한 번 누르고 뗄 때까지 기다리는 함수
    while pressed(BTN_5):                      # 이미 눌려 있으면 (앞 화면에서 누른 것이 이어지는 경우)
        time.sleep(0.02)                       # 잠깐 쉬면서 뗄 때까지 기다리기
    while not pressed(BTN_5):                  # 아직 안 눌렀으면
        time.sleep(0.02)                       # 잠깐 쉬면서 누를 때까지 기다리기
    while pressed(BTN_5):                      # 눌렀으면
        time.sleep(0.02)                       # 뗄 때까지 기다리기 (게임 시작할 때 버튼이 낚기로 인식되는 것 방지)

# 글자 쓰기
def text_c(d, y, msg, font, color):            
    d.text((120, y), msg, font=font, fill=color, anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))

# 시작 화면
def show_start(best):                          # 시작 화면을 그려서 LCD로 보내는 함수
    img = bg.copy()                            # 배경을 복사해서 그 위에 그리기
    boat_x0 = 120 - boat.width // 2            # 배를 가운데에 두기
    img.paste(boat, (boat_x0, BOAT_Y), boat)   # 배 이미지 붙이기
    d = ImageDraw.Draw(img)                    # 제목 쓰기
    text_c(d, 78, "FISHY", TITLE, (255, 255, 255))         
    text_c(d, 114, "BOMB", TITLE, (255, 90, 60))           
    text_c(d, 150, f"BEST {best}", FONT, (255, 240, 80))   
    text_c(d, 206, "PRESS #5", FONT, (255, 255, 255))      
    disp.image(img)                            # 완성된 화면을 LCD로 전송

# 결과 화면
def show_result(score, caught, best, is_new):  # 결과 화면을 그려서 LCD로 보내는 함수 (점수, 낚은 수, 최고 기록, 신기록 여부)
    img = bg.copy()                            # 배경을 복사해서 그 위에 그리기
    d = ImageDraw.Draw(img)                    # 글자를 쓸 도구
    text_c(d, 50, "TIME UP!", BIG, (255, 255, 255))           # 종료 문구
    text_c(d, 95, f"SCORE {score}", BIG, (255, 240, 80))      # 최종 점수
    text_c(d, 133, f"FISH {caught}", FONT, (255, 255, 255))   # 낚은 물고기 수
    if is_new:                                 # 이번 점수가 최고 기록이면
        text_c(d, 168, "NEW RECORD!", FONT, (255, 90, 60))    # 신기록 문구
    else:                                      # 아니면
        text_c(d, 168, f"BEST {best}", FONT, (200, 220, 255)) # 기존 최고 기록 표시
    text_c(d, 206, "PRESS #5", FONT, (255, 255, 255))         # 다시 하기 안내
    disp.image(img)                            # 완성된 화면을 LCD로 전송

# 난이도/물고기 생성
def get_level():                               # 10초마다 난이도 +1
    past = time.monotonic() - game_start   
    level = int(past // LEVEL_TIME)         
    if level > MAX_LEVEL:                     
        level = MAX_LEVEL                      
    return level                               

def make_fish():                               # 물고기 한 마리를 새로 만드는 함수
    level = get_level()                        
    # 폭탄 개수 세기 (난이도보다 많아지지 않도록)
    bombs = 0                                  
    for other in fishes:                       
        if other["kind"] == "bomb":            
            bombs += 1                         

    passed = time.monotonic() - game_start     
    max_bombs = BOMB_CAP + level // 3          # 지금 단계에서 허용되는 폭탄 수 (3단계마다 1마리씩 늘어남)

    bomb_allowed = True                        
    if passed < BOMB_FREE_TIME:                
        bomb_allowed = False                   
    if bombs >= max_bombs:                     
        bomb_allowed = False                   


    if bomb_allowed:                           
        bomb_weight = 25 + 5 * level           # 폭탄의 비중 (단계가 오를수록 커짐)
    else:                                      
        bomb_weight = 0
    # 각 물고기마다 비중을 둬서 랜덤으로 물고기가 나오도록 만들기 (폭탄 물고기는 제한을 두고)                        
    total = 40 + 25 + 15 + 5 + bomb_weight     
    r = random.randint(1, total)              

    if r <= 40:                              
        kind = "small"                       
    elif r <= 65:                           
        kind = "mid"                           
    elif r <= 80:                             
        kind = "big"                           
    elif r <= 85:                              
        kind = "gold"                          
    else:                                      
        kind = "bomb"                          

    # 폭탄 물고기 이미지 생성
    if kind == "bomb":                        
        look = random.choice(LOOKS)            
        key = "bomb_" + look                   
        pad = BOMB_PAD                         
    else:                                     
        look = kind                            
        key = kind                             
        pad = 0                                

    # 크기 정하기
    picture = sprites[look][("R", 0)]          # 그 모습의 이미지 한 장
    w = picture.width                          # 가로 크기 (판정에 쓰는 크기는 흉내 내는 일반 물고기 크기)
    h = picture.height                         # 세로 크기
    # 방향 무작위
    dr = random.choice(["R", "L"])
    # 시작 위치(왼/오) 정하기             
    if dr == "R":                              
        x = 0                                  
    else:                                      
        x = 240 - w                            
    # 물고기 위치(높이) 랜덤으로
    y_low = KINDS[look]["y"][0]                
    y_high = KINDS[look]["y"][1]               
    y = random.randint(y_low, y_high)          

    # 물고기 정보
    fish = {}                                  
    fish["kind"] = kind                        # 물고기 종류(폭탄인지 아닌지)
    fish["x"] = x                              
    fish["y"] = y                              
    fish["y0"] = y                             # 출렁임의 기준 높이
    fish["look"] = look                        # 흉내 내는 모습
    fish["key"] = key                          # 이미지 이름
    fish["pad"] = pad                          # 이미지 위쪽 여백
    fish["ph"] = random.uniform(0, 6.28)       # 출렁임 시작 위치 (물고기마다 다르게)
    fish["dir"] = dr                           
    fish["w"] = w                              
    fish["h"] = h                             
    return fish                               

def hit(f, conflict=HIT_FISH):                 # 바늘이 물고기 f와 겹쳤는지 알려주는 함수 (conflict: 판정 범위를 넓혀주기 위한 변수)
    hook_left = boat_x - hook.width // 2 - conflict      # 바늘 판정 영역의 왼쪽
    hook_right = boat_x + hook.width // 2 + conflict     # 바늘 판정 영역의 오른쪽
    hook_top = hook_y - conflict                         # 바늘 판정 영역의 위쪽
    hook_bottom = hook_y + hook.height + conflict        # 바늘 판정 영역의 아래쪽
    fish_left = f["x"]                                 
    fish_right = f["x"] + f["w"]                       
    fish_top = f["y"]                                  
    fish_bottom = f["y"] + f["h"]                      
    overlap_x = hook_left < fish_right and hook_right > fish_left      # 가로로 겹치는지
    overlap_y = hook_top < fish_bottom and hook_bottom > fish_top      # 세로로 겹치는지
    if overlap_x and overlap_y:                        
        return True                                    
    return False                                       

# 물고기 잡을 때마다 위에 점수 표시할 위치
def popup_y_position():                        
    y = hook_y - 12                            
    if y < 30:                                
        y = 30                                 
    return y                                   

def draw_frame():                              # 한 프레임을 그려서 LCD로 보내는 함수
    now = time.monotonic()                     
    img = bg.copy()                            
    for f in fishes:                           
        by_name = sprites[f["key"]]            # 그 이름의 이미지 묶음을 꺼내고
        direction_tail = (f["dir"], tail)      # (방향, 꼬리 모양) 쌍을 만들어서
        s = by_name[direction_tail]            # 알맞은 이미지를 고르기
        paste_x = int(f["x"])                  # 붙일 x 위치
        paste_y = f["y"] - f["pad"]            # 붙일 y 위치 (폭탄은 여백만큼 위로 올려서 몸 위치를 맞춤)
        img.paste(s, (paste_x, paste_y), s)    # 물고기 붙이기 (세 번째 인자=투명 처리)
    d = ImageDraw.Draw(img)                    
    d.line([(boat_x, LINE_TOP), (boat_x, hook_y)], fill=(235, 235, 235), width=1)  # 배에서 바늘까지 낚싯줄
    img.paste(hook, (boat_x - hook.width // 2, hook_y), hook)   # 바늘 붙이기
    img.paste(boat, (boat_x - boat.width // 2, BOAT_Y), boat)   # 배 붙이기
    idx = int((now - boom_t) / BOOM_FRAME)     # 폭발이 시작된 뒤 몇 번째 이미지를 보여줄지
    if idx >= 0 and idx < len(explosion):      # 폭발 이미지 위치(가운데) 
        e = explosion[idx]                     
        e_x = boom_pos[0] - e.width // 2       
        e_y = boom_pos[1] - e.height // 2      
        img.paste(e, (e_x, e_y), e)            
    passed = int(now - game_start)             
    left = GAME_TIME - passed                  
    if left < 0:                               
        left = 0                               
    d.text((4, 2), f"SCORE {score}", font=FONT, fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))   # 왼쪽 위에 점수
    d.text((236, 2), f"{left}s", font=FONT, fill=(255, 255, 255), anchor="ra", stroke_width=1, stroke_fill=(0, 0, 0))   # 오른쪽 위에 남은 시간
    if now < popup_until:                      # 물고기 잡았을 때 위에 점수 표시
        d.text(popup_pos, popup_text, font=FONT, fill=(255, 240, 80), anchor="mm", stroke_width=1, stroke_fill=(0, 0, 0))
    disp.image(img)                            # 완성된 그림을 LCD로 전송


# 전체 흐름 (시작 화면 -> 게임 -> 결과 화면 -> 반복)                                       
while True:                                
    best = load_best()                     # 파일에서 최고 기록 읽기
    show_start(best)                       # 시작 화면 보여주기
    wait_5()                               # 버튼(#5)을 누를 때까지 기다리기

    # 게임 상태
    boat_x = 120                           
    hook_y = 100                           
    tail = 0                               
    tail_t = time.monotonic()              
    game_start = time.monotonic()          
    score = 0                              
    press_prev = False                     
    boom_t = -100.0                        # 폭발이 시작된 시각
    boom_pos = (0, 0)                      
    popup_text = ""                        
    popup_pos = (0, 0)                     
    popup_until = 0.0                      
    idle_t = time.monotonic()              # 마지막으로 낚은 시각 (동작 안 할때의 감점을 위해)
    caught = 0                             
    fishes = []                            
    for _ in range(NUM_FISH):              
        f = make_fish()                    
        f["x"] = random.randint(0, 240 - f["w"])   # 시작할 때는 화면 아무 곳에나 물고기 놓기
        fishes.append(f)                   

    while True:                            
        now = time.monotonic()             # 이번 프레임 현재 시각  
        level = get_level()                # 현재 난이도 단계

        if now - game_start >= GAME_TIME:  
            break                          

        if pressed(LEFT):                  
            boat_x -= BOAT_SPEED           
        if pressed(RIGHT):                 
            boat_x += BOAT_SPEED           
        boat_left_limit = boat.width // 2          
        boat_right_limit = 240 - boat.width // 2   
        if boat_x < boat_left_limit:               
            boat_x = boat_left_limit               
        if boat_x > boat_right_limit:              
            boat_x = boat_right_limit              

        if pressed(UP):                    
            hook_y -= HOOK_SPEED           
        if pressed(DOWN):                  
            hook_y += HOOK_SPEED           
        if hook_y < HOOK_MIN:              
            hook_y = HOOK_MIN             
        if hook_y > HOOK_MAX:             
            hook_y = HOOK_MAX              

        press_now = pressed(BTN_5)             
        if press_now and not press_prev:           # 방금 전에 눌리지 않고 지금 눌렸다면
            for f in fishes:               # 물고기를 하나씩 확인해서 폭탄이 아닌 물고기가 바늘과 닿으면 점수 더하고 물고기 낚기
                if f["kind"] != "bomb" and hit(f):   
                    pts = KINDS[f["kind"]]["pts"]   
                    score += pts                    
                    caught += 1                      
                    popup_text = f"+{pts}"           
                    popup_pos = (boat_x, popup_y_position()) 
                    popup_until = now + 0.3         
                    idle_t = now                     # 지금부터 3초를 센다
                    fishes.remove(f)                 
                    fishes.append(make_fish())      
                    break                            # 한 번에 한 마리만 낚기
        press_prev = press_now                    # 이번 버튼 상태를 기억

        # 물고기를 잡지 않고 5초동안 가만히 있다면 점수 10점 감점
        if now - idle_t >= IDLE_TIME:      
            idle_t = now                   
            if score > 0:                  
                score -= IDLE_PENALTY      
                if score < 0:              
                    score = 0              
                popup_text = f"-{IDLE_PENALTY}"    
                popup_pos = (boat_x, popup_y_position())   
                popup_until = now + 0.3    

        for f in fishes:                   # 모든 물고기를 움직이기
            base_speed = KINDS[f["look"]]["speed"]     # 흉내 내는 물고기의 기본 속도
            sp = base_speed * (1 + 0.15 * level)       # 난이도 단계마다 15%씩 빨라짐
            # 화면에 닿으면 방향 전환
            if f["dir"] == "R":            
                f["x"] += sp               
            else:                         
                f["x"] -= sp               
            if f["x"] + f["w"] >= 240:     
                f["x"] = 240 - f["w"]      
                f["dir"] = "L"             
            if f["x"] <= 0:                
                f["x"] = 0                 
                f["dir"] = "R"             
            wy = f["y0"] + WOBBLE * math.sin(now * 2 + f["ph"])   
            # 물고기를 물결 모양으로 움직이게 하기(sin 함수 활용: 새 높이 = 기준 높이 + (출렁이는 폭 × sin(시간에 따라 변하는 값)))
            sea_top = 64                   
            sea_bottom = 222 - f["h"]     
            if wy < sea_top:               
                wy = sea_top               
            if wy > sea_bottom:            
                wy = sea_bottom            
            f["y"] = int(wy)               

        for f in fishes:                  
            if f["kind"] == "bomb" and hit(f, 0):    # 폭탄 물고기에 낚싯바늘이 닿았으면 감점
                score -= BOMB_PENALTY      
                if score < 0:              
                    score = 0              
                boom_t = now               # 폭발 시작 시각 기록
                boom_pos = (boat_x, hook_y + hook.height // 2)   # 폭발 위치는 바늘 근처
                popup_text = f"-{BOMB_PENALTY}"   
                popup_pos = (boat_x, popup_y_position())  
                popup_until = now + 0.3    
                idle_t = now               
                fishes.remove(f)          
                fishes.append(make_fish()) 
                break                      
        # 꼬리 흔드는 모션을 만들기 위해 이미지 2개를 활용해서 번갈아 사용
        if time.monotonic() - tail_t >= TAIL_TIME:   
            if tail == 0:                  
                tail = 1                   
            else:                          
                tail = 0                   
            tail_t = time.monotonic()      # 바꾼 시각 기록

        draw_frame()                       # 화면 그리기

        wait = 1 / FPS - (time.monotonic() - now)    
        if wait > 0:                       
            time.sleep(wait)               
    is_new = (score > best)
    if is_new:                             # 신기록이면 파일에 저장
        save_best(score)                   
    show_result(score, caught, best, is_new)   
    time.sleep(1.0)                        # 마지막 순간에 누르던 버튼이 바로 넘어가지 않게 1초 쉬기
    wait_5()                               # 버튼(#5)을 누르면 시작 화면으로 돌아가기