# -*- coding: utf-8 -*-
"""离线验证：浏览器限定模式的核心逻辑（不依赖 AstrBot 运行时）"""
import re
import sys
import types

# ---------- 桩：把 astrbot 相关模块打桩，只提取被测代码 ----------
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_MAIN = os.path.join(os.path.dirname(_HERE), "main.py")
src = open(_MAIN, encoding="utf-8").read()

# 1) 抽出 BROWSER_ONLY_* 常量 + _BrowserOnlyFilter
m = re.search(
    r"BROWSER_ONLY_SITE = .*?class _ExactPointsCommandFilter",
    src, re.S,
)
assert m, "没找到浏览器限定模式代码块"
block = m.group(0)
block = block.replace("class _ExactPointsCommandFilter", "").rstrip()
assert "class _BrowserOnlyFilter" in block

# 2) 抽出 USER_COMMAND_PATTERN 以及它引用的 re
m2 = re.search(r'^USER_COMMAND_PATTERN = re\.compile\(.*?\)$', src, re.M)
assert m2, "没找到 USER_COMMAND_PATTERN"
pattern_line = m2.group(0)

ns = {"re": re}
# 打桩 CustomFilter / AstrMessageEvent
class _StubCustomFilter:
    def __init__(self, raise_error=True, **kw):
        pass

class _StubEvent:
    """最小事件桩，模拟 get_extra / set_extra / get_message_str"""
    def __init__(self, text):
        self._text = text
        self._extra = {}
    def get_message_str(self):
        return self._text
    def get_extra(self, k, d=None):
        return self._extra.get(k, d)
    def set_extra(self, k, v):
        self._extra[k] = v

ns["CustomFilter"] = _StubCustomFilter
ns["AstrMessageEvent"] = _StubEvent

exec(pattern_line, ns)
exec(block, ns)

USER_COMMAND_PATTERN = ns["USER_COMMAND_PATTERN"]
BrowserOnlyFilter = ns["_BrowserOnlyFilter"]
TIP = ns["BROWSER_ONLY_TIP"]
SITE = ns["BROWSER_ONLY_SITE"]

print("=" * 60)
print("提示文案：")
print(TIP)
print("=" * 60)

# ---------- 用例 ----------
class FakePlugin:
    def __init__(self, on):
        self.feature_flags = {"browser_only_mode": on}

fails = []

def check(name, cond):
    print(("  ✅ " if cond else "  ❌ ") + name)
    if not cond:
        fails.append(name)

print("\n【1】开关关闭时，指令应放行")
f = BrowserOnlyFilter(FakePlugin(False))
for cmd in ["转盘 10", "签到", "修仙 修炼", "挂机钓鱼", "财富榜", "抽卡"]:
    check(f"放行 {cmd}", f.filter(_StubEvent(cmd), None) is True)

print("\n【2】开关开启时，指令应被拦截")
f = BrowserOnlyFilter(FakePlugin(True))
for cmd in ["转盘 10", "签到", "修仙 修炼", "挂机钓鱼", "抽卡", "买鱼竿", "存款", "赌一把"]:
    check(f"拦截 {cmd}", f.filter(_StubEvent(cmd), None) is False)

print("\n【3】提示 handler 的指令识别逻辑（USER_COMMAND_PATTERN）")
# 该开关模式下这些都应被识别为本插件指令 → 回提示
should_match = [
    "转盘", "转盘 100", "签到", "jrzj", "今日座驾", "闯关", "攻击", "BOSS状态",
    "买彩票", "卧底开始", "投票", "掷骰", "转账 @某人 100", "开户", "存钱 500",
    "取钱", "我的银行", "发红包", "贷款 100", "还款", "积分", "查询", "查积分",
    "排行", "富豪榜", "炸弹开始", "猜 50", "速算", "抽卡", "图鉴", "水果机 100",
    "刮刮乐 3", "猜数字 10 大", "十连", "买鱼竿", "买鱼饵", "挂机钓鱼", "收鱼",
    "卖鱼", "鱼图鉴", "钓鱼天气", "鱼竿列表", "修鱼竿", "钓鱼排行", "钓鱼统计",
    "鱼塘", "升级鱼塘", "买矿镐", "买体力", "挂机挖矿", "收矿", "矿仓", "卖矿",
    "矿图鉴", "矿镐列表", "修矿镐", "矿洞", "升级矿洞", "挖矿任务", "挖矿排行",
    "挖矿统计", "偷矿", "修仙", "修仙 修炼", "种树", "浇水", "摇钱树", "收获",
    "开店", "咖啡店", "帮助", "添加车辆 宝马", "查看车池", "删除车辆 宝马",
]
for cmd in should_match:
    check(f"识别为指令：{cmd}", bool(USER_COMMAND_PATTERN.search(cmd)))

print("\n【4】非指令消息不应被误伤（正常聊天放行）")
should_not_match = [
    "今天天气不错", "哈哈哈哈", "你吃了吗", "abc", "hello world",
    "这个游戏真好玩", "我积分有多少", "帮我写首诗",
]
for cmd in should_not_match:
    check(f"不识别：{cmd}", not USER_COMMAND_PATTERN.search(cmd))

print("\n【5】幂等性：重复挂载不会叠加")
class H:
    def __init__(self, name):
        self.handler_name = name
        self.event_filters = []
        self.handler_module_path = "x.y"

handlers = [H("spin"), H("quiz"), H("browser_only_notice")]
installed = 0
for h in handlers:
    if h.handler_name == "browser_only_notice":
        continue
    if any(isinstance(x, BrowserOnlyFilter) for x in h.event_filters):
        continue
    h.event_filters.append(BrowserOnlyFilter(FakePlugin(True)))
    installed += 1
check("首次挂载 2 个", installed == 2)
check("提示 handler 未被挂载", handlers[2].event_filters == [])
check("每个 handler 只有 1 个过滤器",
      all(len(h.event_filters) <= 1 for h in handlers))

installed2 = 0
for h in handlers:
    if h.handler_name == "browser_only_notice":
        continue
    if any(isinstance(x, BrowserOnlyFilter) for x in h.event_filters):
        continue
    h.event_filters.append(BrowserOnlyFilter(FakePlugin(True)))
    installed2 += 1
check("重复挂载 0 个（幂等）", installed2 == 0)

print("\n" + "=" * 60)
if fails:
    print(f"❌ 失败 {len(fails)} 项：")
    for x in fails:
        print("   -", x)
    sys.exit(1)
print("✅ 全部通过")
