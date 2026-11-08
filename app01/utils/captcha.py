"""验证码工具 - 生成简单的字母数字图形验证码."""
import io
import random
import string
from PIL import Image, ImageDraw, ImageFont


def generate_captcha(width=120, height=40, length=4):
    """返回 (图片二进制, 验证码字符串)."""
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=length))

    img = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(img)

    # 尝试加载字体，失败则用默认
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()

    # 画干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = (random.randint(0, 200), random.randint(0, 200), random.randint(0, 200))
        draw.line([(x1, y1), (x2, y2)], fill=color, width=1)

    # 画字符
    for i, c in enumerate(code):
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        x = 15 + i * 25 + random.randint(-3, 3)
        y = 5 + random.randint(-3, 3)
        draw.text((x, y), c, fill=color, font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), code
