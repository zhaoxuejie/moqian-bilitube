"""生成 OpenGraph 分享图 web/public/og.png（1200×630）。

设计对齐站点首屏：浅青白底、翠绿强调色、衬线标题 + 两处绿色数字。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "og.png"

W, H = 1200, 630

PAPER = (242, 247, 244)
INK = (31, 46, 39)
INK3 = (91, 109, 100)
ACCENT = (47, 122, 85)
WASH = (230, 241, 234)

SERIF = "C:/Windows/Fonts/simsun.ttc"
SERIF_BOLD = "C:/Windows/Fonts/simsun.ttc"
LATIN_BOLD = "C:/Windows/Fonts/georgiab.ttf"
SANS = "C:/Windows/Fonts/msyh.ttc"
SANS_BOLD = "C:/Windows/Fonts/msyhbd.ttc"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def main() -> None:
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # 右上角淡绿色块，呼应站点面板
    draw.rounded_rectangle((830, 64, 1136, 300), radius=18, fill=WASH)

    # 顶部小标签
    draw.line((72, 96, 104, 96), fill=ACCENT, width=2)
    draw.text((116, 84), "CURATED · BILIBILI · AI 大模型", font=font(SANS, 20), fill=INK3)

    # 主标题：两句，数字用主色
    big = font(SERIF_BOLD, 62)
    big_num = font(LATIN_BOLD, 66)
    small_gap = 26
    y = 150
    draw.text((72, y), "翻完 ", font=big, fill=INK)
    w = draw.textlength("翻完 ", font=big)
    draw.text((72 + w, y - 3), "3,652", font=big_num, fill=ACCENT)
    w += draw.textlength("3,652", font=big_num)
    draw.text((72 + w, y), " 个 AI 视频，", font=big, fill=INK)

    y2 = y + 62 + small_gap
    draw.text((72, y2), "留下这 ", font=big, fill=INK)
    w2 = draw.textlength("留下这 ", font=big)
    draw.text((72 + w2, y2 - 3), "1,360", font=big_num, fill=ACCENT)
    w2 += draw.textlength("1,360", font=big_num)
    draw.text((72 + w2, y2), " 个。", font=big, fill=INK)

    # 说明
    draw.text(
        (74, y2 + 108),
        "少一点寻找，多一点收获。把时间留给值得看的 AI 视频。",
        font=font(SANS, 24),
        fill=INK3,
    )

    # 底部品牌行
    draw.line((72, 534, 1128, 534), fill=(214, 228, 220), width=1)
    draw.text((72, 558), "BiliTube", font=font(LATIN_BOLD, 28), fill=INK)
    draw.text((200, 562), "AI 视频精选 · 按内容质量排序，不看播放量", font=font(SANS, 20), fill=INK3)

    # 右侧面板里的两条指标
    draw.text((870, 110), "通过筛选的候选", font=font(SANS, 18), fill=INK3)
    draw.text((868, 136), "3,652", font=font(LATIN_BOLD, 40), fill=INK)
    draw.text((870, 196), "精选视频", font=font(SANS, 18), fill=INK3)
    draw.text((868, 222), "1,360", font=font(LATIN_BOLD, 40), fill=INK)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(f"written {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
