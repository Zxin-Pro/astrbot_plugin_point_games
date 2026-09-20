# -*- coding: utf-8 -*-
"""钓鱼播报自定义 t2i 模板（烛之播报）

通过 AstrBot Star 基类 html_render(tmpl, data, return_url=True) 提交到平台 t2i 服务渲染。
布局要求：头部品牌「烛之播报」+ 日期（无版本号）；每个成员一个独立卡片段；
每条动态独占一行不换行（页面宽度随内容伸展，full_page 截图完整容纳）。
"""

FISHING_T2I_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>烛之播报</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/misans@4.1.0/lib/Normal/MiSans-Regular.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/misans@4.1.0/lib/Normal/MiSans-Bold.min.css">
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
  <span class="brand"><span class="dot">烛</span>之播报</span>
  <span class="sub">钓鱼实况 · {{ date }}</span>
</header>
<main>
{%- for m in members %}
  <section class="card">
    <div class="name">{{ m.name }}<span class="count">{{ m.events | length }} 条动态</span></div>
    <ul>
    {%- for e in m.events %}
      <li>{{ e }}</li>
    {%- endfor %}
    </ul>
  </section>
{%- endfor %}
</main>
</body>
</html>
"""
