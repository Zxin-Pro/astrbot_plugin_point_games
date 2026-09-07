# -*- coding: utf-8 -*-
"""钓鱼半时快报渲染器：把同一批次判定事件解析、分类、绘制成单张圆角 PNG。"""
import os
from PIL import Image, ImageDraw, ImageFont

ORDER = {
    "catch": 0,   # 上钩/进篓（好收获）
    "good": 1,    # 正向奖励（老渔夫/宝箱/幸运）
    "empty": 2,   # 失败（空钩/暗流/大雾/杂物/脱钩）
    "fine": 3,    # 负向罚款/损失/维修
    "state": 4,   # 状态（鱼饵用完/休息）
}

CAT_BAR = {
    "catch": (60, 190, 255),
    "good": (255, 200, 80),
    "empty": (135, 145, 160),
    "fine": (255, 105, 105),
    "state": (170, 170, 190),
}
CAT_TITLE = {
    "catch": "🐟 有鱼上钩",
    "good": "✨ 意外收获",
    "empty": "😅 空手而归",
    "fine": "⚠️ 损失与罚款",
    "state": "🧺 状态提醒",
}


def classify(text: str) -> str:
    if ("上钩" in text or "进篓" in text or "双鱼" in text or "两条" in text
            or "卖鱼" in text):
        return "catch"
    if ("获得 " in text or "宝箱" in text or "幸运" in text or "传说召唤" in text
            or "龙王" in text or "美人鱼" in text or "补贴" in text or "传授" in text):
        return "good"
    if ("空钩" in text or "一无所得" in text or "啥也没" in text or "破靴子" in text
            or "大雾" in text or "暗流" in text or "海市蜃楼" in text or "锚被" in text
            or "赤墨" in text or "乌贼" in text or "拔河" in text or "水草团" in text):
        return "empty"
    if ("罚" in text or "损失" in text or "维修" in text or "保" in text or "-" in text
            or "医药" in text or "中毒" in text or "断" in text or "卷刃" in text):
        return "fine"
    return "state"


def font_path():
    here = os.path.dirname(os.path.abspath(__file__))
    for n in ("千图马克手写体.ttf", "SourceHanSansCN-Regular.otf"):
        p = os.path.join(here, "font", n)
        if os.path.exists(p):
            return p
    return ""


def _pick(name, font, text, color, **kw):
    return font, color


class FishingBatchPoster:
    MAX_W = 820
    PAD = 28

    def __init__(self):
        path = font_path()
        if path:
            self.big = ImageFont.truetype(path, 34)
            self.sec = ImageFont.truetype(path, 26)
            self.md = ImageFont.truetype(path, 24)
        else:
            self.big = self.sec = self.md = ImageFont.load_default()

    def _width(self, font, s):
        return font.getlength(s) if hasattr(font, "getlength") else font.getsize(s)[0]

    def _wrap(self, font, s):
        cap = self.MAX_W - 2 * self.PAD - 40  # 左侧留分类色条
        out, cur = [], ""
        if not s:
            return [""]
        for ch in s:
            if self._width(font, cur + ch) > cap:
                out.append(cur)
                cur = ch
            else:
                cur += ch
        if cur:
            out.append(cur)
        return out

    def render(self, raw_lines, out):
        bycat = {k: [] for k in ORDER}
        for line in raw_lines:
            line = line.strip()
            cleaner = line.split(" ", 1)[1] if line.startswith("🎣") else line
            bycat[classify(cleaner)].append(cleaner)
        body = 0
        for cat in sorted(ORDER, key=ORDER.get):
            rows_all = [self._wrap(self.md, t) for t in bycat[cat]]
            if not rows_all:
                continue
            body += 52  # 分类标题行
            body += sum(len(rs) for rs in rows_all) * 36
            body += 18
        title_h = 92
        h = title_h + body + 40
        img = Image.new("RGB", (self.MAX_W, h), (9, 30, 44))
        dr = ImageDraw.Draw(img)
        # 标题渐变
        for i in range(title_h):
            dr.line([(0, i), (self.MAX_W, i)],
                    fill=(int(15 + 0.28 * i), int(48 + 0.35 * i), int(84 + 0.18 * i)))
        dr.text((self.PAD, 24), "🎣 钓鱼实时快报", font=self.big, fill=(255, 236, 174))
        dr.line([(self.PAD - 4, 70), (self.MAX_W - self.PAD + 4, 70)],
                fill=(88, 118, 130), width=3)
        y = title_h + 16
        # 分类排序绘制
        for cat in sorted(ORDER, key=ORDER.get):
            entries = bycat[cat]
            if not entries:
                continue
            bar_color = CAT_BAR[cat]
            # 分类标题底色块
            txt = CAT_TITLE[cat]
            dr.rectangle([(self.PAD, y - 4), (self.PAD + dr.textlength(txt, font=self.sec or self.sec) and 240, y + 34)],
                         fill=(255, 255, 255))
            dr.rectangle([(self.PAD, y - 2), (self.MAX_W - self.PAD, y + 38)],
                         fill=bar_color + (0,) if isinstance(bar_color, tuple) and len(bar_color) == 4 else ((bar_color[0] // 10, bar_color[1] // 10, bar_color[2] // 10)))
            dr.rectangle([(self.PAD, y - 4), (self.PAD + 210, y + 36)], fill=bar_color)
            dr.text((self.PAD + 14, y - 2), txt, font=self.sec, fill=(255, 255, 255))
            y += 46
            for ent in entries:
                for seg in self._wrap(self.md, ent):
                    idx = seg.find("（")
                    badge = seg  # 整段已分类不需前缀
                    dr.text((self.PAD + 16, y), badge, font=self.md,
                            fill=(225, 232, 240))
                    y += 34
            y += 8
        img.save(out)
        return out


def render_fishing_batch(lines, out_path):
    return FishingBatchPoster().render(lines, out_path)
