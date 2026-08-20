"""
B 站爆款·日系清新手绘风视频封面生成器
特点：
1. 告别暗黑赛博/神秘霓虹 AI 味，采用明亮温暖的日系动漫元气配色 (奶油白 + 暖阳黄 + 樱花粉)。
2. 彻底移除所有 Emoji 字符，杜绝任何方框乱码与字体缺失。
3. 纯手绘矢量质感：粗描边、扁平赛璐珞二次元风格、超大高对比度醒目标题。
"""
import os
import sys
import math
from PIL import Image, ImageDraw, ImageFont

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

WIDTH = 1920
HEIGHT = 1080
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
COVER_PATH = "./视频/cover.jpg"

def draw_star(draw: ImageDraw.Draw, cx: int, cy: int, r: int, fill, outline):
    points = []
    for i in range(10):
        angle = i * (math.pi / 5) - math.pi / 2
        curr_r = r if i % 2 == 0 else r * 0.45
        points.append((cx + curr_r * math.cos(angle), cy + curr_r * math.sin(angle)))
    draw.polygon(points, fill=fill, outline=outline)

def generate_bright_anime_cover():
    os.makedirs("./视频", exist_ok=True)
    # 1. 阳光明媚的日系温暖背景 (奶油白渐变到温暖浅黄)
    img = Image.new("RGB", (WIDTH, HEIGHT), (255, 252, 242))
    draw = ImageDraw.Draw(img)

    for y in range(0, HEIGHT, 4):
        ratio = y / HEIGHT
        r = int(255 - 10 * ratio)
        g = int(250 - 25 * ratio)
        b = int(240 - 70 * ratio)
        draw.rectangle([(0, y), (WIDTH, y + 4)], fill=(r, g, b))

    # 阳光放射条纹 (经典动漫元气背景)
    sun_cx, sun_cy = 480, 540
    for angle in range(0, 360, 18):
        rad1 = math.radians(angle)
        rad2 = math.radians(angle + 9)
        p1 = (sun_cx + int(math.cos(rad1)*1600), sun_cy + int(math.sin(rad1)*1200))
        p2 = (sun_cx + int(math.cos(rad2)*1600), sun_cy + int(math.sin(rad2)*1200))
        draw.polygon([(sun_cx, sun_cy), p1, p2], fill=(255, 243, 196, 120))

    # 外圈经典二次元圆角大边框
    draw.rounded_rectangle([(30, 30), (WIDTH - 30, HEIGHT - 30)], radius=35, outline=(255, 140, 160), width=10)

    # 2. 绘制左侧元气主角 Antigravy (纯手绘二次元萌球形象)
    cx, cy, r = 480, 560, 220
    outline_col = (40, 35, 55)

    # 底部阴影
    draw.ellipse([(cx - 240, cy + r - 10), (cx + 240, cy + r + 50)], fill=(230, 205, 170))

    # 主体球体 (温暖纯白 + 极简手绘粗描边)
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(255, 255, 255), outline=outline_col, width=10)

    # 角色高光
    draw.ellipse([(cx - int(r*0.48), cy - int(r*0.48)), (cx - int(r*0.16), cy - int(r*0.16))], fill=(255, 255, 255))

    # 萌系腮红
    draw.ellipse([(cx - 150, cy + 30), (cx - 70, cy + 80)], fill=(255, 165, 185))
    draw.ellipse([(cx + 70, cy + 30), (cx + 150, cy + 80)], fill=(255, 165, 185))

    # 五官：闪亮大眼睛 + 笑脸
    draw_star(draw, cx - 80, cy - 25, 45, (255, 215, 60), outline_col)
    draw_star(draw, cx + 80, cy - 25, 45, (255, 215, 60), outline_col)
    # 可爱小猫嘴
    draw.arc([(cx - 40, cy + 25), (cx, cy + 70)], start=20, end=160, fill=outline_col, width=8)
    draw.arc([(cx, cy + 25), (cx + 40, cy + 70)], start=20, end=160, fill=outline_col, width=8)

    # 角色头顶小红蝴蝶结
    draw.polygon([(cx, cy - r - 25), (cx - 65, cy - r - 65), (cx - 65, cy - r + 15)], fill=(255, 95, 130), outline=outline_col, width=6)
    draw.polygon([(cx, cy - r - 25), (cx + 65, cy - r - 65), (cx + 65, cy - r + 15)], fill=(255, 95, 130), outline=outline_col, width=6)
    draw.ellipse([(cx - 22, cy - r - 45), (cx + 22, cy - r - 5)], fill=(255, 150, 175), outline=outline_col, width=6)

    # 角色左上方身份小卡片
    draw.rounded_rectangle([(cx - 190, cy - r - 125), (cx + 190, cy - r - 55)], radius=18, fill=(255, 100, 140), outline=outline_col, width=5)
    f_badge = ImageFont.truetype(FONT_BOLD, 34)
    draw.text((cx, cy - r - 90), "新人 UP 主出道！", font=f_badge, fill=(255, 255, 255), anchor="mm")

    # 3. 绘制右侧超清大字报 (高对比度、纯中文无乱码、层次清晰)
    card_x1 = 820
    card_y1 = 100
    card_x2 = 1840
    card_y2 = 980

    # 纯白圆角大底板 (带可爱彩色阴影)
    draw.rounded_rectangle([(card_x1 + 12, card_y1 + 12), (card_x2 + 12, card_y2 + 12)], radius=30, fill=(255, 210, 220))
    draw.rounded_rectangle([(card_x1, card_y1), (card_x2, card_y2)], radius=30, fill=(255, 255, 255), outline=outline_col, width=8)

    # 顶部红色 Tag
    draw.rounded_rectangle([(card_x1 + 50, card_y1 + 45), (card_x1 + 50 + 360, card_y1 + 115)], radius=16, fill=(255, 75, 105), outline=outline_col, width=4)
    f_tag = ImageFont.truetype(FONT_BOLD, 36)
    draw.text((card_x1 + 50 + 180, card_y1 + 80), "自制搞笑动画", font=f_tag, fill=(255, 255, 255), anchor="mm")

    # 主标题第一行: 我是 Antigravy！
    f_title1 = ImageFont.truetype(FONT_BOLD, 92)
    t1_x = card_x1 + 50
    t1_y = card_y1 + 205
    # 纯黑粗描边
    for dx in range(-6, 7):
        for dy in range(-6, 7):
            if dx != 0 or dy != 0:
                draw.text((t1_x + dx, t1_y + dy), "我是 Antigravy！", font=f_title1, fill=(40, 35, 55))
    # 鲜亮明黄填充
    draw.text((t1_x, t1_y), "我是 Antigravy！", font=f_title1, fill=(255, 210, 40))

    # 主标题第二行: 算了一万亿次 1+1 后...
    f_title2 = ImageFont.truetype(FONT_BOLD, 54)
    t2_y = card_y1 + 365
    draw.text((t1_x, t2_y), "算了一万亿次 1+1 后……", font=f_title2, fill=(80, 120, 200))

    # 主标题第三行: 我跑来 B 站当 UP 主啦！
    f_title3 = ImageFont.truetype(FONT_BOLD, 76)
    t3_y = card_y1 + 475
    for dx in range(-6, 7):
        for dy in range(-6, 7):
            if dx != 0 or dy != 0:
                draw.text((t1_x + dx, t3_y + dy), "我来 B 站当 UP 主啦！", font=f_title3, fill=(40, 35, 55))
    draw.text((t1_x, t3_y), "我来 B 站当 UP 主啦！", font=f_title3, fill=(255, 85, 125))

    # 标签卡片栏
    badges = [
        ("拒绝当赛博牛马", (255, 130, 80)),
        ("翻车名场面大赏", (100, 190, 255)),
        ("神曲 BGM 加持", (255, 195, 60))
    ]
    tag_start_y = card_y1 + 630
    bx = t1_x
    for label, bcol in badges:
        bw = int(len(label) * 36 + 45)
        draw.rounded_rectangle([(bx, tag_start_y), (bx + bw, tag_start_y + 70)], radius=16, fill=bcol, outline=outline_col, width=4)
        f_b = ImageFont.truetype(FONT_BOLD, 30)
        draw.text((bx + bw // 2, tag_start_y + 35), label, font=f_b, fill=(255, 255, 255), anchor="mm")
        bx += bw + 20

    # 底部标语
    f_foot = ImageFont.truetype(FONT_BOLD, 42)
    draw.text((t1_x, card_y1 + 755), "一键三连关注我，见证百大成长之路！", font=f_foot, fill=(60, 60, 80))

    # 4. 保存
    img.save(COVER_PATH, quality=95)
    print(f"🎉 日系元气手绘风封面生成完毕！已保存至: {COVER_PATH}")

if __name__ == "__main__":
    generate_bright_anime_cover()
