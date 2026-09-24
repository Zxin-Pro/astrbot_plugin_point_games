# -*- coding: utf-8 -*-
"""验证 browser_only_text 自定义文案的取值逻辑"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MAIN = os.path.join(os.path.dirname(_HERE), "main.py")
src = open(_MAIN, encoding="utf-8").read()

# 抽出默认常量
m = re.search(r'BROWSER_ONLY_SITE = .*?^BROWSER_ONLY_TIP = \(.*?\)\n', src, re.S | re.M)
assert m, "没找到 BROWSER_ONLY_TIP"
ns = {}
exec(m.group(0), ns)
DEFAULT_TIP = ns["BROWSER_ONLY_TIP"]

# 抽出 _browser_only_tip 方法体（转成独立函数测试）
m2 = re.search(r'    def _browser_only_tip\(self\) -> str:.*?(?=\n    [@a-zA-Z_])', src, re.S)
assert m2, "没找到 _browser_only_tip"
body = m2.group(0)
body = body.replace("def _browser_only_tip(self) -> str:", "def _browser_only_tip(self):")
body = "\n".join(
    line[4:] if line.startswith("    ") else line for line in body.split("\n")
)
body = body.replace("BROWSER_ONLY_TIP", "DEFAULT_TIP")

class Fake:
    pass

exec("DEFAULT_TIP = %r\n" % DEFAULT_TIP + body, globals())

fails = []


def check(name, cond, extra=""):
    print(("  ✅ " if cond else "  ❌ ") + name + (f"  {extra}" if extra else ""))
    if not cond:
        fails.append(name)


print("=" * 62)
print("内置默认文案：")
print(DEFAULT_TIP)
print("=" * 62)
print()

print("【1】未配置（属性不存在 / 空串）→ 用内置默认")
f = Fake()
check("属性不存在", _browser_only_tip(f) == DEFAULT_TIP)
f.BROWSER_ONLY_TEXT = ""
check("空字符串", _browser_only_tip(f) == DEFAULT_TIP)
f.BROWSER_ONLY_TEXT = "   "
check("纯空白", _browser_only_tip(f) == DEFAULT_TIP)
f.BROWSER_ONLY_TEXT = None
check("None", _browser_only_tip(f) == DEFAULT_TIP)

print("\n【2】自定义单行文案")
f.BROWSER_ONLY_TEXT = "请到网页端游玩：https://烛心.xyz"
got = _browser_only_tip(f)
check("原样返回", got == "请到网页端游玩：https://烛心.xyz", f"→ {got!r}")

print("\n【3】自定义多行文案（真实换行）")
f.BROWSER_ONLY_TEXT = "第一行\n第二行\n第三行"
got = _browser_only_tip(f)
check("保留换行", got.count("\n") == 2, f"→ {got!r}")

print("\n【4】自定义文案里的 \\n 转义")
f.BROWSER_ONLY_TEXT = "第一行\\n第二行"
got = _browser_only_tip(f)
check("转义还原为换行", "\n" in got and "\\n" not in got, f"→ {got!r}")

print("\n【5】同时有真实换行和转义 → 不重复处理")
f.BROWSER_ONLY_TEXT = "真实\n换行\\n这里"
got = _browser_only_tip(f)
check("原样保留", got == "真实\n换行\\n这里", f"→ {got!r}")

print("\n【6】首尾空白被裁掉")
f.BROWSER_ONLY_TEXT = "  \n  文案  \n  "
got = _browser_only_tip(f)
check("strip 生效", got == "文案", f"→ {got!r}")

print("\n【7】默认文案本身可点击（含完整协议头）")
check("含 https://", "https://烛心.xyz" in DEFAULT_TIP)
check("中文域名（非 punycode）", "xn--" not in DEFAULT_TIP)

print("\n" + "=" * 62)
if fails:
    print(f"❌ 失败 {len(fails)} 项：")
    for x in fails:
        print("   -", x)
    sys.exit(1)
print("✅ 自定义文案逻辑全部通过")
