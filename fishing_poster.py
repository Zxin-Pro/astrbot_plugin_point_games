# -*- coding: utf-8 -*-
"""钓鱼半时快报渲染（成员聚合 · 整体渐变背景 · 思源黑体 / 无 emoji 缺字问题）

布局：标题区 -> 每个成员一块，其下按 上钩/收获/落空/损失·罚款/状态 用彩色小标签罗列，
同一个人在相隔事件能连续阅读。整张背景为 深蓝→青绿 上下渐变。
"""
import os
from PIL import Image, ImageDraw, ImageFont

ORDER = ["catch", "good", "empty", "fine", "state"]
BAR = {
    "catch": (255, 208, 112), "good": (250, 194, 62),
    "empty": (150, 160, 175), "fine": (245, 110, 110), "state": (140, 190, 220),
}
TAG = {"catch": "上钩", "good": "收获", "empty": "落空", "fine": "损失·罚款", "state": "状态"}


def classify(text: str) -> str:
    if "上钩" in text or "进篓" in text or "双鱼" in text or "两条" in text or "卖鱼" in text:
        return "catch"
    if ("获得" in text or "宝箱" in text or "幸运" in text or "龙王" in text
            or "美人鱼" in text or "补贴" in text or "传授" in text):
        return "good"
    if ("空钩" in text or "一无所得" in text or "啥也没" in text or "破靴" in text
            or "大雾" in text or "暗流" in text or "拔河" in text or "激流" in text
            or "蜃楼" in text or "乌贼" in text or "漩涡" in text or "水草团" in text):
        return "empty"
    if ("罚" in text or "损失" in text or "维修" in text or "保养" in text
            or "医药" in text or "卷刃" in text or "断裂" in text or "进水" in text
            or "撞" in text):
        return "fine"
    return "state"


def font_path() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    for name in ("SourceHanSansCN-Regular.otf", "千图马克手写体.ttf"):
        p = os.path.join(base, "font", name)
        if os.path.exists(p):
            return p
    return ""


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Poster:
    W = 860

    def __init__(self):
        path = font_path()
        self.big = ImageFont.truetype(path, 34) if path else ImageFont.load_default()
        self.md = ImageFont.truetype(path, 24) if path else ImageFont.load_default()
        self.sm = ImageFont.truetype(path, 20) if path else ImageFont.load_default()

    @staticmethod
    def _wd(font, s):
        return font.getlength(s) if hasattr(font, "getlength") else font.getsize(s)[0]

    def _wrap(self, text):
        cap = self.W - 96
        out, cur = [], ""
        for ch in text:
            if self._wd(self.md, cur + ch) > cap and cur:
                out.append(cur)
                cur = ch
            else:
                cur += ch
        out.append(cur)
        while out and out[-1] == "":
            out.pop()
        return out or [""]

    def render(self, lines: list, out: str):
        users, uorder, u_cat = {}, [], {}
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            body = ln.split(" ", 1)[1] if ln.startswith("🎣") else ln
            head = body.split(" ", 1)
            if len(head) != 2 or not head[1].strip():
                continue
            uname, ev = head
            ev = ev.strip()
            if uname not in users:
                users[uname] = {k: [] for k in ORDER}
                uorder.append(uname)
            users[uname][classify(ev)].append(ev)
        # 高度：标题 + 每人(名行)块
        title_h, gap, nh = 110, 18, 40
        hh = title_h + 24
        for uname in uorder:
            hh += 40
            member_rows = 0
            for cat in ORDER:
                if not users[uname][cat]:
                    continue
                hh += 26
                for e in users[uname][cat]:
                    member_rows += len(self._wrap(e))
            hh += member_rows * 34 + 12 + gap
        # 画布
        img = Image.new("RGB", (self.W, hh), (9, 26, 40))
        dr = ImageDraw.Draw(img)
        top = (9, 36, 58)
        bottom = (12, 92, 78)
        for yy in range(hh):
            dr.line([(0, yy), (self.W, yy)],
                    fill=_mix(top, bottom, yy / max(1, hh)))
        # 标题（亮字）
        dr.text((30, 26), "钓鱼实况 · 成员汇总", font=self.big, fill=(250, 251, 253))
        dr.rectangle((30, 92, self.W - 30, 96), fill=(255, 255, 255))
        y = 124
        for uname in uorder:
            dr.text((34, y), uname, font=self.sm, fill=(255, 218, 130))
            y += 36
            for cat in ORDER:
                for e in []:
                    pass
                for ev in users[uname][cat]:
                    pass
                # flatten
                tags = users[uname][cat]
                if not tags:
                    continue
                dr.text((40, y), f"〔{TAG[cat]}〕", font=self.sm, fill=BAR[cat])
                y += 26
                for ev in tags:
                    for seg in self._wrap(ev):
                        dr.text((64, y), seg, font=self.md, fill=(213, 231, 238))
                        y += 34
            y += 10
        img.save(out)
        return out


def render_fishing_batch(lines, out_path):
    return Poster().render(lines, out_path)
