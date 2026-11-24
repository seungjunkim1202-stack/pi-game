# TICK TOCK
# 게임 흐름: 시작 대기 -> 방향 화살표 4개 보여주기 -> 같은 순서로 입력 -> 성공/실패

import time                                   
import random                                 
import board                                  
import digitalio                              
from PIL import Image, ImageDraw, ImageFont   
from adafruit_rgb_display import st7789       

dc_pin  = digitalio.DigitalInOut(board.D25)
rst_pin = digitalio.DigitalInOut(board.D24)

backlight = digitalio.DigitalInOut(board.D26)
backlight.switch_to_output()
backlight.value = True

spi = board.SPI()
disp = st7789.ST7789(
    spi, width = 240, height = 240, y_offset = 80, rotation = 180, cs = None, dc = dc_pin, rst = rst_pin, baudrate = 24000000
)

# ---------- 조이스틱 ----------
def btn(pin):
    d = digitalio.DigitalInOut(pin)
    d.direction = digitalio.Direction.INPUT
    d.pull = digitalio.Pull.UP
    return d

UP, DOWN = btn(board.D17), btn(board.D22)
RIGHT, LEFT = btn(board.D23), btn(board.D27)
CENTER = btn(board.D4)               # 조이스틱 가운데(누르기) = 4번 핀

# ---------- 글꼴 ----------
try:                                          # 먼저 아래 코드를 시도해 보고, 실패하면 except로 넘어간다
    BIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)  # 큰 글자(크기 40)
    MID = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)  # 중간 글자(크기 24)
except OSError:                               # 글꼴 파일이 없어서 오류가 나면
    BIG = MID = ImageFont.load_default()      # 기본 글꼴로 대신 쓴다(작게 보일 수 있다)

DIRS = ["UP", "DOWN", "LEFT", "RIGHT"]        # 게임에서 쓰는 방향 4개의 이름 목록

# 위쪽 화살표 모양: 화살표의 꼭짓점 좌표 7개. (0,0)이 화살표의 중심, 위쪽이 -y 방향이다.
# 다른 방향의 화살표는 이 좌표를 돌려서 만든다.
ARROW_UP = [(0, -70),                         # 화살촉의 맨 위 꼭짓점
            (50, -10),                        # 화살촉의 오른쪽 아래 끝
            (20, -10),                        # 화살촉과 몸통이 만나는 오른쪽 안쪽 점
            (20, 60),                         # 몸통의 오른쪽 아래 점
            (-20, 60),                        # 몸통의 왼쪽 아래 점
            (-20, -10),                       # 화살촉과 몸통이 만나는 왼쪽 안쪽 점
            (-50, -10)]                       # 화살촉의 왼쪽 아래 끝


def rotate(point, direction):
    x, y = point
    if direction == "UP":
        return (x, y)
    if direction == "RIGHT":
        return (-y, x)
    if direction == "DOWN":
        return (-x, -y)
    return (y, -x)


def draw_arrow(direction):                    # 화면에 큰 화살표 하나를 보여 주는 함수
    img = Image.new("RGB", (240, 240), (25, 0, 0))   # 240x240 빈 그림을 만든다.
    d = ImageDraw.Draw(img)                   # 그 그림 위에 그릴 수 있는 도구
    pts = []                                  # 빈 목록을 만든다
    for p in ARROW_UP:                        # ARROW_UP의 점을 하나씩 꺼낸다 (p = 점 하나)
        x, y = rotate(p, direction)           # 그 점을 방향에 맞게 돌린다
        pts.append((120 + x, 120 + y))        # 화면 가운데로 옮겨서 목록에 추가한다
    d.polygon(pts, fill=(255, 200, 0))        # 그 점들을 이어서 노란색으로 채운 도형을 그린다
    disp.image(img)                           # 완성된 그림을 LCD로 보낸다


def draw_text(text, color=(255, 255, 255), font=None):   # 화면 한가운데에 글자를 보여 주는 함수(색, 글꼴은 생략 가능)
    img = Image.new("RGB", (240, 240), (25, 0, 0))       # 어두운 빨간 배경의 빈 그림을 만든다
    d = ImageDraw.Draw(img)                              # 그릴 도구를 만든다
    if font is None:                 # 글꼴을 안 받았으면
        font = BIG                   # 큰 글꼴(BIG)을 쓴다
    d.text((120, 120), text, font=font, fill=color, anchor="mm")
    disp.image(img)                                      # 그림을 LCD로 보낸다


def draw_input(i, n, remaining):              # 입력할 때의 화면: 몇 번째 입력인지 + 남은 시간
    # 몇 번째 입력인지(i/n)와 남은 시간을 보여줘요
    img = Image.new("RGB", (240, 240), (25, 0, 0))       # 어두운 빨간 배경의 빈 그림을 만든다
    d = ImageDraw.Draw(img)                              # 그릴 붓을 만든다
    d.text((120, 90), f"{i}/{n}", font=BIG, fill=(255, 255, 255), anchor="mm")   # 위쪽에 "1/4" 같은 진행 상황을 흰색으로 쓴다
    color = (255, 200, 0) if remaining > 2 else (255, 60, 60)   # 남은 시간이 2초보다 크면 노랑, 2초 이하면 빨강
    d.text((120, 160), f"TIME {remaining}", font=MID, fill=color, anchor="mm")  # 아래쪽에 "TIME 7" 같은 남은 시간을 쓴다
    disp.image(img)                                      # 그림을 LCD로 보낸다


def make_sequence(length):   # 무작위 방향 순서를 만드는 함수 (length = 몇 개)
    i = 0                 
    return [random.choice(DIRS) for i in range(length)]  # DIRS 중 하나를 무작위로 뽑는 것을 length번 반복해서 목록으로 돌려준다


def show_sequence(seq, show_time):            # 방향 순서를 화면에 하나씩 보여 주는 함수 (show_time = 화살표 하나가 보이는 시간)
    for direction in seq:                     # 순서 목록에서 방향을 하나씩 꺼내며 반복한다
        draw_arrow(direction)                 # 그 방향의 화살표를 화면에 띄운다
        time.sleep(show_time)                 # show_time(초) 동안 그대로 둔다
        draw_text("")                         # 빈 글자를 그려서 화면을 비운다 (화살표 사이에 잠깐 비워요)
        time.sleep(0.2)                       # 0.2초 동안 비워 둔다. 같은 방향이 연속되어도 구분된다


def read_dir():                               
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


def wait_release():                           # 조이스틱에서 손을 뗄 때까지 기다리는 함수
    while read_dir() is not None:             
        time.sleep(0.02)                      


ARROW_COUNT = 4                               # 1레벨의 화살표 개수
SHOW_TIME = 0.8                               # 화살표 하나가 보이는 시간
INPUT_TIME = ARROW_COUNT                      # 입력 제한 시간


def get_input(i, n, deadline):                # 방향 하나를 입력받는 함수. deadline = 입력 마감 시각
    wait_release()                            # 먼저 손을 뗄 때까지 기다린다
    shown = None                              # 화면에 마지막으로 보여 준 "남은 초"를 기억하는 변수
    while True:                               
        left = deadline - time.monotonic()    # 남은 시간 = 마감 시각 - 지금 시각
        if left <= 0:                         
            return None                       
        sec = int(left) + 1                   # 남은 시간을 초 단위 정수로 올림한다 (예: 3.2초 남음 -> 4)
        if sec != shown:                      # 화면과 실제의 남은 시간이 다르면 화면을 새로 보여준다
            draw_input(i, n, sec)             
            shown = sec                       
        d = read_dir()                        # 지금 눌린 방향을 읽는다
        if d in DIRS:                         # 위/아래/왼쪽/오른쪽 중 하나가 눌렸으면 그 방향을 반환한다
            return d                          
        time.sleep(0.02)                      


# 메인: 게임 전체 흐름
while True:                                   
    draw_text("READY")                        
    while CENTER.value:                       
        time.sleep(0.02)                      
    wait_release()                            
    seq = make_sequence(ARROW_COUNT)          # 무작위 방향 ARROW_COUNT개의 순서를 만든다
    print("순서:", seq)                       # 터미널에도 정답을 출력한다
    show_sequence(seq, SHOW_TIME)             # 화면에 화살표를 하나씩 SHOW_TIME(0.8)초씩 보여 준다

    deadline = time.monotonic() + INPUT_TIME  # 마감 시각 = 지금 + INPUT_TIME
    result = "SAFE"                           
    for i, answer in enumerate(seq):          # 정답 순서를 하나씩 꺼낸다.
        pressed = get_input(i + 1, len(seq), deadline)   # 입력을 기다린다. i+1은 화면에 보일 번호, len(seq)는 전체 개수(4)
        if pressed is None:                   
            result = "TIMEOUT"                
            break                             
        print("입력:", pressed, "정답:", answer)   
        if pressed != answer:                 
            result = "WRONG"                  
            break                             

    if result == "SAFE":                      
        draw_text("SAFE!", (0, 255, 120))     # 초록색으로 "SAFE!"를 보여 준다   
    else:                                     
        draw_text("BOOM!", (255, 60, 60))     
    time.sleep(2)                             # 결과를 2초 동안 보여 준 뒤, 맨 위 while로 돌아가 다시 READY부터 시작
