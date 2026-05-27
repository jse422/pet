import tkinter as tk
from PIL import Image, ImageOps, ImageTk
import random

SPRITE_PATH = r'C:\Users\jsepr\OneDrive\Desktop\강아지\dog\ChatGPT Image 2026년 5월 27일 오후 11_51_22.png'

BG_RGB = (1, 1, 1)
BG_HEX = '#010101'
WIN   = 130      # 창 크기 (정사각형)
SPEED = 2
TICK  = 80       # ms

# 스프라이트 좌표 (분석 결과)
WALK_COORDS = [
    (160, 148, 306, 275),
    (318, 148, 467, 275),
    (483, 148, 642, 275),
    (658, 148, 803, 275),
]
IDLE_COORDS = [
    (189, 437, 356, 593),
    (394, 437, 558, 593),
    (598, 437, 758, 593),
]
JUMP_COORDS = [
    (293, 732, 476, 897),
    (536, 732, 717, 897),
]

TARGET = 100  # 목표 스프라이트 크기


def crop_sprite(sheet, x1, y1, x2, y2):
    """잘라내기 + 리사이즈 (PNG alpha 채널 그대로 사용)"""
    frame = sheet.crop((x1, y1, x2, y2)).convert('RGBA')
    w, h = frame.size
    scale = TARGET / max(w, h)
    return frame.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST)


def to_tk(pil_img, flip=False):
    """RGBA 이미지 → tkinter PhotoImage (BG_RGB 배경으로 합성)"""
    if flip:
        pil_img = ImageOps.mirror(pil_img)
    canvas = Image.new('RGB', (WIN, WIN), BG_RGB)
    sw, sh = pil_img.size
    ox = (WIN - sw) // 2
    oy = WIN - sh - 4
    canvas.paste(pil_img, (ox, oy), mask=pil_img.split()[3])
    return ImageTk.PhotoImage(canvas)


class DogPet:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes('-topmost', True)
        self.root.wm_attributes('-transparentcolor', BG_HEX)

        print("스프라이트 로딩 중...")
        sheet = Image.open(SPRITE_PATH)
        raw = {
            'walk': [crop_sprite(sheet, *c) for c in WALK_COORDS],
            'idle': [crop_sprite(sheet, *c) for c in IDLE_COORDS],
            'jump': [crop_sprite(sheet, *c) for c in JUMP_COORDS],
        }
        self.frames = {}
        for state, imgs in raw.items():
            self.frames[f'{state}_r'] = [to_tk(f)             for f in imgs]
            self.frames[f'{state}_l'] = [to_tk(f, flip=True)  for f in imgs]
        print("완료!")

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()

        self.x = random.randint(100, max(100, self.sw - WIN - 100))
        self.y = self.sh - WIN - 55
        self.vx = SPEED
        self.facing = 'r'
        self.state = 'walk'
        self.fi = 0          # frame index
        self.ftimer = 0      # frame 진행 타이머
        self.stimer = 0      # state 유지 타이머

        self._dragging = False
        self._drag_ox = 0
        self._drag_oy = 0
        self._saved_vx = SPEED

        self.root.geometry(f'{WIN}x{WIN}+{self.x}+{self.y}')
        self.root.config(bg=BG_HEX)

        self.label = tk.Label(self.root, bg=BG_HEX, bd=0)
        self.label.pack()

        self.label.bind('<ButtonPress-1>',   self._press)
        self.label.bind('<B1-Motion>',       self._drag)
        self.label.bind('<ButtonRelease-1>', self._release)
        self.label.bind('<Button-3>',        lambda e: self.root.destroy())

        self.tick()
        self.root.mainloop()

    # ── 드래그 ─────────────────────────────────────────
    def _press(self, e):
        self._dragging = True
        self._drag_ox = e.x
        self._drag_oy = e.y
        self._saved_vx = self.vx
        self.vx = 0
        # 클릭하면 점프!
        if self.state == 'walk':
            self.state = 'jump'
            self.fi = 0
            self.stimer = len(JUMP_COORDS) * 3

    def _drag(self, e):
        if self._dragging:
            self.x += e.x - self._drag_ox
            self.y += e.y - self._drag_oy
            self._drag_ox = e.x
            self._drag_oy = e.y
            self.root.geometry(f'{WIN}x{WIN}+{self.x}+{self.y}')

    def _release(self, e):
        self._dragging = False
        self.vx = (
            self._saved_vx if self._saved_vx != 0
            else SPEED * (1 if self.facing == 'r' else -1)
        )

    # ── 메인 루프 ───────────────────────────────────────
    def tick(self):
        self.ftimer += 1
        if self.stimer > 0:
            self.stimer -= 1

        # 상태 전환
        if self.state == 'walk':
            if self.stimer == 0 and random.random() < 0.005:
                self.state = 'idle'
                self.fi = 0
                self.stimer = 55       # ~4.4초 앉아있기
                self.vx = 0
        elif self.state == 'idle' and self.stimer == 0:
            self.state = 'walk'
            self.fi = 0
            self.vx = SPEED * (1 if self.facing == 'r' else -1)
        elif self.state == 'jump' and self.stimer == 0:
            self.state = 'walk'
            self.fi = 0

        # 이동
        if not self._dragging:
            self.x += self.vx
            if self.x >= self.sw - WIN - 5:
                self.vx = -SPEED
                self.facing = 'l'
                self.fi = 0
            elif self.x <= 5:
                self.vx = SPEED
                self.facing = 'r'
                self.fi = 0
            self.root.geometry(f'{WIN}x{WIN}+{self.x}+{self.y}')

        # 프레임 속도 (상태별)
        speed = {'walk': 2, 'idle': 4, 'jump': 2}[self.state]
        key = f'{self.state}_{self.facing}'
        flist = self.frames[key]
        if self.ftimer % speed == 0:
            self.fi = (self.fi + 1) % len(flist)

        self.label.config(image=flist[self.fi])
        self.root.after(TICK, self.tick)


if __name__ == '__main__':
    DogPet()
