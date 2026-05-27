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

WIN     = 150
TARGET  = 110
SPEED   = 2
TICK_W  = 150
TICK_I  = 250
ROW_GAP = 50
MIN_PX  = 3000
MIN_H   = 50


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
        if len(rs) < MIN_PX or h < MIN_H:
            continue
        y1 = max(0, int(rs.min()) - 2)
        y2 = min(arr.shape[0], int(rs.max()) + 2)
        x1 = max(0, int(cs.min()) - 2)
        x2 = min(arr.shape[1], int(cs.max()) + 2)
        comps.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                      'cy': (y1 + y2) / 2, 'cx': (x1 + x2) / 2})

    if not comps:
        return

    comps.sort(key=lambda c: c['cy'])

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

    for name, row in zip(['walk', 'idle', 'jump'], groups):
        for i, comp in enumerate(row):
            save_frame(comp, f'{name}_{i}.png')


def load_state(state, count):
    r_frames, l_frames = [], []
    for i in range(count):
        path = os.path.join(FRAMES_DIR, f'{state}_{i}.png')
        if not os.path.exists(path):
            continue
        img = Image.open(path).convert('RGBA')
        data = [(0, 0, 0, 0) if (r > 240 and g < 20 and b > 240) else (r, g, b, a)
                for r, g, b, a in img.getdata()]
        img.putdata(data)
        w, h  = img.size
        scale = TARGET / max(w, h)
        img   = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST)
        w, h  = img.size
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
        self.stimer    = 0

        self._dragging = False
        self._moved    = False
        self._drag_ox  = 0
        self._drag_oy  = 0

        self.label = tk.Label(self.root, bd=0, bg='magenta')
        self.label.pack()

        self.label.bind('<ButtonPress-1>',   self._press)
        self.label.bind('<B1-Motion>',       self._drag)
        self.label.bind('<ButtonRelease-1>', self._release)
        self.label.bind('<Button-3>',        lambda e: self.root.destroy())

        self.root.geometry(f'{WIN}x{WIN}+{self.x}+{self.y}')
        self.update_animation()
        self.change_state()
        self.root.mainloop()

    # ── 드래그 / 클릭 ──────────────────────────────────────
    def _press(self, e):
        self._dragging = True
        self._moved    = False
        self._drag_ox  = e.x
        self._drag_oy  = e.y
        if self.state != 'jump':
            self.state  = 'jump'
            self.fi     = 0
            self.stimer = len(self.frames['jump_right']) * 4

    def _drag(self, e):
        if self._dragging:
            self._moved    = True
            self.x        += e.x - self._drag_ox
            self.y        += e.y - self._drag_oy
            self._drag_ox  = e.x
            self._drag_oy  = e.y
            self.root.geometry(f'{WIN}x{WIN}+{self.x}+{self.y}')

    def _release(self, e):
        self._dragging = False
        if self._moved:     # 실제 드래그였으면 즉시 walk로 복귀
            self.state  = 'walk'
            self.fi     = 0
            self.stimer = 0
        # 클릭이었으면 stimer가 끝날 때까지 점프 유지

    # ── 메인 루프 ──────────────────────────────────────────
    def update_animation(self):
        # 점프 타이머
        if self.stimer > 0:
            self.stimer -= 1
            if self.stimer == 0 and self.state == 'jump':
                self.state = 'walk'
                self.fi    = 0

        # 이동
        if not self._dragging and self.state == 'walk':
            self.x += SPEED if self.direction == 'right' else -SPEED
            if self.x > self.sw - WIN - 5:
                self.direction = 'left'
            elif self.x < 5:
                self.direction = 'right'
            self.root.geometry(f'{WIN}x{WIN}+{self.x}+{self.y}')

        # 프레임 갱신
        key   = f'{self.state}_{self.direction}'
        flist = self.frames[key]
        if flist:
            self.fi = (self.fi + 1) % len(flist)
            self.label.config(image=flist[self.fi])

        delay = TICK_I if self.state == 'idle' else TICK_W
        self.root.after(delay, self.update_animation)

    def change_state(self):
        if not self._dragging and self.state != 'jump':
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
