import subprocess, math, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

SRC = sys.argv[1]
OUT = sys.argv[2]
EMO = 'emo/f/package/assets/'
W, H, FPS = 1080, 1440, 30
DUR = 11.54
ORANGE = (217, 119, 87)
F_BLACK = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
F_XB = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
F_MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
F_SYM = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
font = lambda p, s: ImageFont.truetype(p, s)

def ease_out_back(t):
    t = max(0, min(1, t)); c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def ease(t):
    t = max(0, min(1, t)); return t * t * (3 - 2 * t)

# Scenes: (start, end, emoji, label, gradient colors)
SCENES = [
    (1.00, 1.55, '1f3ac', 'CIAK, SI GIRA!', ((40, 40, 60), (90, 60, 140))),
    (1.55, 2.30, '1f4f9', 'QUESTO VIDEO', ((20, 70, 120), (60, 140, 200))),
    (2.30, 3.60, '1f9ea', 'DI PROVA', ((20, 110, 90), (90, 200, 140))),
    (3.60, 8.10, '23f3', 'PER...', ((120, 80, 20), (220, 160, 60))),
    (8.10, 9.45, 'TERMINAL', 'CLAUDE CODE', ((30, 22, 18), (120, 55, 35))),
    (9.45, DUR + 1, '1f440', 'ECCO, VEDIAMO!', ((110, 30, 80), (230, 90, 120))),
]
WORDS = [  # phrase -> words with (start, end)
    [('Sto', .57, .80), ('realizzando', .80, 1.5), ('questo', 1.5, 1.9), ('video', 1.9, 2.3)],
    [('di', 2.3, 2.5), ('prova', 2.5, 3.42), ('per…', 3.67, 4.64)],
    [('Claude', 8.14, 8.65), ('Code,', 8.65, 9.15)],
    [('ecco,', 9.49, 9.75), ('vediamo!', 9.76, 10.49)],
]
PHRASE_END = [2.3, 5.4, 9.45, DUR + 1]

emoji_cache = {}
def emoji(code, size):
    k = (code, size)
    if k not in emoji_cache:
        emoji_cache[k] = Image.open(EMO + code + '.webp').convert('RGBA').resize((size, size), Image.LANCZOS)
    return emoji_cache[k]

def gradient(w, h, c1, c2):
    g = Image.new('RGB', (1, h))
    for y in range(h):
        t = y / (h - 1)
        g.putpixel((0, y), tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return g.resize((w, h))

CW, CH = 800, 700
card_bg = {}
def card(scene, t_local):
    s0, s1, code, label, cols = scene
    if s0 not in card_bg:
        bg = gradient(CW, CH, *cols).convert('RGBA')
        m = Image.new('L', (CW, CH), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, CW - 1, CH - 1), 56, fill=255)
        bg.putalpha(m)
        d = ImageDraw.Draw(bg)
        d.rounded_rectangle((0, 0, CW - 1, CH - 1), 56, outline=(255, 255, 255, 90), width=4)
        card_bg[s0] = bg
    im = card_bg[s0].copy()
    d = ImageDraw.Draw(im)
    if code == 'TERMINAL':
        draw_terminal(im, t_local)
    else:
        bob = math.sin(t_local * 5) * 12
        e = emoji(code, 470)
        if code == '23f3':
            e = e.rotate(math.sin(t_local * 3) * 12, Image.BICUBIC)
        im.alpha_composite(e, ((CW - 470) // 2, int(50 + bob)))
    f = font(F_BLACK, 76)
    lab = label
    if code == '23f3':
        lab = 'PER' + '.' * (1 + int(t_local * 2.5) % 3)
    tw = d.textlength(label if code == '23f3' else lab, font=f)
    d.text(((CW - tw) / 2, CH - 140), lab, font=f, fill='white', stroke_width=5, stroke_fill=(0, 0, 0, 160))
    return im

def draw_terminal(im, t):
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 70, 60, CW - 70, 520
    d.rounded_rectangle((x0, y0, x1, y1), 28, fill=(18, 18, 20, 255), outline=(255, 255, 255, 60), width=3)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((x0 + 28 + i * 40, y0 + 24, x0 + 52 + i * 40, y0 + 48), fill=c)
    # star burst
    cx, cy, r = x0 + 110, y0 + 170, 58
    ang = t * 1.5
    for k in range(8):
        a = ang + k * math.pi / 4
        d.line((cx, cy, cx + r * math.cos(a), cy + r * math.sin(a)), fill=ORANGE, width=16)
    d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=ORANGE)
    d.text((x0 + 200, y0 + 118), 'Claude Code', font=font(F_BLACK, 74), fill=ORANGE)
    cmd = '> claude'
    n = min(len(cmd), int(t * 14))
    mono = font(F_MONO, 52)
    txt = cmd[:n] + ('█' if int(t * 4) % 2 == 0 else ' ')
    d.text((x0 + 40, y0 + 300), txt, font=mono, fill=(230, 230, 230))

def text_center(d, y, s, f, fill, stroke=0, sfill='black'):
    tw = d.textlength(s, font=f)
    d.text(((W - tw) / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)

def draw_title(frame, t):
    """Big intro title 0-1.0s, then fly to header."""
    T_HOLD, T_MOVE = 0.85, 0.45
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    if t < T_HOLD + T_MOVE:
        fade = 1 - ease((t - T_HOLD) / T_MOVE)
        d.rectangle((0, 0, W, H), fill=(12, 10, 9, int(235 * fade)))
    p = ease((t - T_HOLD) / T_MOVE)
    pop = ease_out_back(t / 0.45) if t < 0.45 else 1
    size_big, size_small = 210, 92
    size = (size_big + (size_small - size_big) * p) * (0.6 + 0.4 * pop)
    f = font(F_BLACK, max(10, int(size)))
    # big: two lines centred; small: one line at top
    y_big, y_small = H / 2 - size_big * 1.15, 60
    if p < 0.5:
        lines = [('CLAUDE', (255, 255, 255)), ('CODE', ORANGE)]
        lh = size * 1.08
        y = y_big + (y_small - y_big) * p * 2 * 0.5
        a = int(255 * (1 - p * 2))
        for i, (s, c) in enumerate(lines):
            text_center(d, y + i * lh, s, f, c + (a,), int(size / 20), (0, 0, 0, a))
        if p == 0:
            fs = font(F_XB, 46)
            text_center(d, y + 2 * lh + 30, 'video di prova', fs, (255, 255, 255, int(220 * pop)))
    if p > 0.5:
        a = int(255 * (p - 0.5) * 2)
        fs = font(F_BLACK, size_small)
        part1, part2 = 'CLAUDE ', 'CODE'
        w1, w2 = d.textlength(part1, font=fs), d.textlength(part2, font=fs)
        x = (W - w1 - w2) / 2
        d.rounded_rectangle((x - 36, y_small - 18, x + w1 + w2 + 36, y_small + size_small * 1.22), 30, fill=(0, 0, 0, int(a * 0.55)))
        d.text((x, y_small), part1, font=fs, fill=(255, 255, 255, a), stroke_width=4, stroke_fill=(0, 0, 0, a))
        d.text((x + w1, y_small), part2, font=fs, fill=ORANGE + (a,), stroke_width=4, stroke_fill=(0, 0, 0, a))
    frame.alpha_composite(ov)

def draw_subs(frame, t):
    idx = None
    for i, ws in enumerate(WORDS):
        if ws[0][1] - 0.15 <= t < PHRASE_END[i]:
            idx = i
    if idx is None:
        return
    ws = WORDS[idx]
    f = font(F_BLACK, 84)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    space = d.textlength(' ', font=f)
    widths = [d.textlength(w, font=f) for w, _, _ in ws]
    total = sum(widths) + space * (len(ws) - 1)
    # wrap into lines if too wide
    lines, cur, cw = [], [], 0
    for k, w in enumerate(widths):
        if cur and cw + space + w > W - 120:
            lines.append(cur); cur, cw = [], 0
        cw += (space if cur else 0) + w; cur.append(k)
    lines.append(cur)
    y = H - 140 - 110 * len(lines)
    fade_in = ease((t - (ws[0][1] - 0.15)) / 0.2)
    pad = 26
    for line in lines:
        lw = sum(widths[k] for k in line) + space * (len(line) - 1)
        x = (W - lw) / 2
        d.rounded_rectangle((x - pad, y - 14, x + lw + pad, y + 104), 24, fill=(0, 0, 0, int(150 * fade_in)))
        for k in line:
            word, s, e = ws[k]
            if t < s:
                col = (255, 255, 255, int(110 * fade_in))
            elif t < e:
                col = (255, 214, 10, 255)
            else:
                col = (255, 255, 255, 255)
            dy = -10 * math.sin(math.pi * min(1, (t - s) / 0.25)) if s <= t < s + 0.25 else 0
            d.text((x, y + dy), word, font=f, fill=col, stroke_width=6, stroke_fill=(0, 0, 0, col[3]))
            x += widths[k] + space
        y += 112
    frame.alpha_composite(ov)

def draw_card(frame, t):
    for sc in SCENES:
        s0, s1 = sc[0], sc[1]
        if s0 <= t < s1 + 0.2:
            tl = t - s0
            p_in = ease_out_back(tl / 0.35)
            p_out = 1 - ease((t - s1) / 0.2) if t > s1 else 1
            c = card(sc, tl)
            sc_ = max(0.01, p_in * (0.9 + 0.1 * p_out))
            cw, ch = int(CW * sc_), int(CH * sc_)
            c = c.resize((cw, ch), Image.BILINEAR)
            if p_out < 1:
                a = c.getchannel('A').point(lambda v: int(v * p_out)); c.putalpha(a)
            # shadow
            sh = Image.new('RGBA', (cw + 80, ch + 80), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((40, 50, cw + 40, ch + 50), 56, fill=(0, 0, 0, int(140 * p_out)))
            sh = sh.filter(ImageFilter.GaussianBlur(22))
            cx, cy = W // 2, 640
            frame.alpha_composite(sh, (cx - cw // 2 - 40, cy - ch // 2 - 40))
            frame.alpha_composite(c, (cx - cw // 2, cy - ch // 2))

dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', SRC, '-vf',
                        f'fps={FPS},scale={W}:{H}:flags=lanczos', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                        '-r', str(FPS), '-i', '-', '-i', SRC, '-map', '0:v', '-map', '1:a:0', '-c:v', 'libx264',
                        '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
                        '-shortest', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
n = 0
while True:
    raw = dec.stdout.read(W * H * 3)
    if len(raw) < W * H * 3:
        break
    t = n / FPS
    bg = Image.frombytes('RGB', (W, H), raw)
    bg = ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(3))).enhance(0.6).convert('RGBA')
    draw_card(bg, t)
    draw_subs(bg, t)
    draw_title(bg, t)
    enc.stdin.write(bg.convert('RGB').tobytes())
    n += 1
enc.stdin.close(); enc.wait()
print('frames', n)
