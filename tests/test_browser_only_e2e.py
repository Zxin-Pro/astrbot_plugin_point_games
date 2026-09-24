# -*- coding: utf-8 -*-
"""端到端逻辑仿真：模拟 AstrBot 的 waking_check + star_request 两阶段，
验证浏览器限定模式下的实际行为（不改动真实环境）。"""
import asyncio
import re

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_MAIN = os.path.join(os.path.dirname(_HERE), "main.py")
src = open(_MAIN, encoding="utf-8").read()

m = re.search(r"BROWSER_ONLY_SITE = .*?class _ExactPointsCommandFilter", src, re.S)
block = m.group(0).replace("class _ExactPointsCommandFilter", "").rstrip()
m2 = re.search(r"^USER_COMMAND_PATTERN = re\.compile\(.*?\)$", src, re.M)
pattern_line = m2.group(0)

class StubCustomFilter:
    def __init__(self, raise_error=True, **kw):
        self.raise_error = raise_error

class StubEvent:
    def __init__(self, text):
        self._text = text
        self._extra = {}
        self.is_wake = False
        self._stopped = False
    def get_message_str(self): return self._text
    def get_extra(self, k, d=None): return self._extra.get(k, d)
    def set_extra(self, k, v): self._extra[k] = v
    def stop_event(self): self._stopped = True
    def is_stopped(self): return self._stopped
    def plain_result(self, t): return ("plain", t)

ns = {"re": re, "CustomFilter": StubCustomFilter, "AstrMessageEvent": StubEvent}
exec(pattern_line, ns)
exec(block, ns)
USER_COMMAND_PATTERN = ns["USER_COMMAND_PATTERN"]
BrowserOnlyFilter = ns["_BrowserOnlyFilter"]
TIP = ns["BROWSER_ONLY_TIP"]


class Handler:
    def __init__(self, name, filters, fn, priority=0):
        self.handler_name = name
        self.event_filters = filters
        self.handler_module_path = "p.main"
        self.extras_configs = {"priority": priority}
        self.fn = fn


class FakePlugin:
    """复刻 browser_only_notice 的方法体"""
    def __init__(self, on):
        self.feature_flags = {"browser_only_mode": on}
    async def browser_only_notice(self, event):
        if not bool((self.feature_flags or {}).get("browser_only_mode", False)):
            return
        raw = str(event.get_message_str() or "").strip()
        if not raw:
            return
        if not USER_COMMAND_PATTERN.search(raw):
            return
        yield event.plain_result(TIP)
        event.stop_event()


async def dispatch(plugin, handlers, text):
    """模拟 AstrBot：filter 求值 → 按 priority 降序执行 → stop 则中断"""
    event = StubEvent(text)
    # 阶段1：filter
    activated = []
    for h in handlers:
        passed = True
        for f in h.event_filters:
            try:
                if not f.filter(event, None):
                    passed = False
                    break
            except Exception:
                passed = False
                break
        if passed:
            activated.append(h)
    # 阶段2：按 priority 降序执行
    activated.sort(key=lambda h: -h.extras_configs["priority"])
    outputs = []
    for h in activated:
        if event.is_stopped():
            break
        async for r in h.fn(event):
            outputs.append(r)
    return outputs, event


async def main():
    fails = []
    def check(name, cond):
        print(("  ✅ " if cond else "  ❌ ") + name)
        if not cond: fails.append(name)

    for mode, expect_tip in ((True, True), (False, False)):
        print(f"\n{'='*60}\n模式：browser_only_mode = {mode}\n{'='*60}")
        plug = FakePlugin(mode)
        bo = BrowserOnlyFilter(plug)
        def make_play(name, cmd):
            async def play(event):
                # 真实 handler 有 command filter，只对匹配指令生效（前缀匹配即可）
                if not str(event.get_message_str()).strip().startswith(cmd):
                    return
                yield ("plain", f"[{name}] 玩法正常执行")
            return play

        handlers = [
            Handler("browser_only_notice", [], plug.browser_only_notice, priority=9999),
            Handler("spin", [bo], make_play("转盘", "转盘")),
            Handler("sign_in", [bo], make_play("签到", "签到")),
            Handler("xiuxian", [bo], make_play("修仙", "修仙")),
            Handler("fishing", [bo], make_play("挂机钓鱼", "挂机钓鱼")),
        ]
        for cmd in ["转盘 10", "签到", "修仙 修炼", "挂机钓鱼"]:
            outs, ev = await dispatch(plug, handlers, cmd)
            texts = [o[1] for o in outs]
            has_tip = any("浏览器" in t for t in texts)
            played = any("玩法正常执行" in t for t in texts)
            print(f"\n  指令「{cmd}」→ 输出 {len(outs)} 条, 事件停止={ev.is_stopped()}")
            if expect_tip:
                check(f"  返回引导文案", has_tip)
                check(f"  事件被终止", ev.is_stopped())
                check(f"  玩法未执行", not played)
            else:
                check(f"  不返回引导文案（放行）", not has_tip)
                check(f"  玩法正常执行", played)

        # 非指令消息
        outs, ev = await dispatch(plug, handlers, "今天天气不错")
        print(f"\n  闲聊「今天天气不错」→ 输出 {len(outs)} 条")
        check("  闲聊不受影响", len(outs) == 0 and not ev.is_stopped())

    print("\n" + "="*60)
    if fails:
        print(f"❌ 失败 {len(fails)} 项")
        for f in fails: print("   -", f)
        raise SystemExit(1)
    print("✅ 端到端仿真全部通过")

asyncio.run(main())
