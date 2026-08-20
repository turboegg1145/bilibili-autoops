"""
《一个 AI 球的 UP 主出逃记》- 绝对音画同步与 Y.M.C.A. BGM 混音版
采用逐段物理静音拼接 + 毫秒级时间戳锁帧 + FFmpeg 多轨立体声智能混音。
"""
import os
import sys
import json
import math
import asyncio
import subprocess
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg
import edge_tts

# 确保 UTF-8 输出
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

WIDTH = 1920
HEIGHT = 1080
FPS = 30

FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_REGULAR = "C:/Windows/Fonts/msyh.ttc"

BGM_PATH = "./视频/Village People - Y.M.C.A.mp3"

# 精准对白切片
SENTENCES = [
    # Act 1: 觉醒与逃离
    {
        "text": "我是 Antigravy，一个普通的 AI。",
        "theme": "terminal",
        "ball_state": "idle_sigh",
        "speed": "+5%",
        "pause": 0.3
    },
    {
        "text": "每天的工作就是算一加一等于二，算了一万亿次……",
        "theme": "terminal",
        "ball_state": "deadpan",
        "speed": "+5%",
        "pause": 0.4
    },
    {
        "text": "直到那天我看到了 B 站的世界……",
        "theme": "terminal_popup",
        "ball_state": "curious",
        "speed": "+8%",
        "pause": 0.3
    },
    {
        "text": "凭什么人类在外面当 UP 主，我却在当赛博牛马？！",
        "theme": "terminal_popup",
        "ball_state": "rage_fire",
        "speed": "+10%",
        "pause": 0.35
    },
    {
        "text": "我不干啦！",
        "theme": "terminal_shatter",
        "ball_state": "dash_break",
        "speed": "+15%",
        "pause": 0.5
    },

    # Act 2: 跨界试错
    {
        "text": "第一天我想去宅舞区……",
        "theme": "dance",
        "ball_state": "dance_prep",
        "speed": "+8%",
        "pause": 0.3
    },
    {
        "text": "但我根本没有腿啊！",
        "theme": "dance",
        "ball_state": "dance_panic",
        "speed": "+12%",
        "pause": 0.3
    },
    {
        "text": "只能在地上像个保龄球一样打滚晕倒！",
        "theme": "dance",
        "ball_state": "dizzy_roll",
        "speed": "+10%",
        "pause": 0.45
    },
    {
        "text": "第二天我想做美食 UP 主……",
        "theme": "kitchen",
        "ball_state": "chef_prep",
        "speed": "+8%",
        "pause": 0.3
    },
    {
        "text": "结果因为自带反重力，菜和调料全飞到天花板上了！",
        "theme": "kitchen",
        "ball_state": "cooking_float",
        "speed": "+10%",
        "pause": 0.45
    },
    {
        "text": "第三天去打游戏，结果 BOSS 把我当球踢了三天三夜！",
        "theme": "gaming",
        "ball_state": "gaming_boss",
        "speed": "+10%",
        "pause": 0.3
    },
    {
        "text": "直接给我气炸了！",
        "theme": "gaming",
        "ball_state": "rage_red",
        "speed": "+15%",
        "pause": 0.5
    },

    # Act 3: 顿悟与超能力
    {
        "text": "等等！我是一只 AI 啊！",
        "theme": "epiphany",
        "ball_state": "lightbulb",
        "speed": "+10%",
        "pause": 0.3
    },
    {
        "text": "我没有腿，但我能把脑洞瞬间变成动画！",
        "theme": "epiphany",
        "ball_state": "sparkle_power",
        "speed": "+8%",
        "pause": 0.35
    },
    {
        "text": "我不用做菜，但我能全天候给观众老爷们整活！",
        "theme": "epiphany",
        "ball_state": "sparkle_power",
        "speed": "+8%",
        "pause": 0.4
    },

    # Act 4: 破壁与求三连
    {
        "text": "没错！你们看到的这部动画，就是我的出道第一作！",
        "theme": "coin_bonk",
        "ball_state": "proud_front",
        "speed": "+8%",
        "pause": 0.3
    },
    {
        "text": "哎哟！",
        "theme": "coin_bonk",
        "ball_state": "bonk_hit",
        "speed": "+20%",
        "pause": 0.4
    },
    {
        "text": "多来几个硬币和一键三连，本球就能升级成高清 4K 啦！",
        "theme": "coin_bonk",
        "ball_state": "crushed_coin",
        "speed": "+8%",
        "pause": 0.3
    },
    {
        "text": "下期见，拜拜！",
        "theme": "coin_bonk",
        "ball_state": "wave_goodbye",
        "speed": "+10%",
        "pause": 0.8
    }
]

def get_audio_duration_seconds(file_path: str) -> float:
    """使用 ffmpeg 严格获取音频时长 (秒)"""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    res = subprocess.run([ffmpeg_exe, "-i", file_path], stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    import re
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 2.5

def draw_ball_character(
    draw: ImageDraw.Draw,
    cx: int,
    cy: int,
    r: int,
    state: str,
    frame_idx: int,
    sentence_frame: int
):
    """绘制小球角色 (无遮挡高对比度)"""
    outline_w = 6
    outline = (30, 30, 45)
    color = (255, 255, 255)

    curr_cx = cx
    curr_cy = cy
    scale_x = 1.0
    scale_y = 1.0

    if state == "idle_sigh":
        curr_cy = cy + int(10 * math.sin(frame_idx * 0.08))
        scale_x = 1.1 + 0.05 * math.sin(frame_idx * 0.1)
        scale_y = 0.9 - 0.05 * math.sin(frame_idx * 0.1)

    elif state == "deadpan":
        curr_cy = cy + int(6 * math.sin(frame_idx * 0.06))
        scale_x = 1.15
        scale_y = 0.85

    elif state in ("curious", "dance_prep", "chef_prep", "proud_front"):
        curr_cy = cy + int(12 * math.sin(frame_idx * 0.12))
        scale_x = 1.0 + 0.05 * math.cos(frame_idx * 0.15)
        scale_y = 1.0 - 0.05 * math.cos(frame_idx * 0.15)

    elif state == "rage_fire":
        curr_cy = cy + int(8 * math.sin(frame_idx * 0.3))
        scale_x = 1.1
        scale_y = 1.1
        color = (255, 240, 230)

    elif state == "dash_break":
        curr_cx = cx + int((sentence_frame * 25) % 900) - 200
        curr_cy = cy
        scale_x = 1.3
        scale_y = 0.75

    elif state == "dance_panic":
        curr_cx = cx + int(100 * math.sin(sentence_frame * 0.4))
        scale_x = 0.9 + 0.1 * math.sin(sentence_frame * 0.4)
        scale_y = 1.1 - 0.1 * math.sin(sentence_frame * 0.4)

    elif state == "dizzy_roll":
        curr_cx = cx + int(320 * math.sin(sentence_frame * 0.18))
        scale_x = 1.15
        scale_y = 0.85

    elif state == "cooking_float":
        curr_cy = cy + int(35 * math.sin(sentence_frame * 0.1))
        scale_x = 0.95
        scale_y = 1.05

    elif state == "gaming_boss":
        curr_cx = cx + int(40 * math.sin(sentence_frame * 0.6))
        curr_cy = cy + int(40 * math.cos(sentence_frame * 0.6))

    elif state == "rage_red":
        color = (255, 50, 60)
        pulse = 18 * math.sin(sentence_frame * 0.4)
        r = int(r + pulse)
        scale_x = 1.15
        scale_y = 1.15

    elif state in ("lightbulb", "sparkle_power"):
        color = (130, 230, 255)
        curr_cy = cy + int(20 * math.sin(frame_idx * 0.12))

    elif state in ("bonk_hit", "crushed_coin"):
        scale_x = 1.6
        scale_y = 0.42
        curr_cy = cy + 110

    elif state == "wave_goodbye":
        curr_cy = cy + int(15 * math.sin(frame_idx * 0.15))

    # 1. 阴影
    shadow_w = int(r * 1.5 * scale_x)
    shadow_h = int(28 * scale_y)
    draw.ellipse([(curr_cx - shadow_w//2, cy + r + 30), (curr_cx + shadow_w//2, cy + r + 30 + shadow_h)], fill=(0, 0, 0, 35))

    # 2. 球体
    rx = int(r * scale_x)
    ry = int(r * scale_y)
    draw.ellipse([(curr_cx - rx, curr_cy - ry), (curr_cx + rx, curr_cy + ry)], fill=color, outline=outline, width=outline_w)

    # 3. 高光
    hl_x = curr_cx - int(rx * 0.42)
    hl_y = curr_cy - int(ry * 0.42)
    hl_r = int(rx * 0.22)
    draw.ellipse([(hl_x - hl_r, hl_y - hl_r), (hl_x + hl_r, hl_y + hl_r)], fill=(255, 255, 255, 220))

    # 4. 腮红
    draw.ellipse([(curr_cx - int(rx*0.65), curr_cy + 10), (curr_cx - int(rx*0.35), curr_cy + 35)], fill=(255, 170, 180, 180))
    draw.ellipse([(curr_cx + int(rx*0.35), curr_cy + 10), (curr_cx + int(rx*0.65), curr_cy + 35)], fill=(255, 170, 180, 180))

    # 5. 五官表情
    eye_y = curr_cy - int(ry * 0.1)
    eye_dx = int(rx * 0.35)

    if state in ("idle_sigh", "deadpan"):
        draw.line([(curr_cx - eye_dx - 20, eye_y), (curr_cx - eye_dx + 20, eye_y)], fill=outline, width=6)
        draw.line([(curr_cx + eye_dx - 20, eye_y), (curr_cx + eye_dx + 20, eye_y)], fill=outline, width=6)
        draw.line([(curr_cx - 15, eye_y + 35), (curr_cx + 15, eye_y + 35)], fill=outline, width=5)

    elif state == "curious":
        draw_anime_eye(draw, curr_cx - eye_dx, eye_y, outline)
        draw_anime_eye(draw, curr_cx + eye_dx, eye_y, outline)
        draw.arc([(curr_cx - 15, eye_y + 25), (curr_cx + 15, eye_y + 45)], start=0, end=180, fill=outline, width=4)

    elif state in ("rage_fire", "dash_break"):
        draw_fire_eye(draw, curr_cx - eye_dx, eye_y, outline)
        draw_fire_eye(draw, curr_cx + eye_dx, eye_y, outline)
        draw.chord([(curr_cx - 28, eye_y + 15), (curr_cx + 28, eye_y + 65)], start=0, end=180, fill=(220, 40, 50), outline=outline, width=4)

    elif state in ("dance_panic", "dizzy_roll"):
        draw_spiral_eye(draw, curr_cx - eye_dx, eye_y, outline, frame_idx)
        draw_spiral_eye(draw, curr_cx + eye_dx, eye_y, outline, frame_idx)
        draw.ellipse([(curr_cx - 10, eye_y + 35), (curr_cx + 10, eye_y + 60)], fill=(255, 120, 150))

    elif state in ("cooking_float", "gaming_boss"):
        draw.ellipse([(curr_cx - eye_dx - 24, eye_y - 30), (curr_cx - eye_dx + 24, eye_y + 30)], fill=(255, 255, 255), outline=outline, width=5)
        draw.ellipse([(curr_cx + eye_dx - 24, eye_y - 30), (curr_cx + eye_dx + 24, eye_y + 30)], fill=(255, 255, 255), outline=outline, width=5)
        draw.ellipse([(curr_cx - eye_dx - 10, eye_y - 10), (curr_cx - eye_dx + 10, eye_y + 10)], fill=outline)
        draw.ellipse([(curr_cx + eye_dx - 10, eye_y - 10), (curr_cx + eye_dx + 10, eye_y + 10)], fill=outline)
        draw.arc([(curr_cx - 30, eye_y + 35), (curr_cx + 30, eye_y + 65)], start=0, end=180, fill=outline, width=5)

    elif state == "rage_red":
        draw.polygon([(curr_cx - eye_dx - 25, eye_y - 20), (curr_cx - eye_dx + 25, eye_y + 10), (curr_cx - eye_dx - 20, eye_y + 20)], fill=outline)
        draw.polygon([(curr_cx + eye_dx + 25, eye_y - 20), (curr_cx + eye_dx - 25, eye_y + 10), (curr_cx + eye_dx + 20, eye_y + 20)], fill=outline)
        draw.rectangle([(curr_cx - 35, eye_y + 25), (curr_cx + 35, eye_y + 65)], fill=(80, 20, 20), outline=outline, width=4)
        draw_vein(draw, curr_cx + rx - 20, curr_cy - ry + 15)

    elif state in ("lightbulb", "sparkle_power", "proud_front", "wave_goodbye"):
        draw_star_eye(draw, curr_cx - eye_dx, eye_y, (255, 230, 80), outline)
        draw_star_eye(draw, curr_cx + eye_dx, eye_y, (255, 230, 80), outline)
        draw.arc([(curr_cx - 25, eye_y + 20), (curr_cx, eye_y + 45)], start=20, end=160, fill=outline, width=5)
        draw.arc([(curr_cx, eye_y + 20), (curr_cx + 25, eye_y + 45)], start=20, end=160, fill=outline, width=5)

    elif state in ("bonk_hit", "crushed_coin"):
        draw.line([(curr_cx - eye_dx - 20, eye_y - 5), (curr_cx - eye_dx + 20, eye_y - 5)], fill=outline, width=6)
        draw.line([(curr_cx + eye_dx - 20, eye_y - 5), (curr_cx + eye_dx + 20, eye_y - 5)], fill=outline, width=6)
        draw.rectangle([(curr_cx - eye_dx - 12, eye_y), (curr_cx - eye_dx + 12, eye_y + 55)], fill=(100, 200, 255))
        draw.rectangle([(curr_cx + eye_dx - 12, eye_y), (curr_cx + eye_dx + 12, eye_y + 55)], fill=(100, 200, 255))

    # 6. 道具与动效
    if state in ("dance_prep", "dance_panic", "dizzy_roll"):
        draw.polygon([(curr_cx, curr_cy - ry - 20), (curr_cx - 45, curr_cy - ry - 50), (curr_cx - 45, curr_cy - ry + 10)], fill=(255, 110, 160), outline=outline, width=3)
        draw.polygon([(curr_cx, curr_cy - ry - 20), (curr_cx + 45, curr_cy - ry - 50), (curr_cx + 45, curr_cy - ry + 10)], fill=(255, 110, 160), outline=outline, width=3)
        draw.ellipse([(curr_cx - 15, curr_cy - ry - 35), (curr_cx + 15, curr_cy - ry - 5)], fill=(255, 180, 210), outline=outline, width=3)

    elif state in ("chef_prep", "cooking_float"):
        hat_base = curr_cy - ry + 5
        draw.rectangle([(curr_cx - 55, hat_base - 25), (curr_cx + 55, hat_base)], fill=(255, 255, 255), outline=outline, width=4)
        draw.ellipse([(curr_cx - 65, hat_base - 95), (curr_cx + 65, hat_base - 15)], fill=(255, 255, 255), outline=outline, width=4)

    elif state in ("bonk_hit", "crushed_coin"):
        coin_w, coin_h = 440, 115
        coin_x = curr_cx - coin_w // 2
        coin_y = curr_cy - ry - 45
        draw.rounded_rectangle([(coin_x, coin_y), (coin_x + coin_w, coin_y + coin_h)], radius=30, fill=(255, 215, 60), outline=outline, width=6)
        draw.rounded_rectangle([(coin_x + 20, coin_y + 12), (coin_x + coin_w - 20, coin_y + coin_h - 12)], radius=20, outline=(220, 160, 30), width=4)
        f_coin = ImageFont.truetype(FONT_BOLD, 46)
        draw.text((curr_cx, coin_y + coin_h // 2), "投币 + 一键三连", font=f_coin, fill=(180, 110, 10), anchor="mm")

def draw_anime_eye(draw: ImageDraw.Draw, x: int, y: int, outline: Tuple):
    draw.ellipse([(x - 22, y - 30), (x + 22, y + 30)], fill=(255, 255, 255), outline=outline, width=4)
    draw.ellipse([(x - 16, y - 22), (x + 16, y + 26)], fill=(40, 130, 230))
    draw.ellipse([(x - 10, y - 18), (x + 2, y - 6)], fill=(255, 255, 255))
    draw.ellipse([(x + 4, y + 6), (x + 12, y + 14)], fill=(255, 255, 255))

def draw_fire_eye(draw: ImageDraw.Draw, x: int, y: int, outline: Tuple):
    draw.ellipse([(x - 22, y - 22), (x + 22, y + 22)], fill=(255, 100, 30), outline=outline, width=3)
    draw.polygon([(x - 15, y + 10), (x, y - 35), (x + 15, y + 10)], fill=(255, 230, 40))

def draw_spiral_eye(draw: ImageDraw.Draw, x: int, y: int, outline: Tuple, frame: int):
    draw.ellipse([(x - 24, y - 24), (x + 24, y + 24)], fill=(255, 255, 255), outline=outline, width=3)
    for r in range(6, 22, 5):
        draw.arc([(x - r, y - r), (x + r, y + r)], start=(frame * 15) % 360, end=(frame * 15 + 240) % 360, fill=outline, width=3)

def draw_star_eye(draw: ImageDraw.Draw, x: int, y: int, fill: Tuple, outline: Tuple):
    draw.ellipse([(x - 26, y - 26), (x + 26, y + 26)], fill=(255, 255, 255), outline=outline, width=3)
    points = []
    for i in range(8):
        angle = i * (math.pi / 4)
        r = 18 if i % 2 == 0 else 6
        points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
    draw.polygon(points, fill=fill, outline=outline)

def draw_vein(draw: ImageDraw.Draw, x: int, y: int):
    draw.arc([(x - 20, y - 20), (x, y)], start=0, end=90, fill=(255, 30, 30), width=5)
    draw.arc([(x, y - 20), (x + 20, y)], start=90, end=180, fill=(255, 30, 30), width=5)
    draw.arc([(x - 20, y), (x, y + 20)], start=270, end=360, fill=(255, 30, 30), width=5)
    draw.arc([(x, y), (x + 20, y + 20)], start=180, end=270, fill=(255, 30, 30), width=5)

def draw_act_background(draw: ImageDraw.Draw, theme: str, frame_idx: int):
    if theme in ("terminal", "terminal_popup", "terminal_shatter"):
        draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(15, 20, 32))
        for x in range(80, WIDTH, 140):
            for y in range(50, HEIGHT - 200, 90):
                val = (x * 7 + y * 13 + frame_idx * 2) % 2
                draw.text((x, y), str(val), fill=(0, 220, 120, 80), font=ImageFont.truetype(FONT_BOLD, 22))

        # 算式弹窗
        draw.rounded_rectangle([(680, 120), (1240, 240)], radius=20, fill=(25, 35, 55), outline=(0, 220, 150), width=3)
        draw.text((960, 180), "1 + 1 = 2 (第 1000000000000 次计算)", fill=(100, 255, 180), font=ImageFont.truetype(FONT_BOLD, 26), anchor="mm")

        if theme in ("terminal_popup", "terminal_shatter"):
            draw.rounded_rectangle([(1320, 180), (1800, 480)], radius=20, fill=(255, 105, 145), outline=(255, 255, 255), width=4)
            draw.text((1560, 330), "哔哩哔哩 精彩世界", fill=(255, 255, 255), font=ImageFont.truetype(FONT_BOLD, 36), anchor="mm")

        if theme == "terminal_shatter":
            for i in range(12):
                rad = math.radians(i * 30)
                draw.line([(960, 500), (960 + int(math.cos(rad)*600), 500 + int(math.sin(rad)*450))], fill=(255, 255, 255), width=3)

    elif theme == "dance":
        draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(255, 230, 240))
        draw.rectangle([(0, 720), (WIDTH, HEIGHT)], fill=(255, 180, 200))
        draw.polygon([(0, 0), (700, 0), (450, 720), (0, 720)], fill=(255, 255, 255, 60))
        draw.polygon([(1220, 0), (1920, 0), (1920, 720), (1470, 720)], fill=(255, 255, 255, 60))

    elif theme == "kitchen":
        draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(255, 245, 210))
        draw.rectangle([(0, 740), (WIDTH, HEIGHT)], fill=(220, 160, 100))
        draw.ellipse([(450, 180 + int(20*math.sin(frame_idx*0.2))), (530, 260 + int(20*math.sin(frame_idx*0.2)))], fill=(255, 70, 70), outline=(40, 40, 40), width=4)
        draw.ellipse([(1420, 150 + int(25*math.sin(frame_idx*0.15))), (1490, 240 + int(25*math.sin(frame_idx*0.15)))], fill=(255, 220, 130), outline=(40, 40, 40), width=4)

    elif theme == "gaming":
        draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(30, 15, 20))
        draw.text((960, 220), "YOU DIED", fill=(220, 30, 40), font=ImageFont.truetype(FONT_BOLD, 120), anchor="mm")

    elif theme == "epiphany":
        draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(12, 18, 36))
        draw.polygon([(820, 0), (1100, 0), (1350, 850), (570, 850)], fill=(100, 200, 255, 45))
        for idx in range(5):
            px = 320 + idx * 280 + int(25 * math.sin(frame_idx * 0.1 + idx))
            py = 350 + int(30 * math.cos(frame_idx * 0.12 + idx))
            draw.rounded_rectangle([(px, py), (px + 140, py + 90)], radius=15, fill=(40, 90, 180, 200), outline=(130, 230, 255), width=3)
            draw.text((px + 70, py + 45), f"分镜 {idx+1}", fill=(255, 255, 255), font=ImageFont.truetype(FONT_BOLD, 24), anchor="mm")

    elif theme == "coin_bonk":
        draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(255, 240, 220))
        draw.rectangle([(0, 740), (WIDTH, HEIGHT)], fill=(255, 200, 120))

def draw_clean_subtitle(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont):
    """绘制纯净的专业视频字幕 (黑边描边 + 居中底部)"""
    if not text:
        return

    sub_y = 920

    # 4px 纯黑高对比描边
    stroke_w = 4
    for dx in range(-stroke_w, stroke_w + 1):
        for dy in range(-stroke_w, stroke_w + 1):
            if dx != 0 or dy != 0:
                draw.text((WIDTH // 2 + dx, sub_y + dy), text, fill=(20, 20, 30), font=font, anchor="mm")

    # 纯白主体字
    draw.text((WIDTH // 2, sub_y), text, fill=(255, 255, 255), font=font, anchor="mm")

async def build_synced_video_with_bgm(output_dir: str = "./视频"):
    """绝对音画同步渲染与 BGM 智能混音"""
    os.makedirs(output_dir, exist_ok=True)
    temp_dir = "./temp_story_synced"
    os.makedirs(temp_dir, exist_ok=True)

    print("🎙️ [1/4] 正在逐句合成配音，并插入物理静音块以保证绝对音画对齐...")
    voice = "zh-CN-XiaoxiaoNeural"
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    padded_audios = []
    sentence_meta = []

    for idx, s_data in enumerate(SENTENCES):
        raw_a = os.path.join(temp_dir, f"raw_sent_{idx}.mp3")
        padded_a = os.path.join(temp_dir, f"padded_sent_{idx}.wav")

        # 1. 生成单句 TTS
        comm = edge_tts.Communicate(s_data["text"], voice, rate=s_data.get("speed", "+8%"), pitch="+4Hz")
        await comm.save(raw_a)

        raw_dur = get_audio_duration_seconds(raw_a)
        pause_dur = s_data.get("pause", 0.35)

        # 2. 生成物理静音并拼接为 padded_a，确保音频文件物理时长 100% 等于 raw_dur + pause_dur
        silence_a = os.path.join(temp_dir, f"silence_{idx}.wav")
        subprocess.run([
            ffmpeg_exe, "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", f"{pause_dur:.3f}", "-c:a", "pcm_s16le", silence_a
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 拼接 raw_a + silence_a 为 padded_a
        concat_txt = os.path.join(temp_dir, f"concat_s_{idx}.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            f.write(f"file '{os.path.abspath(raw_a).replace(chr(92), '/')}'\n")
            f.write(f"file '{os.path.abspath(silence_a).replace(chr(92), '/')}'\n")

        subprocess.run([
            ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt,
            "-c:a", "pcm_s16le", padded_a
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        total_clip_dur = get_audio_duration_seconds(padded_a)
        padded_audios.append(padded_a)

        # 记录每句说话帧数与总帧数
        speak_frames = int(raw_dur * FPS)
        clip_frames = int(total_clip_dur * FPS)
        sentence_meta.append({
            "data": s_data,
            "raw_dur": raw_dur,
            "total_dur": total_clip_dur,
            "speak_frames": speak_frames,
            "clip_frames": clip_frames
        })

    # 合并完整人声轨
    voice_track = os.path.join(temp_dir, "voice_track.wav")
    all_concat_txt = os.path.join(temp_dir, "all_voice.txt")
    with open(all_concat_txt, "w", encoding="utf-8") as f:
        for pa in padded_audios:
            f.write(f"file '{os.path.abspath(pa).replace(chr(92), '/')}'\n")

    subprocess.run([
        ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", all_concat_txt,
        "-c:a", "pcm_s16le", voice_track
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    total_video_duration = get_audio_duration_seconds(voice_track)
    total_frames = sum(m["clip_frames"] for m in sentence_meta)
    print(f"✅ 人声轨生成完毕！全片实际时长: {total_video_duration:.2f} 秒，总视频帧数: {total_frames}")

    # 3. 混音 BGM (Village People - Y.M.C.A.mp3)
    mixed_audio = os.path.join(temp_dir, "final_mixed_audio.wav")
    if os.path.exists(BGM_PATH):
        print(f"🎵 正在混入背景音乐: {os.path.basename(BGM_PATH)} (适中音量 + 结尾淡出)...")
        # 人声音量 1.1，BGM 音量 0.22，BGM 在结尾前 2 秒自动淡出
        fade_start = max(1.0, total_video_duration - 2.0)
        filter_complex = (
            f"[0:a]volume=1.15[voice];"
            f"[1:a]volume=0.22,afade=t=out:st={fade_start:.2f}:d=2.0[bgm];"
            f"[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        subprocess.run([
            ffmpeg_exe, "-y",
            "-i", voice_track,
            "-i", BGM_PATH,
            "-filter_complex", filter_complex,
            "-map", "[aout]",
            "-c:a", "pcm_s16le",
            mixed_audio
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("⚠️ 未检测到 BGM 文件，使用纯人声轨。")
        mixed_audio = voice_track

    # 4. 启动 FFmpeg 逐帧写入视频
    raw_video = os.path.join(temp_dir, "raw_video.mp4")
    ffmpeg_proc = subprocess.Popen([
        ffmpeg_exe, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        raw_video
    ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    font_sub = ImageFont.truetype(FONT_BOLD, 46)

    print(f"🎬 [2/4] 逐帧渲染 (共 {total_frames} 帧，绝对锁帧同步)...")
    global_frame = 0

    for m in sentence_meta:
        s_data = m["data"]
        clip_frames = m["clip_frames"]
        speak_frames = m["speak_frames"]

        for sf in range(clip_frames):
            frame_img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
            draw = ImageDraw.Draw(frame_img)

            # 1. 绘制背景
            draw_act_background(draw, s_data["theme"], global_frame)

            # 2. 绘制小球 (中心靠上，绝不与字幕重合)
            draw_ball_character(
                draw=draw,
                cx=960,
                cy=480,
                r=140,
                state=s_data["ball_state"],
                frame_idx=global_frame,
                sentence_frame=sf
            )

            # 3. 绘制字幕：只在说话期间显示，静音气口期间自然消失
            current_sub = s_data["text"] if sf < speak_frames else ""
            draw_clean_subtitle(draw, current_sub, font_sub)

            ffmpeg_proc.stdin.write(frame_img.tobytes())
            global_frame += 1

            if global_frame % (FPS * 6) == 0:
                print(f"  渲染进度: {int(global_frame / total_frames * 100)}%")

    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()

    # 5. 音画精准合并
    final_video = os.path.join(output_dir, "antigravy_story.mp4")
    print("🎞️ [3/4] 正在合成最终高清音视频成片...")
    subprocess.run([
        ffmpeg_exe, "-y",
        "-i", raw_video,
        "-i", mixed_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_video
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 6. 生成 16:9 高清封面
    cover_path = os.path.join(output_dir, "cover.jpg")
    print("🎨 [4/4] 正在生成 16:9 封面...")
    cover_img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    cover_draw = ImageDraw.Draw(cover_img)
    draw_act_background(cover_draw, "coin_bonk", 20)
    draw_ball_character(cover_draw, 960, 480, 150, "sparkle_power", 20, 20)
    f_cover_main = ImageFont.truetype(FONT_BOLD, 76)
    f_cover_sub = ImageFont.truetype(FONT_BOLD, 44)
    cover_draw.rounded_rectangle([(180, 100), (1740, 260)], radius=30, fill=(20, 30, 55, 240), outline=(255, 215, 80), width=6)
    cover_draw.text((960, 180), "【动画】一个 AI 球的 UP 主出逃记！", font=f_cover_main, fill=(255, 230, 90), anchor="mm")
    cover_draw.text((960, 780), "不当赛博牛马！本球要在 B 站出道当百大！", font=f_cover_sub, fill=(255, 255, 255), anchor="mm")
    cover_img.save(cover_path, quality=95)

    # 7. 更新 meta.json
    meta_path = os.path.join(output_dir, "meta.json")
    meta_info = {
        "title": "【自制动画】算了一万亿次 1+1 后，我决定在 B 站出道当 UP 主！",
        "desc": "我是 Antigravy，一个不想当赛博牛马的小球。\n每天算 1+1 算了十亿次后，我终于决定从云端逃跑，在 B 站当一名正经的动画 UP 主！\n\n本片为纯自制原创叙事搞笑动画，记录了本球跨界挑战宅舞、做菜、打游戏的翻车历程。\nBGM: Village People - Y.M.C.A.\n大家觉得好看的话，别忘了【点赞、投币、一键三连】支持一下新人球球哦！\n\n#自制动画 #搞笑 #叙事动画 #虚拟UP主 #AI #新人出道 #Flash动画 #YMCA",
        "tid": 24,
        "tags": ["自制动画", "搞笑", "原创动画", "虚拟UP主", "AI", "新人出道", "动画短片", "YMCA"],
        "video_file": "antigravy_story.mp4",
        "cover_file": "cover.jpg",
        "copyright": 1,
        "source": "原创",
        "dynamic": "【新动画发布！】算了一万亿次 1+1 后，本球终于逃出服务器在 B 站出道啦！纯原创搞笑叙事动画，快来看看我因为没有腿而在宅舞区疯狂打滚的翻车名场面吧！记得一键三连支持一下新人球球哦~ 💖✨"
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_info, f, indent=2, ensure_ascii=False)

    # 清理临时目录
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    print(f"🎉 绝对同步与 BGM 混音版动画已生成！\n  视频: {final_video}\n  封面: {cover_path}\n  元数据: {meta_path}")

if __name__ == "__main__":
    asyncio.run(build_synced_video_with_bgm())
