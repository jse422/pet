import os
import sys
import tkinter as tk
import random
import numpy as np
from scipy import ndimage
from PIL import Image, ImageTk, ImageOps

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(BASE_DIR, "cat.png")
FRAMES_DIR = os.path.join(BASE_DIR, "frames")

WIN     = 150   # 창 크기 (정사각형)
TARGET  = 110   # 스프라이트 목표 크기
SPEED   = 2
TICK_W  = 150   # 걷기 ms
TICK_I  = 250   # 대기 ms
ROW_GAP = 50    # 행 구분 최소 Y 간격
MIN_PX  = 3000  # 스프라이트 최소 픽셀 수
MIN_H   = 50    # 최소 높이 (텍스트 헤더 제거용)


def extract_frames():
    os.makedirs(FRAMES_DIR, exist_ok=True)

    img = Image.open(IMAGE_PATH).convert("RGBA")
    arr = np.array(img)
    bg  = arr[0, 0, :3]

    diff = np.abs(arr[:, :, :3].astype(int) - bg.astype(int))
    mask = np.any(diff > 15, axis=-1)
    labeled, n = ndimage.label(mask)

    comps = []
    for cid in range(1, n + 1):
        cm = labeled == cid
        rs, cs = np.where(cm)
        h = int(rs.max()) - int(rs.min())
        if len(rs) < MIN_PX or h < MIN_H:  # 텍스트/장식 제거
            continue
        y1 = max(0, int(rs.min()) - 2)
        y2 = min(arr.shape[0], int(rs.max()) + 2)
        x1 = max(0, int(cs.min()) - 2)
        x2 = min(arr.shape[1], int(cs.max()) + 2)
        comps.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                      'cy': (y1 + y2) / 2, 'cx': (x1 + x2) / 2})

    comps.sort(key=lambda c: c['cy'])

    # Y 간격으로 행 그룹화 (고정 슬라이싱 대신 자동 감지)
    groups, cur = [], [comps[0]]
    for c in comps[1:]:
        if c['cy'] - cur[-1]['cy'] > ROW_GAP:
            groups.append(sorted(cur, key=lambda c: c['cx']))
            cur = []
        cur.append(c)
    groups.append(sorted(cur, key=lambda c: c['cx']))

    def save_frame(comp, fname):
        crop = np.array(img.crop((comp['x1'], comp['y1'], comp['x2'], comp['y2'])))
        d    = np.abs(crop[:, :, :3].astype(int) - bg.astype(int))
        crop[np.all(d < 15, axis=-1)] = [255, 0, 255, 255]
        Image.fromarray(crop).save(os.path.join(FRAMES_DIR, fname))

    names = ['walk', 'idle', 'jump']
    for name, row in zip(names, groups):
        for i, comp in enumerate(row):
            save_frame(comp, f'{name}_{i}.png')

    pass


def load_state(state, count):
    """파일에서 프레임 로드 → WIN×WIN 마젠타 캔버스에 정규화 → (오른쪽, 왼쪽) 반환"""
    r_frames, l_frames = [], []
    for i in range(count):
        path = os.path.join(FRAMES_DIR, f'{state}_{i}.png')
        if not os.path.exists(path):
            continue
        img = Image.open(path).convert('RGBA')
        # 마젠타 픽셀 → 투명으로 변환
        data = [(0, 0, 0, 0) if (r > 240 and g < 20 and b > 240) else (r, g, b, a)
                for r, g, b, a in img.getdata()]
        img.putdata(data)
        # TARGET 크기로 스케일링
        w, h  = img.size
        scale = TARGET / max(w, h)
        img   = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST)
        w, h  = img.size
        # WIN×WIN 마젠타 캔버스에 붙여넣기 (하단 정렬)
        canvas = Image.new('RGB', (WIN, WIN), (255, 0, 255))
        canvas.paste(img, ((WIN - w) // 2, WIN - h - 4), mask=img.split()[3])
        r_frames.append(ImageTk.PhotoImage(canvas))
        l_frames.append(ImageTk.PhotoImage(ImageOps.mirror(canvas)))
    return r_frames, l_frames


class DesktopCat:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", "magenta")
        self.root.config(bg='magenta')

        wr, wl = load_state('walk', 5)
        ir, il = load_state('idle', 4)
        jr, jl = load_state('jump', 2)
        if not jr:
            jr, jl = wr, wl

        self.frames = {
            'walk_right': wr, 'walk_left': wl,
            'idle_right': ir, 'idle_left': il,
            'jump_right': jr, 'jump_left': jl,
        }
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.x  = self.sw // 2
        self.y  = self.sh - WIN - 55
        self.direction = "right"
        self.state     = "walk"
        self.fi        = 0

        self.label = tk.Label(self.root, bd=0, bg='magenta')
        self.label.pack()

        self.label.bind('<Button-3>', lambda e: self.root.destroy())

        self.root.geometry(f'{WIN}x{WIN}+{self.x}+{self.y}')
        self.update_animation()
        self.change_state()
        self.root.mainloop()

    def update_animation(self):
        key    = f'{self.state}_{self.direction}'
        flist  = self.frames[key]
        if flist:
            self.fi = (self.fi + 1) % len(flist)
            self.label.config(image=flist[self.fi])

            if self.state == "walk":
                self.x += SPEED if self.direction == "right" else -SPEED
                if self.x > self.sw - WIN - 5:
                    self.direction = "left"
                elif self.x < 5:
                    self.direction = "right"

            self.root.geometry(f'{WIN}x{WIN}+{self.x}+{self.y}')

        delay = TICK_I if self.state == "idle" else TICK_W
        self.root.after(delay, self.update_animation)

    def change_state(self):
        prev = self.state
        self.state = random.choice(["idle", "walk"])
        if self.state == "walk":
            self.direction = random.choice(["left", "right"])
        if self.state != prev:
            self.fi = 0
        self.root.after(random.randint(3000, 6000), self.change_state)


if __name__ == '__main__':
    if not os.path.exists(FRAMES_DIR) or not os.listdir(FRAMES_DIR):
        if not os.path.exists(IMAGE_PATH):
            sys.exit(1)
        extract_frames()

    DesktopCat()
