# =====================================================================
# TICK TOCK - 1주차 게임 뼈대 (줄마다 설명을 붙인 버전)
# 게임 흐름: 시작 대기 -> 방향 화살표 4개 보여주기 -> 같은 순서로 입력 -> 성공/실패
# 제안서의 1레벨 규칙: 화살표 4개, 화살표 표시 0.8초, 입력 제한 시간 = 화살표 개수(4초)
# =====================================================================

# ---------- 필요한 도구(라이브러리) 가져오기 ----------
import time                                   # 시간 관련 기능(기다리기, 시간 재기)
import random                                 # 무작위(랜덤) 기능
import board                                  # 라즈베리파이의 핀 이름(D25, D17 등)을 쓰기 위한 도구
import digitalio                              # 핀을 켜고 끄거나(출력), 값을 읽는(입력) 도구
from PIL import Image, ImageDraw, ImageFont   # 그림 만들기(Image), 그림 위에 그리기(ImageDraw), 글꼴(ImageFont)
from adafruit_rgb_display import st7789       # 우리 LCD(ST7789 칩)를 제어하는 도구

# ---------- LCD 설정 (Pi 5용: cs=None) ----------
spi = board.SPI()                             # SPI 통신 길(파이와 LCD가 그림 데이터를 주고받는 통로)을 연다
dc = digitalio.DigitalInOut(board.D25)        # 25번 핀 준비. LCD에게 "명령이다/데이터다"를 알려주는 핀(DC)
disp = st7789.ST7789(spi,                     # LCD 객체를 만든다. 앞으로 disp.image(그림)으로 화면에 그림을 보낸다
                     width=240, height=240,   # 화면 크기: 가로 240, 세로 240 픽셀
                     y_offset=80,             # 이 모듈의 화면이 위아래로 어긋나지 않게 맞추는 값
                     rotation=180,            # 화면을 180도 돌려서 올바른 방향으로 보이게 한다
                     cs=None,                 # Pi 5에서 오류(Errno 16)를 피하기 위해 칩 선택(CS) 핀을 따로 쓰지 않는다
                     dc=dc,                   # 위에서 준비한 DC 핀을 알려준다
                     rst=None,                # 리셋(RST) 핀은 쓰지 않는다
                     baudrate=24000000)       # SPI 통신 속도: 초당 2400만 비트
backlight = digitalio.DigitalInOut(board.D26) # 26번 핀 준비. LCD 뒤쪽 불빛(백라이트) 핀이다
backlight.switch_to_output(value=True)        # 출력 모드로 바꾸고 켠다(True). 이걸 해야 화면이 밝게 보인다

# ---------- 조이스틱 ----------
def make_button(pin):                         # 핀 하나를 "버튼 입력"으로 만들어 주는 함수를 정의한다
    b = digitalio.DigitalInOut(pin)           # 받은 핀 번호를 준비한다
    b.switch_to_input(pull=digitalio.Pull.UP) # 입력 모드로 바꾼다. 풀업: 안 누르면 True, 누르면 False가 된다
    return b                                  # 만든 버튼을 돌려준다

UP = make_button(board.D17)                   # 조이스틱 위쪽 = 17번 핀
DOWN = make_button(board.D22)                 # 조이스틱 아래쪽 = 22번 핀
LEFT = make_button(board.D27)                 # 조이스틱 왼쪽 = 27번 핀
RIGHT = make_button(board.D23)                # 조이스틱 오른쪽 = 23번 핀
CENTER = make_button(board.D4)                # 조이스틱 가운데(누르기) = 4번 핀

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
            (18, -10),                        # 화살촉과 몸통이 만나는 오른쪽 안쪽 점
            (18, 60),                         # 몸통의 오른쪽 아래 점
            (-18, 60),                        # 몸통의 왼쪽 아래 점
            (-18, -10),                       # 화살촉과 몸통이 만나는 왼쪽 안쪽 점
            (-50, -10)]                       # 화살촉의 왼쪽 아래 끝


def rotate(point, direction):                 # 위쪽 기준 좌표를 원하는 방향으로 돌려 주는 함수
    x, y = point                              # 점의 좌표를 x, y로 꺼낸다
    if direction == "UP":                     # 위쪽이면
        return (x, y)                         # 그대로 쓴다
    if direction == "RIGHT":                  # 오른쪽이면 (시계 방향으로 90도)
        return (-y, x)                        # 좌표를 이렇게 바꾸면 오른쪽을 향한다
    if direction == "DOWN":                   # 아래쪽이면 (180도)
        return (-x, -y)                       # x, y의 부호를 모두 뒤집는다
    return (y, -x)  # LEFT                    # 위 세 경우가 아니면 왼쪽이다 (반시계 방향으로 90도)


def draw_arrow(direction):                    # 화면에 큰 화살표 하나를 보여 주는 함수
    img = Image.new("RGB", (240, 240), (25, 0, 0))   # 240x240 빈 그림을 만든다. 색은 아주 어두운 빨강(R,G,B)
    d = ImageDraw.Draw(img)                   # 그 그림 위에 그릴 수 있는 붓을 만든다
    pts = [(120 + rotate(p, direction)[0],    # 돌린 꼭짓점의 x 좌표에 120을 더해 화면 한가운데로 옮긴다
            120 + rotate(p, direction)[1])    # y 좌표도 마찬가지로 120을 더한다
           for p in ARROW_UP]                 # 화살표의 꼭짓점 7개 전부에 대해 반복해서 새 좌표 목록을 만든다
    d.polygon(pts, fill=(255, 200, 0))        # 그 점들을 이어서 노란색(255,200,0)으로 채운 도형을 그린다
    disp.image(img)                           # 완성된 그림을 LCD로 보낸다


def draw_text(text, color=(255, 255, 255), font=None):   # 화면 한가운데에 글자를 보여 주는 함수(색, 글꼴은 생략 가능)
    img = Image.new("RGB", (240, 240), (25, 0, 0))       # 어두운 빨간 배경의 빈 그림을 만든다
    d = ImageDraw.Draw(img)                              # 그릴 붓을 만든다
    d.text((120, 120), text, font=font or BIG, fill=color, anchor="mm")   # (120,120)=화면 중앙에 글자를 쓴다. 글꼴을 안 주면 BIG. anchor="mm"은 글자의 정중앙을 그 좌표에 맞춘다
    disp.image(img)                                      # 그림을 LCD로 보낸다


def draw_input(i, n, remaining):              # 입력할 때의 화면: 몇 번째 입력인지 + 남은 시간
    # 몇 번째 입력인지(i/n)와 남은 시간을 보여줘요
    img = Image.new("RGB", (240, 240), (25, 0, 0))       # 어두운 빨간 배경의 빈 그림을 만든다
    d = ImageDraw.Draw(img)                              # 그릴 붓을 만든다
    d.text((120, 90), f"{i}/{n}", font=BIG, fill=(255, 255, 255), anchor="mm")   # 위쪽에 "1/4" 같은 진행 상황을 흰색으로 쓴다
    color = (255, 200, 0) if remaining > 2 else (255, 60, 60)   # 남은 시간이 2초보다 크면 노랑, 2초 이하면 빨강
    d.text((120, 160), f"TIME {remaining}", font=MID, fill=color, anchor="mm")  # 아래쪽에 "TIME 7" 같은 남은 시간을 쓴다
    disp.image(img)                                      # 그림을 LCD로 보낸다


def make_sequence(length):                    # 무작위 방향 순서를 만드는 함수 (length = 몇 개)
    return [random.choice(DIRS) for _ in range(length)]  # DIRS 중 하나를 무작위로 뽑는 것을 length번 반복해서 목록으로 돌려준다


def show_sequence(seq, show_time):            # 방향 순서를 화면에 하나씩 보여 주는 함수 (show_time = 화살표 하나가 보이는 시간)
    for direction in seq:                     # 순서 목록에서 방향을 하나씩 꺼내며 반복한다
        draw_arrow(direction)                 # 그 방향의 화살표를 화면에 띄운다
        time.sleep(show_time)                 # show_time(초) 동안 그대로 둔다
        draw_text("")                         # 빈 글자를 그려서 화면을 비운다 (화살표 사이에 잠깐 비워요)
        time.sleep(0.2)                       # 0.2초 동안 비워 둔다. 같은 방향이 연속되어도 구분된다


def read_dir():                               # 지금 눌려 있는 방향을 알려 주는 함수
    # 눌린 방향 이름을 돌려주고, 아무것도 안 눌렸으면 None
    if not UP.value:                          # 위쪽 값이 False(=눌림)이면
        return "UP"                           # "UP"을 돌려주고 함수를 끝낸다
    if not DOWN.value:                        # 아래쪽이 눌렸으면
        return "DOWN"                         # "DOWN"을 돌려준다
    if not LEFT.value:                        # 왼쪽이 눌렸으면
        return "LEFT"                         # "LEFT"를 돌려준다
    if not RIGHT.value:                       # 오른쪽이 눌렸으면
        return "RIGHT"                        # "RIGHT"를 돌려준다
    if not CENTER.value:                      # 가운데가 눌렸으면
        return "CENTER"                       # "CENTER"를 돌려준다
    return None                               # 아무것도 안 눌렸으면 None(= 없음)을 돌려준다


def wait_release():                           # 조이스틱에서 손을 뗄 때까지 기다리는 함수
    while read_dir() is not None:             # 무언가 눌려 있는 동안(None이 아닌 동안) 계속 반복한다
        time.sleep(0.02)                      # 0.02초씩 쉬면서 기다린다 (손을 뗄 때까지 기다려요)


ARROW_COUNT = 4                               # 1레벨의 화살표 개수 (제안서: 4개)
SHOW_TIME = 0.8                               # 화살표 하나가 보이는 시간(초) (제안서: 0.8초)
INPUT_TIME = ARROW_COUNT                      # 입력 제한 시간(초) = 화살표 개수 (제안서: 개수와 같은 초 -> 4초)


def get_input(i, n, deadline):                # 방향 하나를 입력받는 함수. deadline = 입력 마감 시각
    # 방향 하나가 눌릴 때까지 기다려요. 시간이 끝나면 None을 돌려줘요.
    wait_release()                            # 먼저 손을 뗄 때까지 기다린다 (한 번 누른 게 여러 번 입력되는 것을 막는다)
    shown = None                              # 화면에 마지막으로 보여 준 "남은 초"를 기억하는 변수(처음엔 없음)
    while True:                               # 입력이 들어오거나 시간이 끝날 때까지 무한 반복한다
        left = deadline - time.monotonic()    # 남은 시간 = 마감 시각 - 지금 시각
        if left <= 0:                         # 남은 시간이 0 이하면
            return None                       # 시간 초과: None을 돌려주고 끝낸다
        sec = int(left) + 1                   # 남은 시간을 초 단위 정수로 올림한다 (예: 3.2초 남음 -> 4)
        if sec != shown:                      # 마지막으로 보여 준 숫자와 다를 때만 (초가 바뀔 때만 화면을 다시 그려요)
            draw_input(i, n, sec)             # 입력 화면을 새로 그린다
            shown = sec                       # 방금 보여 준 숫자를 기억해 둔다
        d = read_dir()                        # 지금 눌린 방향을 읽는다
        if d in DIRS:                         # 위/아래/왼쪽/오른쪽 중 하나가 눌렸으면 (가운데나 None은 무시)
            return d                          # 그 방향을 돌려주고 끝낸다
        time.sleep(0.02)                      # 0.02초 쉰다 (컴퓨터가 너무 바쁘게 돌지 않게)


# ======================= 메인: 게임 전체 흐름 =======================
while True:                                   # 게임이 끝나도 다시 시작하도록 무한 반복한다
    draw_text("READY")                        # 화면에 "READY"를 보여 준다
    while CENTER.value:                       # 가운데 버튼이 안 눌려 있는 동안(값이 True인 동안) 반복한다
        time.sleep(0.02)                      # 0.02초씩 쉬면서 가운데를 누르기를 기다린다
    wait_release()                            # 가운데에서 손을 뗄 때까지 기다린다
    seq = make_sequence(ARROW_COUNT)          # 무작위 방향 ARROW_COUNT(4)개의 순서를 만든다 (정답)
    print("순서:", seq)                       # 터미널에도 정답을 출력한다 (확인용)
    show_sequence(seq, SHOW_TIME)             # 화면에 화살표를 하나씩 SHOW_TIME(0.8)초씩 보여 준다

    deadline = time.monotonic() + INPUT_TIME  # 마감 시각 = 지금 + INPUT_TIME(4초)
    result = "SAFE"                           # 결과를 일단 "성공"으로 두고 시작한다. 틀리면 아래에서 바꾼다
    for i, answer in enumerate(seq):          # 정답 순서를 하나씩 꺼낸다. i는 0,1,2,3 번호, answer는 그 번째 정답 방향
        pressed = get_input(i + 1, len(seq), deadline)   # 입력을 기다린다. i+1은 화면에 보일 번호, len(seq)는 전체 개수(4)
        if pressed is None:                   # None이면 시간이 끝난 것이다
            result = "TIMEOUT"                # 결과를 "시간 초과"로 바꾸고
            break                             # 반복을 멈춘다
        print("입력:", pressed, "정답:", answer)   # 내가 누른 방향과 정답을 터미널에 출력한다 (확인용)
        if pressed != answer:                 # 누른 방향이 정답과 다르면
            result = "WRONG"                  # 결과를 "틀림"으로 바꾸고
            break                             # 반복을 멈춘다 (한 번이라도 틀리면 바로 실패)

    if result == "SAFE":                      # 끝까지 다 맞혔다면
        draw_text("SAFE!", (0, 255, 120))     # 초록색으로 "SAFE!"를 보여 준다 (폭탄 해체 성공)
    elif result == "TIMEOUT":                 # 시간이 끝났다면
        draw_text("TIME UP", (255, 60, 60), MID)   # 빨간색으로 "TIME UP"을 보여 주고
        time.sleep(1)                         # 1초 기다린 뒤
        draw_text("BOOM!", (255, 60, 60))     # "BOOM!"을 보여 준다
    else:                                     # 그 외(= 틀렸다면)
        draw_text("BOOM!", (255, 60, 60))     # 빨간색 "BOOM!"을 바로 보여 준다
    time.sleep(2)                             # 결과를 2초 동안 보여 준 뒤, 맨 위 while로 돌아가 다시 READY부터 시작한다