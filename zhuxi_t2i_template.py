# -*- coding: utf-8 -*-
"""通用「烛之游」播报 t2i 模板

钓鱼/挖矿/修仙等播报共用的 html_render 模板：
头部品牌「烛之游」+ 标题 + 日期；每个对象一个独立卡片段；每条动态独占一行。
数据结构（tmpldata）：
{
  "title": "挖矿实况",
  "date": "09月21日 08:00",
  "cards": [
    {"name": "玩家A", "count": "3 条", "events": ["事件1", "事件2"]},
    ...
  ],
}
"""

ZHUXI_T2I_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>烛之游播报</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/misans@4.1.0/lib/Normal/MiSans-Regular.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/misans@4.1.0/lib/Normal/MiSans-Bold.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/misans@4.1.0/lib/Normal/MiSans-Medium.min.css">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html { background: #101725; }
  body {
    width: max-content;
    min-width: 880px;
    background: linear-gradient(160deg, #101725 0%, #16233a 55%, #12303c 100%);
    color: #e8eef5;
    font-family: "MiSans", -apple-system, "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
    font-size: 23px;
    padding: 34px 40px 42px;
  }
  header {
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 2px solid rgba(255,255,255,.14);
    padding-bottom: 16px; margin-bottom: 26px;
  }
  .brand { font-size: 34px; font-weight: 700; letter-spacing: .04em; color: #ffd882; }
  .brand .dot { color: #6fd3ff; }
  .sub { font-size: 19px; color: rgba(232,238,245,.55); }
  .card {
    background: rgba(255,255,255,.055);
    border: 1px solid rgba(255,255,255,.09);
    border-left: 4px solid #6fd3ff;
    border-radius: 14px;
    padding: 18px 24px 16px;
    margin-bottom: 20px;
  }
  .name {
    font-size: 26px; font-weight: 700; color: #ffd882;
    margin-bottom: 10px; white-space: nowrap;
  }
  .count {
    font-size: 17px; font-weight: 400; color: rgba(232,238,245,.5);
    margin-left: 12px;
  }
  ul { list-style: none; }
  li {
    font-size: 22px; line-height: 1.9; white-space: nowrap;
    color: #dfe9f2; padding-left: 26px; position: relative;
  }
  li::before {
    content: ""; position: absolute; left: 2px; top: 50%;
    width: 9px; height: 9px; margin-top: -4px;
    border-radius: 50%; background: #6fd3ff; opacity: .8;
  }
</style>
</head>
<body>
<header>
  <span class="brand"><span class="dot">烛</span>之游</span>
  <span class="sub">{{ title }} · {{ date }}</span>
</header>
<main>
{%- for c in cards %}
  <section class="card">
    <div class="name">{{ c.name }}{% if c.count %}<span class="count">{{ c.count }}</span>{% endif %}</div>
    <ul>
    {%- for e in c.events %}
      <li>{{ e }}</li>
    {%- endfor %}
    </ul>
  </section>
{%- endfor %}
</main>
</body>
</html>
"""
