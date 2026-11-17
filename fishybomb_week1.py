import time                                    
import os                                      # 이미지 폴더 경로를 만들기 위해 사용
import board                                   
import digitalio                               
from PIL import Image, ImageDraw               
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
BTN_A = btn(board.D5)                          

def pressed(b):                                
    return not b.value                         

IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")  # 이 파일 옆 images 폴더 경로

def load(name):                                # 이미지 한 장을 불러오는 함수
    return Image.open(os.path.join(IMG_DIR, name)).convert("RGBA")  # 투명 배경(RGBA)으로 불러오기

bg = load("bg.png").convert("RGB")             # 배경은 RGB로 변환
boat = load("boat.png")                        # 배
hook = load("hook.png")                        # 낚시바늘
fish = {                                       # 작은 물고기 이미지 4장 미리 저장
    ("R", 0): load("fish_small_R_0.png"),      # 오른쪽 방향, 꼬리 위
    ("R", 1): load("fish_small_R_1.png"),      # 오른쪽 방향, 꼬리 아래
    ("L", 0): load("fish_small_L_0.png"),      # 왼쪽 방향, 꼬리 위
    ("L", 1): load("fish_small_L_1.png"),      # 왼쪽 방향, 꼬리 아래
}
FISH_W, FISH_H = fish[("R", 0)].size           # 물고기 가로/세로 크기 (벽에 닿는지 계산용)

# 게임 상수
FPS = 20                                       # 1초에 20번 화면 갱신
BOAT_Y = 18                                    # 배 위치
BOAT_SPEED = 4                                 # 배가 한 번에 움직이는 픽셀 크기
HOOK_SPEED = 3                                 # 바늘이 한 번에 움직이는 픽셀 크기
HOOK_MIN = 60                                  # 바늘이 올라올 수 있는 가장 높은 위치
HOOK_MAX = 215                                 # 바늘이 내려갈 수 있는 가장 낮은 위치
LINE_TOP = BOAT_Y + 30                         # 낚싯줄이 시작되는 위치
FISH_SPEED = 2                                 # 물고기가 한 번에 움직이는 픽셀 크기
TAIL_TIME = 0.2                                # 꼬리 모양을 바꾸는 간격

# 게임 상태
boat_x = 120                                   # 배의 가운데 x 위치
hook_y = 100                                   # 바늘의 현재 깊이
fish_x = 20                                    # 물고기 x 위치
fish_y = 150                                   # 물고기 y 위치
fish_dir = "R"                                 # 물고기 방향
tail = 0                                       # 꼬리 모양 번호
tail_t = time.monotonic()                      # 마지막으로 꼬리를 바꾼 시각

def draw_frame():                              # 한 프레임을 그려서 LCD로 보내는 함수
    img = bg.copy()                            # 배경을 복사해서 그 위에 그림 (원본 배경은 보존)
    img.paste(fish[(fish_dir, tail)], (int(fish_x), fish_y), fish[(fish_dir, tail)])  # 물고기 붙이기 (세 번째 인자=투명 처리)
    d = ImageDraw.Draw(img)                    # 선을 그리기 위한 도구
    d.line([(boat_x, LINE_TOP), (boat_x, hook_y)], fill=(235, 235, 235), width=1)  # 배에서 바늘까지 낚싯줄
    img.paste(hook, (boat_x - hook.width // 2, hook_y), hook)   # 바늘 붙이기
    img.paste(boat, (boat_x - boat.width // 2, BOAT_Y), boat)   # 배 붙이기
    disp.image(img)                            # 완성된 그림을 LCD로 전송


# main
while True:                                    
    start = time.monotonic()                  

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

    fish_x += FISH_SPEED if fish_dir == "R" else -FISH_SPEED  # 물고기를 현재 방향으로 이동
    if fish_x + FISH_W >= 240:                 
        fish_dir = "L"                         
    if fish_x <= 0:                            
        fish_dir = "R"                         

    if time.monotonic() - tail_t >= TAIL_TIME: # 꼬리 바꿀 시간이 되었으면
        tail = 1 - tail                       
        tail_t = time.monotonic()              

    draw_frame()                               # 화면 그리기

    wait = 1 / FPS - (time.monotonic() - start)  # 남은 시간 계산
    if wait > 0:                               
        time.sleep(wait)                       