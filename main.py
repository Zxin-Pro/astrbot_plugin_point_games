# -*- coding: utf-8 -*-
"""
AstrBot 积分游戏插件
=========================
功能：幸运转盘 / 闯关答题 / BOSS 战 / 大乐透 / 谁是卧底 / 钓鱼系统 / 签到排行
特性：全群积分数据互通、全局排行榜、WebUI 管理面板、群黑白名单（默认全部关闭）

作者：Zxin_Pro    版本：2.18.5
仓库：https://github.com/Zxin-Pro/astrbot_plugin_point_games
"""

import asyncio
import json
import os
import random
import re
import time
from datetime import date, datetime, timedelta
from string import Formatter
from typing import Any, Optional

from sqlalchemy import text

# ---------- AstrBot 框架导入 ----------
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import CustomFilter, EventMessageType, PermissionType
from astrbot.api.message_components import At, AtAll, Image, Plain, Reply
from astrbot.api.star import Context, Star, register

# ---------- 定时任务 ----------
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# 时区（北京时间）
try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Asia/Shanghai")
except ImportError:  # Python < 3.9 兜底
    from pytz import timezone as _pytz_tz

    TZ = _pytz_tz("Asia/Shanghai")

# 主动发消息（私聊发词 / 开奖广播）需要的会话类，尽量从公共 API 取，取不到再退回 core
try:
    from astrbot.api.platform import MessageType as _MessageType
except ImportError:  # pragma: no cover
    from astrbot.core.platform.message_type import MessageType as _MessageType

try:
    from astrbot.core.platform.message_session import MessageSession
except ImportError:  # pragma: no cover
    MessageSession = None


# ============================================================
#  题库（内置 54 道，difficulty: 1 简单 / 2 中等 / 3 困难）
# ============================================================
QUESTION_BANK: list[dict] = [
    {"q": "中国最大的岛屿是哪个？", "options": ["台湾岛", "海南岛", "崇明岛"], "answer": 0, "difficulty": 1},
    {"q": "1 光年大约是多久？", "options": ["9.46 万亿公里", "1 亿公里", "100 万公里"], "answer": 0, "difficulty": 3},
    {"q": "人体最大的器官是什么？", "options": ["皮肤", "肝脏", "大脑"], "answer": 0, "difficulty": 1},
    {"q": "《西游记》中孙悟空用的兵器是？", "options": ["如意金箍棒", "九齿钉耙", "降妖宝杖"], "answer": 0, "difficulty": 1},
    {"q": "地球绕太阳公转一圈大约需要？", "options": ["365 天", "30 天", "100 天"], "answer": 0, "difficulty": 1},
    {"q": "水的化学式是？", "options": ["H2O", "CO2", "O2"], "answer": 0, "difficulty": 1},
    {"q": "我国国歌的歌名是？", "options": ["义勇军进行曲", "东方红", "歌唱祖国"], "answer": 0, "difficulty": 1},
    {"q": "一年有多少个星期？", "options": ["52 个", "48 个", "60 个"], "answer": 0, "difficulty": 1},
    {"q": "中国最大的沙漠是？", "options": ["塔克拉玛干沙漠", "撒哈拉沙漠", "腾格里沙漠"], "answer": 0, "difficulty": 2},
    {"q": "太阳系中最大的行星是？", "options": ["木星", "土星", "海王星"], "answer": 0, "difficulty": 1},
    {"q": "《三国演义》中「桃园三结义」不包括谁？", "options": ["曹操", "刘备", "张飞"], "answer": 0, "difficulty": 2},
    {"q": "人体正常体温大约是多少摄氏度？", "options": ["36-37", "38-39", "34-35"], "answer": 0, "difficulty": 1},
    {"q": "中国的首都是？", "options": ["北京", "上海", "广州"], "answer": 0, "difficulty": 1},
    {"q": "彩虹有几种颜色？", "options": ["7 种", "5 种", "9 种"], "answer": 0, "difficulty": 1},
    {"q": "100 的平方根是多少？", "options": ["10", "20", "50"], "answer": 0, "difficulty": 1},
    {"q": "长城被称为？", "options": ["万里长城", "千尺长城", "百里长城"], "answer": 0, "difficulty": 1},
    {"q": "世界上最长的河流是？", "options": ["尼罗河", "长江", "亚马逊河"], "answer": 0, "difficulty": 2},
    {"q": "《红楼梦》的作者是？", "options": ["曹雪芹", "施耐庵", "罗贯中"], "answer": 0, "difficulty": 2},
    {"q": "1 千克等于多少克？", "options": ["1000 克", "100 克", "10 克"], "answer": 0, "difficulty": 1},
    {"q": "动物界中奔跑速度最快的是？", "options": ["猎豹", "狮子", "羚羊"], "answer": 0, "difficulty": 1},
    {"q": "我们呼吸的气体中，占比例最大的是？", "options": ["氮气", "氧气", "二氧化碳"], "answer": 0, "difficulty": 2},
    {"q": "中国古代四大发明不包括？", "options": ["地动仪", "造纸术", "火药"], "answer": 0, "difficulty": 2},
    {"q": "世界上人口最多的国家是？", "options": ["印度", "中国", "美国"], "answer": 0, "difficulty": 1},
    {"q": "一年中最热的节气是？", "options": ["大暑", "立秋", "夏至"], "answer": 0, "difficulty": 2},
    {"q": "我国第一部诗歌总集是？", "options": ["诗经", "楚辞", "乐府诗集"], "answer": 0, "difficulty": 3},
    {"q": "吃鱼的动物中，哪种是哺乳动物？", "options": ["鲸鱼", "鲨鱼", "带鱼"], "answer": 0, "difficulty": 1},
    {"q": "端午节是为了纪念谁？", "options": ["屈原", "李白", "苏轼"], "answer": 0, "difficulty": 1},
    {"q": "0.5 乘以 0.5 等于？", "options": ["0.25", "0.5", "1"], "answer": 0, "difficulty": 1},
    {"q": "世界上最高的山峰是？", "options": ["珠穆朗玛峰", "乔戈里峰", "乞力马扎罗山"], "answer": 0, "difficulty": 1},
    {"q": "地球上最大的海洋是？", "options": ["太平洋", "大西洋", "印度洋"], "answer": 0, "difficulty": 1},
    {"q": "下列哪种动物是两栖动物？", "options": ["青蛙", "鳄鱼", "乌龟"], "answer": 0, "difficulty": 1},
    {"q": "鲁迅的原名是？", "options": ["周树人", "周作人", "周建人"], "answer": 0, "difficulty": 2},
    {"q": "24 点游戏：3, 3, 8, 8 如何得到 24？", "options": ["8÷(3-8÷3)", "3×8+3-8", "8×3-3-8"], "answer": 0, "difficulty": 3},
    {"q": "中国最长的河流是？", "options": ["长江", "黄河", "珠江"], "answer": 0, "difficulty": 1},
    {"q": "人体内最长的骨骼是？", "options": ["股骨", "胫骨", "肱骨"], "answer": 0, "difficulty": 2},
    {"q": "声音在下列哪种介质中传播最快？", "options": ["钢铁", "水", "空气"], "answer": 0, "difficulty": 2},
    {"q": "圆周率 π 约等于？", "options": ["3.14", "2.71", "1.41"], "answer": 0, "difficulty": 1},
    {"q": "我国少数民族中人口最多的是？", "options": ["壮族", "回族", "满族"], "answer": 0, "difficulty": 2},
    {"q": "一年中白天最长的一天是？", "options": ["夏至", "冬至", "春分"], "answer": 0, "difficulty": 2},
    {"q": "《水浒传》中「及时雨」指的是谁？", "options": ["宋江", "武松", "林冲"], "answer": 0, "difficulty": 2},
    {"q": "世界上面积最大的国家是？", "options": ["俄罗斯", "加拿大", "中国"], "answer": 0, "difficulty": 1},
    {"q": "下列哪个是硬通货货币？", "options": ["美元", "日元", "韩元"], "answer": 0, "difficulty": 3},
    {"q": "地球的卫星是？", "options": ["月球", "火星", "金星"], "answer": 0, "difficulty": 1},
    {"q": "人体最大的消化腺是？", "options": ["肝脏", "胰腺", "胃"], "answer": 0, "difficulty": 3},
    {"q": "下列哪个是中国的传统节日？", "options": ["中秋节", "感恩节", "万圣节"], "answer": 0, "difficulty": 1},
    {"q": "12 英寸等于多少厘米？", "options": ["约 30.5 厘米", "约 20 厘米", "约 40 厘米"], "answer": 0, "difficulty": 2},
    {"q": "植物进行光合作用需要哪种气体？", "options": ["二氧化碳", "氧气", "氮气"], "answer": 0, "difficulty": 2},
    {"q": "下列哪种动物会冬眠？", "options": ["熊", "猫", "狗"], "answer": 0, "difficulty": 1},
    {"q": "中国四大名著中成书最早的是？", "options": ["水浒传", "红楼梦", "三国演义"], "answer": 0, "difficulty": 3},
    {"q": "下列哪个是光学仪器？", "options": ["显微镜", "温度计", "气压计"], "answer": 0, "difficulty": 2},
    {"q": "26 个英文字母中第 13 个是？", "options": ["M", "N", "L"], "answer": 0, "difficulty": 1},
    {"q": "人体有多少块骨骼（成年人）？", "options": ["206 块", "306 块", "106 块"], "answer": 0, "difficulty": 2},
    {"q": "下列哪个城市被称为「天府之国」？", "options": ["成都", "重庆", "昆明"], "answer": 0, "difficulty": 2},
    {"q": "扑克牌中「J」代表什么？", "options": ["侍从", "国王", "王后"], "answer": 0, "difficulty": 3},
]

# ============================================================
#  谁是卧底词库（35 组相近词对）
# ============================================================
DAILY_CAR_FIELDS = {"user_name", "car", "date"}
DAILY_CAR_DEFAULT_POOL = [
    "豪华旅行车 | 年代：2017 | 保时捷 Panamera Sport Turismo | 马力：330–680",
    "跑车 | 年代：2023 | 保时捷 911 GT3 RS (992) | 马力：525",
    "SUV | 年代：2021 | 保时捷 Cayenne Turbo GT (E3) | 马力：640",
    "超级跑车 | 年代：2013 | 保时捷 918 Spyder | 马力：887（综合）",
    "纯电轿车 | 年代：2024 | 保时捷 Taycan Turbo GT | 马力：815–1034（超增压）",
]
DAILY_CAR_DEFAULT_TEMPLATE = "🚗 {user_name}\n您今天的专属座驾是：\n{car}"
DAILY_CAR_ADD_PATTERN = re.compile(r"(?i)^添加车辆(?:\s+)(?P<car>.+?)\s*$")
DAILY_CAR_DELETE_PATTERN = re.compile(r"^删除车辆(?:\s+)(?P<car>.+?)\s*$")
USER_COMMAND_PATTERN = re.compile(r"(?i)^/?(?:积分(?:\s|$)|签到|jrzj|今日座驾|掷骰(?:\s|$)|转盘|闯关|攻击|BOSS状态|BOSS排行|买彩票|彩票奖池|卧底开始|加入卧底|投票|卧底结束|炸弹开始|猜|炸弹结束|速算|抽卡|图鉴|查询|查积分|排行|加积分|减积分|清除数据|初始化|买鱼竿|买鱼饵|挂机钓鱼|收鱼|卖鱼|鱼图鉴|鱼竿列表|修鱼竿|钓鱼排行|钓鱼统计|兑换礼品|转账(?:\s|$)|开户(?:\s|$)|存钱(?:\s|$)|取钱(?:\s|$)|我的银行(?:\s|$)|本群玩法|玩法模式|本群状态|帮助|添加车辆(?:\s|$)|查看车池|删除车辆(?:\s|$))")

WORD_PAIRS: list[tuple[str, str]] = [
    ("钢笔", "铅笔"), ("西瓜", "哈密瓜"), ("猫", "狗"), ("苹果", "香蕉"),
    ("火车", "高铁"), ("微信", "QQ"), ("面包", "蛋糕"), ("牛奶", "豆浆"),
    ("眼镜", "墨镜"), ("雨伞", "雨衣"), ("手机", "平板"), ("地铁", "公交"),
    ("饺子", "馄饨"), ("薯条", "薯片"), ("篮球", "足球"), ("吉他", "尤克里里"),
    ("电影", "电视剧"), ("可乐", "雪碧"), ("火锅", "麻辣烫"), ("图书馆", "书店"),
    ("老师", "教授"), ("咖啡", "奶茶"), ("猴子", "猩猩"), ("老虎", "狮子"),
    ("兔子", "仓鼠"), ("玫瑰", "月季"), ("出租车", "网约车"), ("面条", "米线"),
    ("鸡蛋", "鸭蛋"), ("熊猫", "北极熊"), ("衬衫", "T恤"), ("凉鞋", "拖鞋"),
    ("菠萝", "凤梨"), ("蜂蜜", "蜂王浆"), ("篮球鞋", "跑步鞋"),
]


# ============================================================
#  钓鱼系统配置
# ============================================================
# 鱼类总表：稀有度 -> (该稀有度总概率%, [(鱼名, 售价), ...])
# 共 102 种；同稀有度内各鱼均分概率（至高传说两种各 0.0001%）
FISH_TABLE: dict[str, tuple[float, list[tuple[str, int]]]] = {
    "普通": (58.0, [
        ("小虾米", 3), ("鲫鱼", 4), ("鲤鱼", 5), ("草鱼", 5), ("鲢鱼", 4), ("鳙鱼", 4),
        ("青鱼", 5), ("罗非鱼", 5), ("鲮鱼", 4), ("白条鱼", 3), ("麦穗鱼", 3), ("鳑鲏", 4),
        ("小黄鱼", 3), ("沙丁鱼", 3), ("凤尾鱼", 4), ("银鱼", 5), ("多春鱼", 3), ("秋刀鱼", 4),
        ("鲭鱼", 5), ("鲳鱼", 6), ("红杉鱼", 7), ("马鲛鱼", 8), ("鲈鱼", 9), ("鳜鱼", 10),
    ]),
    "稀有": (15.5, [
        ("金鱼", 30), ("银龙鱼", 65), ("红龙鱼", 80), ("金龙鱼", 90), ("七彩神仙", 50),
        ("罗汉鱼", 45), ("地图鱼", 40), ("鹦鹉鱼", 35), ("招财鱼", 50), ("虎鱼", 70),
        ("孔雀鱼", 35), ("灯鱼", 45), ("神仙鱼", 65), ("龙睛金鱼", 100), ("七彩鱼", 90),
    ]),
    "珍稀": (4.0, [
        ("中华鲟", 130), ("长江鲥鱼", 110), ("松江鲈鱼", 100), ("大马哈鱼", 90), ("虹鳟鱼", 85),
        ("银鲳鱼", 80), ("金枪鱼", 120), ("三文鱼", 100), ("石斑鱼", 110), ("东星斑", 140),
        ("老鼠斑", 150), ("苏眉鱼", 160), ("哲罗鲑", 70), ("狗鱼", 60), ("海鲈鱼", 80),
        ("黄鱼", 90),
    ]),
    "传说": (0.55, [
        ("神话金龙", 500), ("九色神鲤", 480), ("冰雪龙鱼", 450), ("凤凰锦鲤", 400), ("玄天黑鲤", 380),
    ]),
    "远古": (0.1, [
        ("腔棘鱼", 800), ("恐龙鱼", 700), ("巨骨舌鱼", 650), ("鳄雀鳝", 600), ("龙鱼化石", 900),
        ("太古鳐鱼", 1000),
    ]),
    "海洋传说": (0.025, [
        ("北海巨妖", 1200), ("沧龙遗种", 1500), ("利维坦幼崽", 1300), ("深海海妖", 1100),
        ("海神波塞冬", 1500),
    ]),
    "终极神话": (0.007, [
        ("东方青龙", 3000), ("玄武神龟", 2500), ("鲲鹏之祖", 4000),
    ]),
    "至高传说": (0.0006, [
        ("烛心", 10000), ("闲鱼", 10000), ("小洛", 10000), ("满穗", 10000),
    ]),
}

# 展开为 鱼名 -> (售价, 稀有度, 单条概率%)，供加权抽取与广播使用
# 注意：上表概率合计约 78.18%（v2.18.1 上调高价值鱼），剩余约 21.8% 判定为钓上杂物（一无所得）
FISH_POOL: dict[str, tuple[int, str, float]] = {}
for _rarity, (_total_prob, _fishes) in FISH_TABLE.items():
    _per_prob = _total_prob / len(_fishes)
    for _name, _price in _fishes:
        FISH_POOL[_name] = (_price, _rarity, _per_prob)
del _rarity, _total_prob, _fishes, _per_prob, _name, _price

# 钓鱼随机事件表：(事件名, 概率%)，按顺序累计判定，总和 100
FISHING_EVENTS: list[tuple[str, float]] = [
    ("正常上钩", 70.0),   # 钓到 1 条鱼（v2.18.1 再上调，上鱼更容易）
    ("空钩", 17.5),       # 一无所获（幸运日 buff 期间视为上钩）
    ("鱼竿断裂", 2.5),    # 鱼竿损坏，停止挂机，需 /修鱼竿
    ("双鱼上钩", 6.0),    # 一次钓到 2 条
    ("大鱼拔河", 3.0),    # 大鱼脱钩，一无所获
    ("神秘宝箱", 0.7),    # 随机开出 50~100 积分
    ("海怪来袭", 0.2),    # 鱼被吓跑，鱼竿断裂
    ("暴风雨", 0.08),     # 恶劣天气，一无所获
    ("幸运日", 0.02),     # 获得 2 小时幸运 buff：期间空钩视为上钩
]

# 长期期望说明（v2.15.1 调参后）：上钩 67.5% + 双鱼 5% ≈ 每次判定期望卖鱼 13.0 积分，
# 扣鱼饵 10 积分、断竿摊销 2 积分（4% × 修理费 50），宝箱（50~100）期望回补约 0.53，
# 长期期望 ≈ +1.5 积分/次（长期挂机稍微赚，高价值鱼纯看脸）。

# ============================================================
#  玩法帮助注册表
#  【扩展玩法】以后新增玩法时：
#   1. 在下方 COMMAND_HELP 加一行 (指令, 说明)
#   2. 在类里新增一个 @filter.command 处理器 + 对应的内部方法
#   3. 需要定时任务就在 initialize() 里 add_job
#   介绍指令 /帮助 会自动展示，无需改动其他代码
# ============================================================
COMMAND_HELP: list[tuple[str, str]] = [
    ("/积分", "查看自己的积分、收入、支出与签到信息"),
    ("/帮助", "玩法介绍与指令列表"),
    ("/掷骰 @群友", "与群友比大小，胜者+10，平局各+5"),
    ("群活跃奖励", "每日结算群内发言前三名，奖励50/30/10积分"),
    ("/转盘 [积分]", "幸运转盘，最高5倍返还"),
    ("/闯关", "答题闯关，答对得分答错扣分"),
    ("/攻击", "消耗5积分打BOSS，伤害100-500"),
    ("/BOSS状态", "查看BOSS血量与今日战况"),
    ("/BOSS排行", "今日伤害前十"),
    ("/买彩票 [积分]", "每日20:00开奖，每期限购10注"),
    ("/彩票奖池", "查看当前奖池与参与人数"),
    ("/卧底开始 [人数]", "谁是卧底（群聊，需报名）"),
    ("/加入卧底", "报名卧底游戏"),
    ("/投票 @某人", "投票阶段投出卧底"),
    ("/卧底结束", "管理员强制结束"),
    ("/炸弹开始", "数字炸弹（1-100猜数字，猜中者-30，其他人+5）"),
    ("/猜 [数字]", "炸弹游戏中猜数字"),
    ("/炸弹结束", "强制结束炸弹游戏（仅管理员）"),
    ("/速算", "速算挑战（答对得5/15/30积分，每天10次）"),
    ("/抽卡", "消耗10积分抽卡（N/R/SR/SSR）"),
    ("/图鉴", "查看已收集的卡牌和进度"),
    ("/买鱼竿", "钓鱼系统：200积分购买鱼竿（最多5根）"),
    ("/买鱼饵 [数量]", "钓鱼系统：10积分/个购买鱼饵"),
    ("/挂机钓鱼 [编号]", "钓鱼系统：鱼竿挂机，每30分钟判定一次"),
    ("/收鱼", "钓鱼系统：收取挂机钓到的鱼进鱼篓"),
    ("/卖鱼", "钓鱼系统：一键卖出鱼篓里所有鱼"),
    ("/鱼图鉴", "钓鱼系统：查看鱼类收集进度（共102种）"),
    ("/鱼竿列表", "钓鱼系统：查看每根鱼竿状态"),
    ("/修鱼竿 [编号]", "钓鱼系统：50积分修理损坏的鱼竿"),
    ("/钓鱼排行", "钓鱼系统：累计卖鱼收入前十名"),
    ("/钓鱼统计", "钓鱼系统：查看自己的钓鱼数据与称号"),
    ("/兑换礼品", "花费10000积分兑换小礼品一份（兑换后联系管理员领取）"),
    ("/转账 @群友 [积分]", "向群友或指定QQ转账（1-5000，10%手续费）"),
    ("/开户", "银行系统：开通银行账户（免费，享每日5%活期利息）"),
    ("/存钱 [积分]", "银行系统：将钱包积分存入银行"),
    ("/取钱 [积分]", "银行系统：从银行取出积分到钱包"),
    ("/我的银行", "银行系统：查看活期余额与累计利息"),
    ("每日收税", "凌晨0点自动收取余额0.1%税款（余额≥1000才扣，自动执行）"),
    ("/赞助", "查看赞助积分方式（仅私聊）"),
    ("/赞助审核", "提交赞助申请（引用订单截图，仅私聊）"),
    ("/赞助通过 [QQ] [积分]", "管理员审核通过"),
    ("/赞助拒绝 [QQ] [理由]", "管理员拒绝申请"),
    ("/赞助列表", "查看待审核申请（管理员）"),
    ("签到 / jrzj / 今日座驾", "群内触发每日座驾并完成积分签到"),
    ("/查询", "查看自己的积分、收入、支出与签到信息"),
    ("/查积分 @玩家", "查询其他玩家的积分信息"),
    ("/排行", "全服积分排行榜"),
    ("/加积分 /减积分", "调整积分（仅配置页管理员QQ）"),
    ("/清除数据 @玩家", "清除指定玩家账户和流水（仅管理员）"),
    ("/初始化 @玩家", "清除指定玩家账户和流水（仅管理员）"),
    ("/本群玩法 开|关", "群管理员开关本群玩法"),
    ("/玩法模式 白名单|黑名单", "全局模式切换"),
    ("/本群状态", "查看本群与全局状态"),
]


class _BizError(Exception):
    """业务错误：抛出后事务回滚并返回友好提示"""

    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


class _ExactPointsCommandFilter(CustomFilter):
    """只匹配单独的 /积分，避免抢占 /子指令。"""

    def filter(self, event: AstrMessageEvent, cfg) -> bool:
        try:
            return event.get_message_str().strip() == "积分"
        except Exception:
            return False


@register(
    name="积分游戏",
    author="Zxin_Pro",
    desc="幸运转盘/闯关答题/BOSS战/大乐透/谁是卧底/签到排行，全群数据互通，支持WebUI面板与群黑白名单",
    version="2.18.7",
    repo="https://github.com/Zxin-Pro/astrbot_plugin_point_games",
)
class PointGamesPlugin(Star):
    """积分游戏：发送 /帮助 查看全部玩法说明，签到触发每日座驾"""

    # ---------- 数字常量（可自行调整） ----------
    # 幸运转盘概率表：[区间下限, 区间上限, 返还比例, 表情]
    SPIN_TABLE = [
        (1, 40, 0.0, "💀"),
        (41, 70, 0.5, "😅"),
        (71, 85, 0.8, "😌"),
        (86, 95, 1.2, "🙂"),
        (96, 99, 2.0, "🎉"),
        (100, 100, 5.0, "🔥"),
    ]
    SPIN_DEFAULT_COST = 10          # 转盘默认消耗
    # BOSS 战
    BOSS_MAX_HP = 10000             # BOSS 初始血量
    BOSS_POOL = 500                 # BOSS 死亡分红池
    ATTACK_COST = 5                 # 每次攻击消耗
    ATTACK_COOLDOWN = 10            # 攻击冷却（秒）
    ATTACK_DAMAGE_MIN = 100         # 最小伤害
    ATTACK_DAMAGE_MAX = 500         # 最大伤害
    # 大乐透
    LOTTERY_DEFAULT_COST = 10       # 每注默认价格
    LOTTERY_LIMIT_PER_DAY = 10      # 每人每期限购
    LOTTERY_BASE_POOL = 100         # 奖池保底
    LOTTERY_PRIZE = {3: 0.10, 4: 0.30, 5: 0.60}   # 匹配数 -> 奖池比例
    LOTTERY_DRAW_HOUR = 20           # 开奖小时（北京时间）
    LOTTERY_DRAW_MINUTE = 0          # 开奖分钟
    BOSS_RESET_HOUR = 0               # BOSS 重置小时（北京时间）
    BOSS_RESET_MINUTE = 0             # BOSS 重置分钟
    # 闯关答题
    QUIZ_TIMEOUT = 60               # 每题限时（秒）
    QUIZ_STREAK_BONUS_EVERY = 5     # 每连对 N 题触发额外奖励
    QUIZ_STREAK_BONUS = 20          # 连击额外奖励
    QUIZ_WRONG_PENALTY = 5          # 答错扣分
    # 签到
    SIGN_IN_MIN = 1                 # 签到随机积分下限
    SIGN_IN_MAX = 10                # 签到随机积分上限
    SIGN_IN_WEEK_BONUS = 20         # 连续签到 7 天额外奖励
    # 通用
    COMMAND_COOLDOWN = 3            # 每条指令冷却（秒）
    DICE_DAILY_LIMIT = 5            # 掷骰每日次数上限（可配置）
    ACTIVITY_SETTLE_HOUR = 22       # 群活跃奖励结算小时（可配置）
    ACTIVITY_SETTLE_MINUTE = 0      # 群活跃奖励结算分钟（可配置）
    LEADERBOARD_BROADCAST_HOUR = 12 # 全服排行榜播报小时（可配置）
    LEADERBOARD_BROADCAST_MINUTE = 0 # 全服排行榜播报分钟（可配置）
    ACTIVITY_REWARDS = (50, 30, 10)
    # 谁是卧底
    UC_MIN_PLAYERS = 4
    UC_MAX_PLAYERS = 12
    UC_DEFAULT_PLAYERS = 6
    # 消费达标提醒
    SPEND_REWARD_THRESHOLD = 10000  # 消费达标阈值
    # 积分转账
    TRANSFER_FEE_RATE = 0.1         # 手续费比例：10%（向下取整）
    TRANSFER_MIN = 1                # 单次转账最低积分
    TRANSFER_MAX = 5000             # 单次转账最高积分
    TRANSFER_DAILY_LIMIT = 10       # 每日转账次数上限
    TRANSFER_COOLDOWN = 10          # 转账冷却（秒）
    FEE_RECEIVER = ""               # 手续费接收账户QQ（配置页 fee_receiver，默认第一个管理员）
    # 每日自动收税
    TAX_RATE = 0.001                # 税率：余额的 0.1%（向下取整）
    TAX_MIN_BALANCE = 1000          # 余额达到该值才触发扣税
    # 银行系统
    CURRENT_INTEREST_RATE = 0.05    # 活期利率：5%/天（向下取整）
    ADMIN_EXTRA_RATE = 0.01         # 管理员额外收益：存款总额的 1%/天（独立发放）
    BANK_REPORT_TIME = (21, 0)      # 每日流水报告时间 (时, 分)，可配置
    BANK_REPORT_GROUP = []          # 流水报告发送群聊ID列表（空则不发送）
    UC_SPEECH_SECONDS = 120         # 每轮发言限时（秒）
    UC_VOTE_SECONDS = 60            # 投票限时（秒）
    UC_LOBBY_SECONDS = 120          # 报名等待（秒）
    # 数字炸弹
    BOMB_MIN = 1                    # 炸弹范围最小值
    BOMB_MAX = 100                  # 炸弹范围最大值
    BOMB_PENALTY = 30               # 踩到炸弹扣分
    BOMB_MIN_BALANCE = 30           # 玩炸弹的积分门槛（低于不给玩）
    BOMB_REWARD = 5                 # 其他参与者奖励
    # 速算挑战
    MATH_TIMEOUT = 15               # 速算限时（秒）
    MATH_DAILY_LIMIT = 10           # 每天限玩次数
    MATH_REWARD_EASY = 5            # 简单题奖励
    MATH_REWARD_MEDIUM = 15         # 中等题奖励
    MATH_REWARD_HARD = 30           # 困难题奖励
    # 抽卡系统
    CARD_COST = 10                  # 每次抽卡消耗
    CARD_POOL = {                   # 卡池：稀有度 -> (概率, [卡牌名])
        "N": (0.50, ["N-咸鱼", "N-小猫咪", "N-小乌龟", "N-小仓鼠", "N-小兔子"]),
        "R": (0.30, ["R-小狐狸", "R-锦鲤", "R-小鹿", "R-小熊猫", "R-小海豚"]),
        "SR": (0.15, ["SR-独角兽", "SR-凤凰", "SR-麒麟", "SR-白虎", "SR-玄武"]),
        "SSR": (0.05, ["SSR-神龙", "SSR-金龙", "SSR-银龙", "SSR-冰龙", "SSR-火龙"]),
    }
    CARD_COMPLETE_REWARD = 100      # 集齐所有稀有度奖励
    # 钓鱼系统
    MAX_RODS = 5                    # 每人最多鱼竿数
    ROD_COST = 200                  # 鱼竿价格
    BAIT_COST = 10                  # 鱼饵单价
    REPAIR_COST = 50                # 修鱼竿费用
    CHECK_INTERVAL = 30             # 挂机判定间隔（分钟）
    FISHING_BOX_MIN = 50            # 神秘宝箱积分下限
    FISHING_BOX_MAX = 100           # 神秘宝箱积分上限
    FISHING_LUCKY_HOURS = 2         # 幸运日 buff 时长（小时）
    FISHING_FULL_REWARD = 5000      # 集齐 102 种图鉴奖励
    FISHING_BOTH_LEGEND_REWARD = 1000  # 同时拥有烛心和闲鱼额外奖励
    FISHING_BROADCAST_PRICE = 1000  # 触发全群广播的鱼价阈值
    FISHING_BROADCAST_GROUPS = []   # 钓鱼播报群列表（配置页填写，留空播报到挂机所在群）
    FISHING_RESET_HOUR = 0          # 今日统计重置小时
    FISHING_RESET_MINUTE = 0        # 今日统计重置分钟
    FISHING_RANK_SIZE = 10          # 钓鱼排行显示人数
    # 赞助系统
    SPONSOR_RATE = 100              # 1元=100积分（仅展示）
    SPONSOR_ADMIN_QQ_LIST = []      # 管理员QQ列表（配置页填写）
    SPONSOR_GROUP_ID = None         # 管理员群ID（可选，配置页填写）
    DEFAULT_GROUP_MODE = "whitelist"
    FEATURES = {
        "enable_spin": True,
        "enable_quiz": True,
        "enable_boss": True,
        "enable_lottery": True,
        "enable_undercover": True,
        "enable_sign_in": True,
        "enable_ranking": True,
        "enable_bomb": True,
        "enable_math": True,
        "enable_card": True,
        "enable_fishing": True,
        "enable_transfer": True,
        "enable_activity": True,
        "enable_tax": True,
        "enable_bank": True,
    }
    FEATURE_COMMANDS = {
        "转盘": ("enable_spin", "幸运转盘"),
        "闯关": ("enable_quiz", "闯关答题"),
        "攻击": ("enable_boss", "BOSS战"),
        "BOSS状态": ("enable_boss", "BOSS战"),
        "BOSS排行": ("enable_boss", "BOSS战"),
        "买彩票": ("enable_lottery", "大乐透"),
        "彩票奖池": ("enable_lottery", "大乐透"),
        "卧底开始": ("enable_undercover", "谁是卧底"),
        "加入卧底": ("enable_undercover", "谁是卧底"),
        "投票": ("enable_undercover", "谁是卧底"),
        "炸弹开始": ("enable_bomb", "数字炸弹"),
        "猜": ("enable_bomb", "数字炸弹"),
        "炸弹结束": ("enable_bomb", "数字炸弹"),
        "速算": ("enable_math", "速算挑战"),
        "抽卡": ("enable_card", "抽卡系统"),
        "图鉴": ("enable_card", "抽卡系统"),
        "排行": ("enable_ranking", "积分排行"),
        "签到": ("enable_sign_in", "签到"),
        "积分": ("enable_ranking", "积分账户"),
        "买鱼竿": ("enable_fishing", "钓鱼系统"),
        "买鱼饵": ("enable_fishing", "钓鱼系统"),
        "挂机钓鱼": ("enable_fishing", "钓鱼系统"),
        "收鱼": ("enable_fishing", "钓鱼系统"),
        "卖鱼": ("enable_fishing", "钓鱼系统"),
        "鱼图鉴": ("enable_fishing", "钓鱼系统"),
        "鱼竿列表": ("enable_fishing", "钓鱼系统"),
        "修鱼竿": ("enable_fishing", "钓鱼系统"),
        "钓鱼排行": ("enable_fishing", "钓鱼系统"),
        "钓鱼统计": ("enable_fishing", "钓鱼系统"),
        "兑换礼品": ("enable_ranking", "消费兑换"),
        "转账": ("enable_transfer", "积分转账"),
        "开户": ("enable_bank", "银行系统"),
        "存钱": ("enable_bank", "银行系统"),
        "取钱": ("enable_bank", "银行系统"),
        "我的银行": ("enable_bank", "银行系统"),
    }

    # ---------- 表结构定义 ----------
    TABLE_DDL = [
        """CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            user_name TEXT DEFAULT '',
            balance INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            sign_in_date TEXT,
            sign_in_streak INTEGER DEFAULT 0,
            reward_reminded INTEGER DEFAULT 0,
            gift_redeemed INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS lottery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            numbers TEXT,
            cost INTEGER,
            period TEXT,
            platform_id TEXT DEFAULT '',
            group_id TEXT DEFAULT ''
        )""",
        "CREATE INDEX IF NOT EXISTS idx_lottery_period ON lottery(period)",
        """CREATE TABLE IF NOT EXISTS boss (
            id INTEGER PRIMARY KEY,
            current_hp INTEGER DEFAULT 10000,
            reset_date TEXT,
            pool INTEGER DEFAULT 500
        )""",
        """CREATE TABLE IF NOT EXISTS boss_damage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            damage INTEGER,
            attack_time TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_boss_damage_user ON boss_damage(user_id)",
        """CREATE TABLE IF NOT EXISTS quiz_sessions (
            user_id TEXT PRIMARY KEY,
            question_index INTEGER,
            streak INTEGER,
            question_data TEXT,
            expire_time TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS cooldown (
            user_id TEXT PRIMARY KEY,
            last_command_time TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS undercover_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT,
            status TEXT,
            players TEXT,
            civilian_word TEXT,
            undercover_word TEXT,
            undercover_id TEXT,
            votes TEXT,
            round INTEGER,
            current_speaker_index INTEGER,
            phase TEXT,
            platform_id TEXT DEFAULT '',
            updated_at TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_uc_group ON undercover_games(group_id)",
        """CREATE TABLE IF NOT EXISTS point_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            amount INTEGER,
            operation TEXT,
            earned INTEGER DEFAULT 0,
            spent INTEGER DEFAULT 0,
            balance_after INTEGER DEFAULT 0,
            create_time TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pt_user ON point_transactions(user_id)",
        """CREATE TABLE IF NOT EXISTS dice_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            UNIQUE(user_id, date)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_dice_records_user_date ON dice_records(user_id, date)",
        """CREATE TABLE IF NOT EXISTS daily_cars (
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            car_name TEXT NOT NULL,
            PRIMARY KEY(user_id, date)
        )""",
        "DROP TABLE IF EXISTS first_use_users",
        """CREATE TABLE IF NOT EXISTS group_settings (
            group_id TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            updated_at TIMESTAMP,
            platform_id TEXT DEFAULT ''
        )""",
        """CREATE TABLE IF NOT EXISTS plugin_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS lottery_pool (
            period TEXT PRIMARY KEY,
            pool INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS bomb_games (
            group_id TEXT PRIMARY KEY,
            target_number INTEGER,
            min_range INTEGER,
            max_range INTEGER,
            participants TEXT,
            platform_id TEXT DEFAULT '',
            created_at TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS math_challenges (
            user_id TEXT PRIMARY KEY,
            question TEXT,
            answer TEXT,
            difficulty TEXT,
            expire_time TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS math_daily_count (
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, date)
        )""",
        """CREATE TABLE IF NOT EXISTS cards (
            user_id TEXT NOT NULL,
            card_name TEXT NOT NULL,
            rarity TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            PRIMARY KEY(user_id, card_name)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cards_user ON cards(user_id)",
        """CREATE TABLE IF NOT EXISTS sponsor_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            amount INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            admin_id TEXT,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            handle_time TIMESTAMP,
            remark TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_sponsor_user ON sponsor_requests(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_sponsor_status ON sponsor_requests(status)",
        # ---------- 群活跃统计（落库，插件重启/更新后可恢复） ----------
        """CREATE TABLE IF NOT EXISTS activity_stats (
            group_key TEXT NOT NULL,
            date TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT DEFAULT '',
            count INTEGER DEFAULT 0,
            PRIMARY KEY(group_key, date, user_id)
        )""",
        # ---------- 钓鱼系统 ----------
        """CREATE TABLE IF NOT EXISTS fishing_rods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            slot INTEGER,
            status TEXT DEFAULT 'idle',
            platform_id TEXT DEFAULT '',
            group_id TEXT DEFAULT '',
            created_at TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_fishing_rods_user ON fishing_rods(user_id)",
        """CREATE TABLE IF NOT EXISTS fishing_baits (
            user_id TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS fishing_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            fish_name TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            UNIQUE(user_id, fish_name)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_fishing_inv_user ON fishing_inventory(user_id)",
        """CREATE TABLE IF NOT EXISTS fishing_pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            fish_name TEXT,
            catch_time TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_fishing_pending_user ON fishing_pending(user_id)",
        # 图鉴收集（钓到过即记录，卖鱼不影响图鉴进度）
        """CREATE TABLE IF NOT EXISTS fishing_collection (
            user_id TEXT NOT NULL,
            fish_name TEXT NOT NULL,
            first_time TIMESTAMP,
            PRIMARY KEY(user_id, fish_name)
        )""",
        """CREATE TABLE IF NOT EXISTS fishing_stats (
            user_id TEXT PRIMARY KEY,
            total_caught INTEGER DEFAULT 0,
            total_income INTEGER DEFAULT 0,
            total_baits_used INTEGER DEFAULT 0,
            lucky_day INTEGER DEFAULT 0,
            lucky_day_expire TIMESTAMP,
            today_count INTEGER DEFAULT 0,
            today_date TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS transfer_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user TEXT,
            to_user TEXT,
            amount INTEGER,
            fee INTEGER,
            total INTEGER,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS tax_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            amount INTEGER,
            date TEXT,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS bank_accounts (
            user_id TEXT PRIMARY KEY,
            current_balance INTEGER DEFAULT 0,
            total_interest INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS bank_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            type TEXT,
            amount INTEGER,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]

    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context, config)
        # AstrBot 会把 _conf_schema.json 中的配置作为 dict 注入这里。
        # 运行时配置只在插件加载时读取，修改后重新加载插件即可生效。
        self.config = config if config is not None else {}
        self._apply_runtime_config(self.config)
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._uc_jobs: dict[str, Any] = {}      # group_id -> apscheduler Job（卧底计时器）
        self._daily_car_lock = asyncio.Lock()
        self._dice_lock = asyncio.Lock()
        self._activity_counts: dict[str, dict[str, dict[str, Any]]] = {}
        self._activity_lock = asyncio.Lock()
        self._bomb_games: dict[str, dict] = {}  # group_id -> {target, min, max, participants[]}
        self._math_sessions: dict[str, dict] = {}  # user_id -> {question, answer, difficulty, expire}
        # 兼容不同版本的数据库获取方式
        self._db = None
        ctx = self.context
        if hasattr(ctx, "get_db"):
            self._db = ctx.get_db()
        elif hasattr(ctx, "db"):
            self._db = ctx.db

    def _apply_runtime_config(self, config: dict):
        """把配置页中的值应用到玩法常量，异常值回退到安全默认值。"""
        def boolean(key, default):
            value = config.get(key, default)
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "on", "开")
            return bool(value)

        def integer(key, default, minimum=0):
            try:
                value = int(config.get(key, default))
                return value if value >= minimum else default
            except (TypeError, ValueError):
                return default

        def number(key, default, minimum=0.0):
            try:
                value = float(config.get(key, default))
                return value if value >= minimum else default
            except (TypeError, ValueError):
                return default

        self.feature_flags = {
            key: boolean(key, default) for key, default in self.FEATURES.items()
        }
        mode = str(config.get("group_mode", self.DEFAULT_GROUP_MODE)).strip().lower()
        self.DEFAULT_GROUP_MODE = mode if mode in ("whitelist", "blacklist") else "whitelist"
        self.SPIN_DEFAULT_COST = integer("spin_default_cost", self.SPIN_DEFAULT_COST, 1)
        self.BOSS_MAX_HP = integer("boss_max_hp", self.BOSS_MAX_HP, 1)
        self.BOSS_POOL = integer("boss_pool", self.BOSS_POOL, 0)
        self.ATTACK_COST = integer("attack_cost", self.ATTACK_COST, 0)
        self.ATTACK_COOLDOWN = integer("attack_cooldown", self.ATTACK_COOLDOWN, 0)
        self.ATTACK_DAMAGE_MIN = integer("attack_damage_min", self.ATTACK_DAMAGE_MIN, 1)
        self.ATTACK_DAMAGE_MAX = max(
            integer("attack_damage_max", self.ATTACK_DAMAGE_MAX, 1), self.ATTACK_DAMAGE_MIN
        )
        self.LOTTERY_DEFAULT_COST = integer("lottery_default_cost", self.LOTTERY_DEFAULT_COST, 1)
        self.LOTTERY_LIMIT_PER_DAY = integer("lottery_limit_per_day", self.LOTTERY_LIMIT_PER_DAY, 1)
        self.LOTTERY_BASE_POOL = integer("lottery_base_pool", self.LOTTERY_BASE_POOL, 0)
        self.LOTTERY_DRAW_HOUR = min(integer("lottery_draw_hour", self.LOTTERY_DRAW_HOUR, 0), 23)
        self.LOTTERY_DRAW_MINUTE = min(integer("lottery_draw_minute", self.LOTTERY_DRAW_MINUTE, 0), 59)
        self.BOSS_RESET_HOUR = min(integer("boss_reset_hour", self.BOSS_RESET_HOUR, 0), 23)
        self.BOSS_RESET_MINUTE = min(integer("boss_reset_minute", self.BOSS_RESET_MINUTE, 0), 59)
        self.LOTTERY_PRIZE = {
            3: number("lottery_prize_3", self.LOTTERY_PRIZE[3], 0.0),
            4: number("lottery_prize_4", self.LOTTERY_PRIZE[4], 0.0),
            5: number("lottery_prize_5", self.LOTTERY_PRIZE[5], 0.0),
        }
        # 转盘六档概率权重与返还倍率均可在插件配置页调整。
        spin_defaults = [40, 30, 15, 10, 4, 1]
        spin_keys = ["spin_weight_0", "spin_weight_50", "spin_weight_80",
                     "spin_weight_120", "spin_weight_200", "spin_weight_500"]
        self.spin_weights = [integer(k, d, 0) for k, d in zip(spin_keys, spin_defaults)]
        
        # 数字炸弹配置
        self.BOMB_MIN = integer("bomb_min", self.BOMB_MIN, 1)
        self.BOMB_MAX = max(integer("bomb_max", self.BOMB_MAX, 2), self.BOMB_MIN + 1)
        self.BOMB_PENALTY = integer("bomb_penalty", self.BOMB_PENALTY, 0)
        self.BOMB_REWARD = integer("bomb_reward", self.BOMB_REWARD, 0)

        # 钓鱼系统配置：播报群列表（支持逗号分隔字符串或列表）
        raw_fbg = config.get("fishing_broadcast_groups", [])
        if isinstance(raw_fbg, str):
            raw_fbg = [x.strip() for x in raw_fbg.replace("，", ",").split(",") if x.strip()]
        self.FISHING_BROADCAST_GROUPS = [
            str(x).strip() for x in (raw_fbg or []) if str(x).strip()
        ]
        
        # 速算挑战配置
        self.MATH_TIMEOUT = integer("math_timeout", self.MATH_TIMEOUT, 1)
        self.MATH_DAILY_LIMIT = integer("math_daily_limit", self.MATH_DAILY_LIMIT, 1)
        self.MATH_REWARD_EASY = integer("math_reward_easy", self.MATH_REWARD_EASY, 0)
        self.MATH_REWARD_MEDIUM = integer("math_reward_medium", self.MATH_REWARD_MEDIUM, 0)
        self.MATH_REWARD_HARD = integer("math_reward_hard", self.MATH_REWARD_HARD, 0)
        
        # 抽卡系统配置
        self.CARD_COST = integer("card_cost", self.CARD_COST, 1)
        self.CARD_COMPLETE_REWARD = integer("card_complete_reward", self.CARD_COMPLETE_REWARD, 0)
        if sum(self.spin_weights) <= 0:
            self.spin_weights = spin_defaults
        rate_keys = ["spin_rate_0", "spin_rate_50", "spin_rate_80",
                     "spin_rate_120", "spin_rate_200", "spin_rate_500"]
        rate_defaults = [0.0, 0.5, 0.8, 1.2, 2.0, 5.0]
        self.spin_rates = [number(k, d, 0.0) for k, d in zip(rate_keys, rate_defaults)]
        self.QUIZ_TIMEOUT = integer("quiz_timeout", self.QUIZ_TIMEOUT, 1)
        self.QUIZ_STREAK_BONUS_EVERY = integer("quiz_streak_bonus_every", self.QUIZ_STREAK_BONUS_EVERY, 1)
        self.QUIZ_STREAK_BONUS = integer("quiz_streak_bonus", self.QUIZ_STREAK_BONUS, 0)
        self.QUIZ_WRONG_PENALTY = integer("quiz_wrong_penalty", self.QUIZ_WRONG_PENALTY, 0)
        self.SIGN_IN_MIN = integer("sign_in_min", self.SIGN_IN_MIN, 0)
        self.SIGN_IN_MAX = max(integer("sign_in_max", self.SIGN_IN_MAX, 0), self.SIGN_IN_MIN)
        self.SIGN_IN_WEEK_BONUS = integer("sign_in_week_bonus", self.SIGN_IN_WEEK_BONUS, 0)
        self.COMMAND_COOLDOWN = integer("command_cooldown", self.COMMAND_COOLDOWN, 0)
        self.DICE_DAILY_LIMIT = integer("dice_daily_limit", self.DICE_DAILY_LIMIT, 1)
        self.ACTIVITY_SETTLE_HOUR = min(integer("activity_settle_hour", self.ACTIVITY_SETTLE_HOUR, 0), 23)
        self.ACTIVITY_SETTLE_MINUTE = min(integer("activity_settle_minute", self.ACTIVITY_SETTLE_MINUTE, 0), 59)
        self.LEADERBOARD_BROADCAST_HOUR = min(integer("leaderboard_broadcast_hour", self.LEADERBOARD_BROADCAST_HOUR, 0), 23)
        self.LEADERBOARD_BROADCAST_MINUTE = min(integer("leaderboard_broadcast_minute", self.LEADERBOARD_BROADCAST_MINUTE, 0), 59)
        self.UC_MIN_PLAYERS = integer("uc_min_players", self.UC_MIN_PLAYERS, 2)
        self.UC_MAX_PLAYERS = max(integer("uc_max_players", self.UC_MAX_PLAYERS, 2), self.UC_MIN_PLAYERS)
        self.UC_DEFAULT_PLAYERS = min(
            max(integer("uc_default_players", self.UC_DEFAULT_PLAYERS, self.UC_MIN_PLAYERS), self.UC_MIN_PLAYERS),
            self.UC_MAX_PLAYERS,
        )
        self.UC_SPEECH_SECONDS = integer("uc_speech_seconds", self.UC_SPEECH_SECONDS, 1)
        self.UC_VOTE_SECONDS = integer("uc_vote_seconds", self.UC_VOTE_SECONDS, 1)
        self.UC_LOBBY_SECONDS = integer("uc_lobby_seconds", self.UC_LOBBY_SECONDS, 1)

        # 管理员QQ：/加积分 /扣积分 指令仅对名单内QQ生效（支持逗号/中文逗号分隔）
        raw = config.get("admin_qq", [])
        if isinstance(raw, str):
            raw = [x for x in raw.replace("，", ",").split(",") if x.strip()]
        elif not isinstance(raw, (list, tuple, set)):
            raw = []
        self.ADMIN_QQ = {str(x).strip() for x in raw if str(x).strip()}
        # 记录配置页中的第一个管理员，作为手续费账户的默认值
        first_admin = ""
        if isinstance(raw, list) and raw:
            first_admin = str(raw[0]).strip()
        elif isinstance(raw, str) and raw.strip():
            first_admin = raw.split(",")[0].strip()
        # 积分转账手续费接收账户：优先配置页 fee_receiver，缺省回落到第一个管理员
        fee_receiver = str(config.get("fee_receiver", "") or "").strip()
        self.FEE_RECEIVER = fee_receiver or first_admin
        # 每日收税参数
        try:
            tax_rate = float(config.get("tax_rate", self.TAX_RATE))
            self.TAX_RATE = tax_rate if 0 < tax_rate <= 1 else self.TAX_RATE
        except (TypeError, ValueError):
            pass
        self.TAX_MIN_BALANCE = integer("tax_min_balance", self.TAX_MIN_BALANCE, 1)
        # 银行利率参数
        try:
            rate = float(config.get("bank_interest_rate", self.CURRENT_INTEREST_RATE))
            self.CURRENT_INTEREST_RATE = rate if 0 <= rate <= 1 else self.CURRENT_INTEREST_RATE
        except (TypeError, ValueError):
            pass
        try:
            extra = float(config.get("bank_admin_extra_rate", self.ADMIN_EXTRA_RATE))
            self.ADMIN_EXTRA_RATE = extra if 0 <= extra <= 1 else self.ADMIN_EXTRA_RATE
        except (TypeError, ValueError):
            pass
        # 银行流水报告时间与群聊
        report_time = str(config.get("bank_report_time", "") or "").strip() or "21:00"
        try:
            h, m = report_time.split(":")
            self.BANK_REPORT_TIME = (max(0, min(23, int(h))), max(0, min(59, int(m))))
        except (ValueError, TypeError):
            self.BANK_REPORT_TIME = (21, 0)
        raw_groups = str(config.get("bank_report_group", "") or "").strip()
        self.BANK_REPORT_GROUP = [g.strip() for g in raw_groups.replace("，", ",").split(",") if g.strip()]
        
        # 赞助系统配置
        self.SPONSOR_RATE = integer("sponsor_rate", self.SPONSOR_RATE, 1)
        raw_admin = config.get("sponsor_admin_qq", [])
        if isinstance(raw_admin, str):
            raw_admin = [x for x in raw_admin.replace("，", ",").split(",") if x.strip()]
        elif not isinstance(raw_admin, (list, tuple, set)):
            raw_admin = []
        self.SPONSOR_ADMIN_QQ_LIST = [str(x).strip() for x in raw_admin if str(x).strip()]
        group_id_raw = config.get("sponsor_group_id", "")
        self.SPONSOR_GROUP_ID = str(group_id_raw).strip() if str(group_id_raw).strip() else None
        
        self.daily_car_pool, self.daily_car_template = self._validate_daily_car_config(config)

    @staticmethod
    def _normalize_car_text(car: str) -> str:
        """兼容配置页中的真实换行和 \\n 转义换行。"""
        return car.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n").strip()

    @classmethod
    def _validate_daily_car_config(cls, config: dict) -> tuple[list[str], str]:
        """校验并加载每日座驾配置，格式与原每日座驾插件一致。"""
        raw_pool = config.get("car_pool", DAILY_CAR_DEFAULT_POOL)
        if not isinstance(raw_pool, list):
            raw_pool = DAILY_CAR_DEFAULT_POOL
        pool = [cls._normalize_car_text(car) for car in raw_pool if isinstance(car, str) and car.strip()]
        pool = [car for car in pool if car]
        template = config.get("reply_template", DAILY_CAR_DEFAULT_TEMPLATE)
        if not isinstance(template, str) or not template.strip():
            template = DAILY_CAR_DEFAULT_TEMPLATE
        try:
            for _, field_name, format_spec, conversion in Formatter().parse(template):
                if field_name is not None and (field_name not in DAILY_CAR_FIELDS or format_spec or conversion is not None):
                    raise ValueError
        except (ValueError, KeyError):
            template = DAILY_CAR_DEFAULT_TEMPLATE
        return pool, template

    @staticmethod
    def _format_car_entry(car: str) -> str:
        """按原配置顺序输出车辆条目，清理空行。"""
        return "\n".join(part.strip() for part in car.split("\n") if part.strip())

    # ---------- 数据库工具 ----------
    def _get_db(self):
        if self._db is not None:
            return self._db
        ctx = self.context
        if hasattr(ctx, "get_db"):
            return ctx.get_db()
        return ctx.db

    def _session(self):
        """获取一个数据库会话（async context manager）"""
        return self._get_db().get_db()

    async def _tx(self, fn, *args, **kwargs):
        """在一个事务中执行 fn(session, *args)，成功提交返回 (True, msg, data)，失败回滚返回 (False, msg, None)"""
        try:
            async with self._session() as session:
                try:
                    async with session.begin():
                        ok, msg, data = await fn(session, *args, **kwargs)
                        if not ok:
                            raise _BizError(msg)
                        return (True, msg, data)
                except _BizError as e:
                    return (False, e.msg, None)
        except Exception as e:  # 数据库异常统一兜底
            self.logger.exception("积分游戏插件数据库操作失败")
            return (False, f"数据库开小差了喵~：{e}", None)

    async def _save_daily_car_config(self, pool: list[str]) -> None:
        """将车池回写 AstrBot 插件配置页。"""
        self.daily_car_pool = pool
        try:
            self.config["car_pool"] = pool
            saver = getattr(self.config, "save_config_async", None)
            if saver:
                await saver({"car_pool": pool})
        except Exception:
            self.logger.exception("每日座驾车池保存失败")
            raise _BizError("车池保存失败，请稍后再试")

    async def _daily_car_text(self, event: AstrMessageEvent) -> str:
        """返回玩家当天固定座驾；抽取记录保存在积分插件数据库。"""
        if not self.daily_car_pool:
            return "🚗 车池为空，请联系管理员添加车辆"
        user_id = str(event.get_sender_id()).strip()
        if not user_id:
            return "🚗 无法获取用户 ID，今日座驾抽取失败"
        today = datetime.now(TZ).date().isoformat()

        async with self._daily_car_lock:
            async def fn(session):
                row = (await session.execute(text(
                    "SELECT car_name FROM daily_cars WHERE user_id=:u AND date=:d"
                ), {"u": user_id, "d": today})).first()
                car = str(row[0]) if row else random.choice(self.daily_car_pool)
                if not row:
                    await session.execute(text(
                        "INSERT INTO daily_cars(user_id, date, car_name) VALUES(:u, :d, :c)"
                    ), {"u": user_id, "d": today, "c": car})
                return True, "ok", car

            ok, msg, car = await self._tx(fn)
        if not ok:
            return f"🚗 今日座驾抽取失败：{msg}"
        try:
            user_name = event.get_sender_name() or user_id
        except Exception:
            user_name = user_id
        return self.daily_car_template.format(
            user_name=user_name,
            car=self._format_car_entry(self._normalize_car_text(car)),
            date=today,
        )

    async def _ensure_user(self, session, user_id: str, user_name: str = ""):
        """确保用户存在，并在有新昵称时更新昵称。"""
        await session.execute(
            text("INSERT OR IGNORE INTO users(user_id, user_name) VALUES(:u, :n)"),
            {"u": user_id, "n": user_name or ""},
        )
        if user_name:
            await session.execute(
                text("UPDATE users SET user_name=:n WHERE user_id=:u"),
                {"u": user_id, "n": user_name},
            )

    @filter.event_message_type(EventMessageType.ALL)
    async def refresh_user_name(self, event: AstrMessageEvent):
        """玩家每次使用本插件时刷新 QQ 昵称。"""
        raw = str(event.get_message_str() or "").strip()
        if not USER_COMMAND_PATTERN.search(raw):
            return
        user_id = str(event.get_sender_id() or "").strip()
        if not user_id:
            return
        try:
            user_name = str(event.get_sender_name() or "").strip()
        except Exception:
            user_name = ""
        if not user_name:
            return

        async def fn(session):
            await self._ensure_user(session, user_id, user_name)
            return True, "ok", None

        await self._tx(fn)

    async def _balance(self, session, user_id: str) -> int:
        await self._ensure_user(session, user_id)
        row = (
            await session.execute(
                text("SELECT balance FROM users WHERE user_id=:u"), {"u": user_id}
            )
        ).first()
        return int(row[0]) if row else 0

    async def _add_points(
        self,
        session,
        user_id: str,
        amount: int,
        operation: str,
        earned: int | None = None,
        spent: int | None = None,
    ):
        """原子变更积分并写流水，必须在事务内调用。

        ``amount`` 是余额净变化；``earned`` 和 ``spent`` 用于准确统计总收入/总支出。
        例如转盘消费 100、返还 120 时，余额变化是 +20，但收入应记 120、支出应记 100。
        负数变更使用带余额条件的 UPDATE，即使并发扣分也不会透支。
        """
        if not user_id:
            raise _BizError("用户 ID 不能为空喵~")
        if not isinstance(amount, int):
            raise _BizError("积分数量必须是整数喵~")
        if amount == 0 and not (earned or spent):
            return
        await self._ensure_user(session, user_id)
        earned = max(amount, 0) if earned is None else max(int(earned), 0)
        spent = max(-amount, 0) if spent is None else max(int(spent), 0)
        if amount < 0:
            result = await session.execute(
                text(
                    "UPDATE users SET balance=balance+:a, total_earned=total_earned+:e, "
                    "total_spent=total_spent+:s "
                    "WHERE user_id=:u AND balance+:a >= 0"
                ),
                {"a": amount, "e": earned, "s": spent, "u": user_id},
            )
            if result.rowcount != 1:
                raise _BizError(
                    f"积分不足喵~ 当前积分：{await self._balance(session, user_id)}"
                )
        else:
            await session.execute(
                text(
                    "UPDATE users SET balance=balance+:a, total_earned=total_earned+:e, "
                    "total_spent=total_spent+:s WHERE user_id=:u"
                ),
                {"a": amount, "e": earned, "s": spent, "u": user_id},
            )
        # 记录完整流水：收入、支出、净变动和变动后的余额。
        current_balance = await self._balance(session, user_id)
        await session.execute(
            text(
                "INSERT INTO point_transactions("
                "user_id, amount, operation, earned, spent, balance_after, create_time) "
                "VALUES(:u, :a, :op, :e, :s, :b, :t)"
            ),
            {"u": user_id, "a": amount, "op": operation,
             "e": earned, "s": spent, "b": current_balance, "t": time.time()},
        )

    async def _check_spend_reward(self, session, user_id: str, group_id: str = None):
        """检查用户累计消费是否达标，发送提醒（必须在事务内调用）"""
        row = (
            await session.execute(
                text("SELECT total_spent, reward_reminded FROM users WHERE user_id=:u"),
                {"u": user_id}
            )
        ).first()
        if not row:
            return
        total_spent, reminded = int(row[0] or 0), int(row[1] or 0)
        if total_spent >= self.SPEND_REWARD_THRESHOLD and reminded == 0:
            await session.execute(
                text("UPDATE users SET reward_reminded=1 WHERE user_id=:u"),
                {"u": user_id}
            )
            # 提醒消息在事务外发送（下方调用处理）
            return True
        return False

    async def _enforce_cooldown(self, session, user_id: str, seconds: int = None) -> float:
        """指令冷却：3 秒内重复指令返回剩余秒数（>0 表示被拦截）。必须在事务内调用"""
        seconds = seconds or self.COMMAND_COOLDOWN
        row = (
            await session.execute(
                text("SELECT last_command_time FROM cooldown WHERE user_id=:u"),
                {"u": user_id},
            )
        ).first()
        now = time.time()
        if row and row[0] is not None:
            last = float(row[0])
            if now - last < seconds:
                return round(seconds - (now - last), 1)
        await session.execute(
            text(
                "INSERT INTO cooldown(user_id, last_command_time) VALUES(:u, :t) "
                "ON CONFLICT(user_id) DO UPDATE SET last_command_time=:t"
            ),
            {"u": user_id, "t": now},
        )
        return 0.0

    # ---------- 群黑白名单 ----------
    async def _get_config_value(self, session, key: str, default: str = "") -> str:
        row = (
            await session.execute(
                text("SELECT value FROM plugin_config WHERE key=:k"), {"k": key}
            )
        ).first()
        return row[0] if row else default

    async def _set_config_value(self, session, key: str, value: str):
        await session.execute(
            text(
                "INSERT INTO plugin_config(key, value) VALUES(:k, :v) "
                "ON CONFLICT(key) DO UPDATE SET value=:v"
            ),
            {"k": key, "v": value},
        )

    async def _group_allowed(self, session, group_id: str) -> tuple[bool, str, int]:
        """检查群是否允许玩积分游戏，返回 (是否允许, 当前模式, 本群是否开启)。
        白名单模式：默认全关，仅开启的群可玩；黑名单模式：默认全开，仅拉黑的群不可玩。
        """
        if not group_id:  # 私聊默认允许
            return True, "", 1
        mode = await self._get_config_value(session, "group_mode", self.DEFAULT_GROUP_MODE)
        row = (
            await session.execute(
                text("SELECT enabled FROM group_settings WHERE group_id=:g"),
                {"g": group_id},
            )
        ).first()
        enabled = int(row[0]) if row else 0
        if mode == "whitelist":
            return enabled == 1, mode, enabled
        # 黑名单模式：有记录且 enabled=0 才拦截
        banned = row is not None and enabled == 0
        return not banned, mode, enabled

    # ---------- 生命周期 ----------
    async def _init_db_tables(self):
        """创建所有数据表并迁移旧版流水字段（幂等）"""
        async with self._session() as session:
            async with session.begin():
                for ddl in self.TABLE_DDL:
                    await session.execute(text(ddl))

                # 旧版数据库没有昵称和流水明细字段，启动时补齐并回填可推导数据。
                group_columns = {
                    str(row[1]) for row in (await session.execute(text("PRAGMA table_info(group_settings)"))).all()
                }
                if "platform_id" not in group_columns:
                    await session.execute(text("ALTER TABLE group_settings ADD COLUMN platform_id TEXT DEFAULT ''"))

                user_columns = {
                    str(row[1]) for row in (await session.execute(text("PRAGMA table_info(users)"))).all()
                }
                if "user_name" not in user_columns:
                    await session.execute(text("ALTER TABLE users ADD COLUMN user_name TEXT DEFAULT ''"))
                if "reward_reminded" not in user_columns:
                    await session.execute(text("ALTER TABLE users ADD COLUMN reward_reminded INTEGER DEFAULT 0"))
                if "gift_redeemed" not in user_columns:
                    # 一次性消费兑换礼品：已兑换次数
                    await session.execute(text("ALTER TABLE users ADD COLUMN gift_redeemed INTEGER DEFAULT 0"))

                transaction_columns = {
                    str(row[1]) for row in (await session.execute(text("PRAGMA table_info(point_transactions)"))).all()
                }
                missing_transaction_columns = []
                for column, definition in (
                    ("earned", "INTEGER DEFAULT 0"),
                    ("spent", "INTEGER DEFAULT 0"),
                    ("balance_after", "INTEGER DEFAULT 0"),
                ):
                    if column not in transaction_columns:
                        await session.execute(text(f"ALTER TABLE point_transactions ADD COLUMN {column} {definition}"))
                        missing_transaction_columns.append(column)
                if missing_transaction_columns:
                    running = {}
                    old_rows = (await session.execute(text(
                        "SELECT id, user_id, amount FROM point_transactions ORDER BY user_id, id"
                    ))).all()
                    for row in old_rows:
                        uid = str(row[1])
                        amount = int(row[2] or 0)
                        running[uid] = running.get(uid, 0) + amount
                        await session.execute(text(
                            "UPDATE point_transactions SET earned=:e, spent=:s, balance_after=:b WHERE id=:i"
                        ), {"e": max(amount, 0), "s": max(-amount, 0),
                            "b": running[uid], "i": row[0]})

                # BOSS 初始行
                row = (await session.execute(text("SELECT id FROM boss WHERE id=1"))).first()
                if not row:
                    await session.execute(
                        text(
                            "INSERT INTO boss(id, current_hp, reset_date, pool) "
                            "VALUES(1, :hp, :d, :p)"
                        ),
                        {"hp": self.BOSS_MAX_HP, "d": date.today().isoformat(),
                         "p": self.BOSS_POOL},
                    )
                # 配置页群号黑白名单合并进群设置（每次加载生效，可覆盖指令设置）
                wl = self.config.get("group_whitelist", [])
                bl = self.config.get("group_blacklist", [])
                if isinstance(wl, str):
                    wl = [x for x in wl.replace("，", ",").split(",") if x.strip()]
                if isinstance(bl, str):
                    bl = [x for x in bl.replace("，", ",").split(",") if x.strip()]
                now = time.time()
                for g in wl:
                    gid = str(g).strip()
                    if not gid:
                        continue
                    await session.execute(
                        text(
                            "INSERT INTO group_settings(group_id, enabled, updated_at) VALUES(:g, 1, :t) "
                            "ON CONFLICT(group_id) DO UPDATE SET enabled=1, updated_at=:t"
                        ),
                        {"g": gid, "t": now},
                    )
                for g in bl:
                    gid = str(g).strip()
                    if not gid:
                        continue
                    await session.execute(
                        text(
                            "INSERT INTO group_settings(group_id, enabled, updated_at) VALUES(:g, 0, :t) "
                            "ON CONFLICT(group_id) DO UPDATE SET enabled=0, updated_at=:t"
                        ),
                        {"g": gid, "t": now},
                    )

    async def initialize(self):
        """插件激活时：建表、启动定时任务、注册 WebUI 接口"""
        await self._init_db_tables()
        # 恢复今日群活跃统计（插件更新/重启不丢数）
        await self._load_activity_counts()
        # 2. 定时任务
        self._scheduler = AsyncIOScheduler(timezone=TZ)
        self._scheduler.add_job(
            self._boss_daily_reset, CronTrigger(hour=self.BOSS_RESET_HOUR, minute=self.BOSS_RESET_MINUTE, timezone=TZ),
            id="boss_daily_reset", replace_existing=True,
        )
        self._scheduler.add_job(
            self._lottery_draw, CronTrigger(hour=self.LOTTERY_DRAW_HOUR, minute=self.LOTTERY_DRAW_MINUTE, timezone=TZ),
            id="lottery_draw", replace_existing=True,
        )
        self._scheduler.add_job(
            self._maintenance, IntervalTrigger(seconds=60, timezone=TZ),
            id="point_games_maintenance", replace_existing=True,
        )
        self._scheduler.add_job(
            self._settle_activity_rewards,
            CronTrigger(hour=self.ACTIVITY_SETTLE_HOUR, minute=self.ACTIVITY_SETTLE_MINUTE, timezone=TZ),
            id="point_games_activity_rewards", replace_existing=True,
        )
        self._scheduler.add_job(
            self._broadcast_leaderboard,
            CronTrigger(hour=self.LEADERBOARD_BROADCAST_HOUR, minute=self.LEADERBOARD_BROADCAST_MINUTE, timezone=TZ),
            id="point_games_leaderboard_broadcast", replace_existing=True,
        )
        # 钓鱼系统：每 30 分钟判定一次挂机鱼竿 + 每天凌晨重置今日统计
        self._scheduler.add_job(
            self._fishing_check,
            IntervalTrigger(minutes=self.CHECK_INTERVAL, timezone=TZ),
            id="fishing_check", replace_existing=True,
        )
        self._scheduler.add_job(
            self._fishing_daily_reset,
            CronTrigger(hour=self.FISHING_RESET_HOUR, minute=self.FISHING_RESET_MINUTE, timezone=TZ),
            id="fishing_daily_reset", replace_existing=True,
        )
        # 每日自动收税：凌晨 0 点对余额达标的用户扣 0.1%，流入手续费接收账户
        self._scheduler.add_job(
            self._daily_tax,
            CronTrigger(hour=0, minute=0, timezone=TZ),
            id="point_games_daily_tax", replace_existing=True,
        )
        # 银行日结：凌晨 0 点发放活期利息 + 管理员额外收益
        self._scheduler.add_job(
            self._daily_bank_settlement,
            CronTrigger(hour=0, minute=0, timezone=TZ),
            id="point_games_bank_settlement", replace_existing=True,
        )
        # 银行流水报告：每晚配置的时间发送当日银行+系统流水
        self._scheduler.add_job(
            self._daily_bank_report,
            CronTrigger(hour=self.BANK_REPORT_TIME[0], minute=self.BANK_REPORT_TIME[1], timezone=TZ),
            id="point_games_bank_report", replace_existing=True,
        )
        self._scheduler.start()
        # 3. 注册 WebUI
        self._register_web_apis()

    async def terminate(self):
        """插件卸载时：停止定时任务"""
        if self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
            self._scheduler = None
        self._uc_jobs.clear()

    # ============================================================
    #  定时任务
    # ============================================================
    async def _boss_daily_reset(self):
        """每天凌晨 0 点重置 BOSS（防御性：/攻击 时也会按 reset_date 惰性重置）"""
        today = date.today().isoformat()

        async def fn(session):
            row = (
                await session.execute(text("SELECT reset_date FROM boss WHERE id=1"))
            ).first()
            if row and row[0] == today:
                return True, "无需重置", None
            await session.execute(
                text("UPDATE boss SET current_hp=:hp, pool=:p, reset_date=:d WHERE id=1"),
                {"hp": self.BOSS_MAX_HP, "p": self.BOSS_POOL, "d": today},
            )
            await session.execute(text("DELETE FROM boss_damage"))
            return True, "BOSS 已重置", None

        await self._tx(fn)

    async def _ensure_boss_reset(self, session) -> None:
        """在事务内惰性重置过期 BOSS（内部调用，必须在事务中）"""
        today = date.today().isoformat()
        row = (
            await session.execute(text("SELECT reset_date FROM boss WHERE id=1"))
        ).first()
        if row and row[0] == today:
            return
        await session.execute(
            text("UPDATE boss SET current_hp=:hp, pool=:p, reset_date=:d WHERE id=1"),
            {"hp": self.BOSS_MAX_HP, "p": self.BOSS_POOL, "d": today},
        )
        await session.execute(text("DELETE FROM boss_damage"))

    async def _lottery_draw(self):
        """每天 20:00 大乐透开奖并广播"""
        today = date.today().isoformat()

        async def fn(session):
            tickets = (
                await session.execute(
                    text("SELECT * FROM lottery WHERE period=:p"), {"p": today}
                )
            ).all()
            if not tickets:
                return False, "今日无人购买彩票，跳过开奖", None
            # 奖池 = 当日购买总额 + 保底 + 上期结转
            bought = sum(int(t.cost or 0) for t in tickets)
            carry = 0
            prev = (date.today() - timedelta(days=1)).isoformat()
            c_row = (
                await session.execute(
                    text("SELECT pool FROM lottery_pool WHERE period=:p"), {"p": prev}
                )
            ).first()
            if c_row:
                carry = int(c_row[0])
            pool = bought + self.LOTTERY_BASE_POOL + carry
            # 生成开奖号码（1-100 选 5 个）
            winning = sorted(random.sample(range(1, 101), 5))
            # 计算各票命中数
            hits: list[tuple] = []  # (user_id, numbers, count)
            for t in tickets:
                nums = json.loads(t.numbers)
                cnt = len(set(nums) & set(winning))
                hits.append((t.user_id, nums, cnt))
            # 最高档位优先：5 中 60%，4 中 30%，3 中 10%
            winners: dict[int, list[tuple]] = {}
            for uid, nums, cnt in hits:
                if cnt >= 3:
                    winners.setdefault(cnt, []).append((uid, nums))
            paid_any = False
            detail_lines = []
            if winners:
                for cnt in sorted(winners.keys(), reverse=True):
                    share = int(pool * self.LOTTERY_PRIZE[cnt])
                    if share <= 0:
                        continue
                    per = share // len(winners[cnt])
                    for uid, nums in winners[cnt]:
                        await self._add_points(session, uid, per, "彩票中奖")
                        paid_any = True
                        detail_lines.append((uid, cnt, per))
            if not paid_any:
                # 无人中奖：奖池累积到下一期
                nxt = (date.today() + timedelta(days=1)).isoformat()
                await session.execute(
                    text(
                        "INSERT INTO lottery_pool(period, pool) VALUES(:p, :v) "
                        "ON CONFLICT(period) DO UPDATE SET pool=lottery_pool.pool+:v"
                    ),
                    {"p": nxt, "v": pool},
                )
            # 记录本次开奖到 lottery_pool 当前期（供 /彩票奖池 展示已开奖）
            await session.execute(
                text(
                    "INSERT INTO lottery_pool(period, pool) VALUES(:p, :v) "
                    "ON CONFLICT(period) DO UPDATE SET pool=:v"
                ),
                {"p": today, "v": 0},
            )
            broadcast_chain = [AtAll(), Plain(
                f"🎰 大乐透开奖（{today}）\n"
                f"开奖号码：{' '.join(map(str, winning))}\n"
                f"本期奖池：{pool} 积分"
            )]
            for uid, cnt, per in detail_lines:
                broadcast_chain.extend([
                    Plain("\n"), At(qq=str(uid)),
                    Plain(f" 命中{cnt}个，奖金 {per} 积分"),
                ])
            if not detail_lines:
                broadcast_chain.append(Plain("\n很遗憾，无人中奖，奖池累计到明天喵~"))
            # 广播到当日所有购买过的群
            seen: set = set()
            for t in tickets:
                pid, gid = t.platform_id or "", t.group_id or ""
                if gid and (pid, gid) not in seen:
                    seen.add((pid, gid))
                    await self._send_group_chain(pid, gid, broadcast_chain)
            return True, "开奖完成", {"winning": winning, "pool": pool}

        await self._tx(fn)

    async def _broadcast_leaderboard(self):
        """每天向已开启玩法的群播报全服积分排行榜。"""
        async def fn(session):
            rows = (await session.execute(text(
                "SELECT user_id, user_name, balance FROM users "
                "ORDER BY balance DESC LIMIT 10"
            ))).all()
            groups = (await session.execute(text(
                "SELECT group_id, platform_id FROM group_settings WHERE enabled=1"
            ))).all()
            return True, "ok", (rows, groups)

        ok, _, data = await self._tx(fn)
        if not ok or not data:
            return
        rows, groups = data
        if not rows:
            broadcast_chain = [Plain("🏆 全服积分排行榜\n暂无玩家数据喵~")]
        else:
            medals = ["🥇", "🥈", "🥉"]
            broadcast_chain = [Plain("🏆 全服积分排行榜 TOP10")]
            for rank, row in enumerate(rows, 1):
                prefix = medals[rank - 1] if rank <= 3 else f"{rank}."
                name = row[1] or "未知玩家"
                broadcast_chain.extend([
                    Plain(f"\n{prefix} "),
                    At(qq=str(row[0])),
                    Plain(f" {name} —— {int(row[2])} 积分"),
                ])
        platform_ids = []
        try:
            manager = getattr(self.context, "platform_manager", None)
            if manager and hasattr(manager, "get_insts"):
                platform_ids = [str(p.meta().id) for p in manager.get_insts() if p.meta().id]
            elif manager and hasattr(manager, "platform_insts"):
                platform_ids = [str(p.meta().id) for p in manager.platform_insts if p.meta().id]
        except Exception:
            platform_ids = []
        for group_id, platform_id in groups:
            targets = [str(platform_id)] if platform_id else platform_ids
            for target_platform in targets:
                await self._send_group_chain(target_platform, str(group_id), broadcast_chain)

    async def _daily_tax(self):
        """每日凌晨 0 点自动收税：余额≥门槛的用户扣余额的 0.1%（向下取整），转入 fee_receiver。

        无需任何指令；fee_receiver 未配置时跳过并记录日志。收税完成后向所有
        已开启玩法的群发送汇总消息。
        """
        if not self.feature_flags.get("enable_tax", True):
            return
        if not self.FEE_RECEIVER:
            self.logger.warning("每日收税未执行：请在插件配置页设置 fee_receiver（或填写管理员QQ列表）")
            return
        tax_date = date.today().isoformat()

        async def fn(session):
            # 只捞余额达标的用户；逐个原子扣税（余额条件防并发透支）
            rows = (await session.execute(text(
                "SELECT user_id, balance FROM users WHERE balance >= :m"
            ), {"m": self.TAX_MIN_BALANCE})).all()
            total_tax = 0
            tax_count = 0
            for uid, balance in rows:
                tax = int(int(balance) * self.TAX_RATE)  # 税率向下取整；余额≥1000时必≥1
                if tax < 1:
                    continue
                # 扣税 + 流水（operation='tax'）
                await self._add_points(session, str(uid), -tax, "tax",
                                       earned=0, spent=tax)
                # 税款流入手续费接收账户（复用转账的 fee_receiver）
                await self._add_points(session, self.FEE_RECEIVER, tax, "tax_income",
                                       earned=tax, spent=0)
                # 税收记录
                await session.execute(text(
                    "INSERT INTO tax_records(user_id, amount, date) VALUES(:u, :a, :d)"
                ), {"u": str(uid), "a": tax, "d": tax_date})
                total_tax += tax
                tax_count += 1
            return True, "ok", (total_tax, tax_count)

        ok, _, data = await self._tx(fn)
        if not ok or not data or data[0] <= 0:
            return
        total_tax, tax_count = data
        broadcast_chain = [Plain(
            "📊 今日税收汇总\n"
            f"共收取 {total_tax} 积分\n"
            f"共 {tax_count} 人纳税\n"
            "已转入管理员账户"
        )]
        # 广播到所有已开启玩法的群（与排行榜播报同一群来源）
        try:
            async with self._session() as session:
                groups = (await session.execute(text(
                    "SELECT group_id, platform_id FROM group_settings WHERE enabled=1"
                ))).all()
        except Exception:
            groups = []
        platform_ids = []
        try:
            manager = getattr(self.context, "platform_manager", None)
            if manager and hasattr(manager, "get_insts"):
                platform_ids = [str(p.meta().id) for p in manager.get_insts() if p.meta().id]
            elif manager and hasattr(manager, "platform_insts"):
                platform_ids = [str(p.meta().id) for p in manager.platform_insts if p.meta().id]
        except Exception:
            platform_ids = []
        for group_id, platform_id in groups:
            if not group_id:
                continue
            targets = [str(platform_id)] if platform_id else platform_ids
            for target_platform in targets:
                try:
                    await self._send_group_chain(target_platform, str(group_id), broadcast_chain)
                except Exception:
                    self.logger.exception(f"收税汇总发送失败：{group_id}")

    async def _maintenance(self):
        """每分钟维护：清理超时闯关会话、超时卧底游戏、超时速算会话"""
        now = time.time()

        async def fn(session):
            # 闯关超时
            await session.execute(
                text("DELETE FROM quiz_sessions WHERE expire_time < :t"), {"t": now}
            )
            # 卧底游戏：30 分钟无操作视为超时结束
            stale = (
                await session.execute(
                    text("SELECT group_id FROM undercover_games WHERE status IN ('waiting','speech','voting') AND updated_at < :t"),
                    {"t": now - 1800},
                )
            ).all()
            for row in stale:
                gid = row[0]
                await session.execute(
                    text("DELETE FROM undercover_games WHERE group_id=:g"), {"g": gid}
                )
                self._cancel_uc_jobs(gid)
            # 速算挑战超时
            await session.execute(
                text("DELETE FROM math_challenges WHERE expire_time < :t"), {"t": now}
            )
            return True, "维护完成", None

        # 清理内存中的超时速算会话
        expired_users = [uid for uid, sess in self._math_sessions.items() if sess.get("expire", 0) < now]
        for uid in expired_users:
            self._math_sessions.pop(uid, None)

        await self._tx(fn)

    # ============================================================
    #  主动发消息工具（私聊发词 / 开奖广播）
    # ============================================================
    async def _send_to_session(self, platform_id: str, message_type, session_id: str,
                               chain: MessageChain):
        """通过平台会话主动发消息（尽力而为，失败仅记日志）"""
        if MessageSession is None:
            self.logger.warning("MessageSession 不可用，无法主动发消息")
            return False
        try:
            platform = self.context.get_platform_inst(platform_id)
            if platform is None:
                self.logger.warning(f"找不到平台实例 {platform_id}")
                return False
            sess = MessageSession(platform_id, message_type, session_id)
            await platform.send_by_session(sess, chain)
            return True
        except Exception as e:
            self.logger.warning(f"主动发消息失败({platform_id}): {e}")
            return False

    async def _send_to_group(self, platform_id: str, group_id: str, text_msg: str,
                             at_all: bool = False):
        chain_objs = []
        if at_all:
            chain_objs.append(AtAll())
        chain_objs.append(Plain(text_msg))
        await self._send_to_session(platform_id, _MessageType.GROUP_MESSAGE, group_id,
                                    MessageChain(chain_objs))

    async def _send_group_chain(self, platform_id: str, group_id: str, chain_objs):
        """向群发送消息链，支持真实 At 组件。"""
        await self._send_to_session(
            platform_id, _MessageType.GROUP_MESSAGE, group_id, MessageChain(chain_objs)
        )

    async def _send_private(self, platform_id: str, user_id: str, text_msg: str):
        await self._send_to_session(platform_id, _MessageType.FRIEND_MESSAGE, user_id,
                                    MessageChain([Plain(text_msg)]))

    # ============================================================
    #  群黑白名单指令
    # ============================================================
    @filter.command("本群玩法")
    @filter.permission_type(PermissionType.ADMIN)
    async def group_toggle(self, event: AstrMessageEvent):
        """/本群玩法 开|关 —— 群管理员开启/关闭本群积分游戏"""
        if event.is_private_chat():
            yield event.plain_result("本群玩法只能在群里设置喵~")
            return
        args = self._strip_command(event, "本群玩法")
        # 从参数中提取动作词（兼容 at 尾巴、多余文本、全角空格），取最后一个
        words = re.findall(r"开|关|开启|关闭|打开|on|off|1|0", args.lower())
        if not words:
            yield event.plain_result("用法：/本群玩法 开 或 /本群玩法 关喵~")
            return
        action = words[-1]
        group_id = event.get_group_id()
        enable = action in ("开", "开启", "打开", "on", "1")

        async def fn(session):
            await session.execute(
                text(
                    "INSERT INTO group_settings(group_id, enabled, updated_at, platform_id) VALUES(:g, :e, :t, :p) "
                    "ON CONFLICT(group_id) DO UPDATE SET enabled=:e, updated_at=:t, platform_id=:p"
                ),
                {"g": group_id, "e": 1 if enable else 0, "t": time.time(),
                 "p": str(event.get_platform_id() or "")},
            )
            return True, ("本群积分游戏已开启喵~" if enable else "本群积分游戏已关闭喵~"), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("玩法模式")
    @filter.permission_type(PermissionType.ADMIN)
    async def mode_set(self, event: AstrMessageEvent):
        """/玩法模式 白名单|黑名单 —— 全局模式（管理员）"""
        mode = self._strip_command(event, "玩法模式").lower()
        if mode in ("白名单", "whitelist"):
            real = "whitelist"
        elif mode in ("黑名单", "blacklist"):
            real = "blacklist"
        else:
            yield event.plain_result("用法：/玩法模式 白名单 或 /玩法模式 黑名单喵~")
            return
        desc = "白名单（默认全关，仅开启的群可玩）" if real == "whitelist" else "黑名单（默认全开，拉黑的群不可玩）"

        async def fn(session):
            await self._set_config_value(session, "group_mode", real)
            return True, f"全局模式已切换为：{desc}喵~", None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("本群状态")
    async def group_status(self, event: AstrMessageEvent):
        """/本群状态 —— 查看本群玩法状态与全局模式"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("私聊不受群黑白名单限制，随时可以玩喵~")
            return

        async def fn(session):
            allowed, mode, enabled = await self._group_allowed(session, group_id)
            mode_txt = "白名单" if mode == "whitelist" else "黑名单"
            status_txt = "✅ 已开启" if allowed else "🚫 已关闭/拉黑"
            return True, f"全局模式：{mode_txt}\n本群状态：{status_txt}\n（管理员可用 /本群玩法 开|关 调整）", None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    async def _check_group_gate(self, event: AstrMessageEvent, command: str = ""):
        """检查群门禁和单个玩法开关，私聊不受群门禁限制。"""
        if command:
            feature = self.FEATURE_COMMANDS.get(command)
            if feature and not self.feature_flags.get(feature[0], True):
                return False, f"{feature[1]}玩法已被管理员在配置页关闭喵~"
        group_id = event.get_group_id()
        if not group_id:
            return True, None
        async with self._session() as session:
            allowed, mode, enabled = await self._group_allowed(session, group_id)
        if not allowed:
            return False, "本群未开启积分游戏喵~ 管理员发送 /本群玩法 开 即可开启（私聊不受限制）"
        return True, None

    # ============================================================
    #  指令入口：积分游戏介绍
    # ============================================================
    @filter.command("帮助")
    async def intro(self, event: AstrMessageEvent):
        """/帮助 —— 玩法介绍与指令列表"""
        yield event.plain_result(self._help_text())

    def _help_text(self) -> str:
        """构建精简的帮助说明（v2.15.0 起指令不再需要 /积分 前缀）。"""
        return "\n".join([
            "🎮 积分游戏 v2.18.7",
            "所有指令直接发送，无需 /积分 前缀",
            "查询：/积分 或 /查询",
            "玩法：/转盘 [积分]｜/闯关｜/攻击｜/BOSS状态｜/BOSS排行",
            "转账：/转账 @群友 [积分]（私聊用QQ号，手续费10%）",
            "银行：/开户｜/存钱 [积分]｜/取钱 [积分]｜/我的银行（活期5%/天）",
            "彩票：/买彩票 [积分]｜/彩票奖池",
            "卧底：/卧底开始 [人数]｜/加入卧底｜/投票 @玩家｜/卧底结束",
            "炸弹：/炸弹开始｜/猜 [数字]（余额需满30）",
            "钓鱼：/买鱼竿｜/买鱼饵｜/挂机钓鱼｜/收鱼｜/卖鱼｜/鱼图鉴",
            "　　　/鱼竿列表｜/修鱼竿｜/钓鱼排行｜/钓鱼统计",
            "兑换：/兑换礼品（花费10000积分）",
            "签到：群发 签到 / jrzj / 今日座驾｜排行：/排行",
            "管理：/加积分 @玩家 数量｜/减积分 @玩家 数量",
            "　　　/清除数据 @玩家｜/初始化 @玩家",
            "群管理：/本群玩法 开|关｜/玩法模式 白名单|黑名单｜/本群状态",
            "帮助：/帮助",
        ])

    # ============================================================
    #  功能一：幸运转盘
    # ============================================================
    @filter.command("转盘")
    async def spin(self, event: AstrMessageEvent):
        """/转盘 [积分数量]"""
        ok_gate, msg_gate = await self._check_group_gate(event, "转盘")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()
        cost = self.SPIN_DEFAULT_COST
        args = self._strip_command(event, "转盘")
        if args:
            try:
                cost = int(args.split()[0])
                if cost <= 0:
                    raise ValueError
            except ValueError:
                yield event.plain_result("积分数量得是正整数喵~")
                return

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            bal = await self._balance(session, user_id)
            if bal < cost:
                raise _BizError(f"积分不足喵~ 需要 {cost} 积分，你只有 {bal} 积分")
            # 默认配置严格按 1-100 区间抽取；自定义权重使用加权抽取。
            emojis = ["💀", "😅", "😌", "🙂", "🎉", "🔥"]
            if sum(self.spin_weights) == 100:
                roll = random.randint(1, 100)
                cumulative = 0
                outcome_index = 0
                for i, weight in enumerate(self.spin_weights):
                    cumulative += weight
                    if roll <= cumulative:
                        outcome_index = i
                        break
                rate, emoji = self.spin_rates[outcome_index], emojis[outcome_index]
            else:
                outcome_index = random.choices(
                    range(len(self.spin_weights)), weights=self.spin_weights, k=1
                )[0]
                rate, emoji = self.spin_rates[outcome_index], emojis[outcome_index]
                roll = outcome_index + 1
            refund = int(cost * rate)
            net = refund - cost
            # 余额按净收益变化，但收入/支出分别统计，便于 WebUI 查看真实流水。
            await self._add_points(
                session, user_id, net, "幸运转盘",
                earned=refund, spent=cost,
            )
            new_bal = await self._balance(session, user_id)
            # 检查消费达标提醒
            should_remind = await self._check_spend_reward(session, user_id, event.get_group_id())
            if net >= 0:
                msg = f"{emoji} 转盘结果：{roll} 点！返还 {refund} 积分（净赚 +{net}）当前积分：{new_bal} 喵~"
            else:
                msg = f"{emoji} 转盘结果：{roll} 点！返还 {refund} 积分（亏损 {abs(net)}）当前积分：{new_bal} 喵~"
            return True, msg, should_remind

        ok, msg, should_remind = await self._tx(fn)
        yield event.plain_result(msg)
        # 事务外发送提醒（避免阻塞数据库）
        if ok and should_remind:
            group_id = event.get_group_id()
            if group_id:
                try:
                    yield event.plain_result(
                        f"[CQ:at,qq={user_id}] 🎉 累计消费达到 {self.SPEND_REWARD_THRESHOLD} 积分！\n"
                        f"发送 /兑换礼品 花费 {self.SPEND_REWARD_THRESHOLD} 积分即可兑换小礼品一份喵~"
                    )
                except Exception:
                    pass

    # ============================================================
    #  功能二：闯关答题
    # ============================================================
    @filter.command("闯关")
    async def quiz_start(self, event: AstrMessageEvent):
        """/闯关 —— 开始答题闯关"""
        ok_gate, msg_gate = await self._check_group_gate(event, "闯关")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            # 重开则清掉旧会话
            await session.execute(
                text("DELETE FROM quiz_sessions WHERE user_id=:u"), {"u": user_id}
            )
            q = self._pick_question([])
            data = {
                "q": q["q"], "options": q["options"], "answer": q["answer"],
                "difficulty": q["difficulty"], "used": [q["idx"]],
            }
            await session.execute(
                text(
                    "INSERT INTO quiz_sessions(user_id, question_index, streak, question_data, expire_time) "
                    "VALUES(:u, 0, 0, :d, :t)"
                ),
                {"u": user_id, "d": json.dumps(data, ensure_ascii=False),
                 "t": time.time() + self.QUIZ_TIMEOUT},
            )
            msg = self._format_question(q["q"], q["options"], 0)
            msg += f"\n⏰ 限时 {self.QUIZ_TIMEOUT} 秒，发送 A/B/C（或1/2/3）作答喵~"
            return True, msg, None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    def _pick_question(self, used: list[int]) -> dict:
        """从未用过的题目中随机抽一题，返回含 idx 的题目字典"""
        candidates = [i for i in range(len(QUESTION_BANK)) if i not in used]
        if not candidates:  # 全部答完，重新洗牌
            candidates = list(range(len(QUESTION_BANK)))
        idx = random.choice(candidates)
        q = dict(QUESTION_BANK[idx])
        q["idx"] = idx
        return q

    def _format_question(self, q: str, options: list, streak: int) -> str:
        lines = [f"❓ {q}"]
        labels = ["A", "B", "C"]
        for i, opt in enumerate(options):
            lines.append(f"{labels[i]}. {opt}")
        lines.append(f"🔥 当前连击：{streak}")
        return "\n".join(lines)

    @filter.event_message_type(EventMessageType.ALL)
    async def quiz_answer(self, event: AstrMessageEvent):
        """监听 A/B/C（或 1/2/3）作答闯关题目"""
        if not self.feature_flags.get("enable_quiz", True):
            return
        raw = event.get_message_str().strip()
        letter = raw.upper()
        mapping = {"A": 0, "B": 1, "C": 2, "1": 0, "2": 1, "3": 2}
        if letter not in mapping:
            return  # 与闯关无关，直接放行
        ok_gate, _ = await self._check_group_gate(event, "闯关")
        if not ok_gate:
            return
        user_id = event.get_sender_id()

        async def fn(session):
            row = (
                await session.execute(
                    text("SELECT streak, question_data, expire_time FROM quiz_sessions WHERE user_id=:u"),
                    {"u": user_id},
                )
            ).first()
            if not row:
                # 没有进行中的题目：静默放行，避免干扰正常聊天
                return True, "", None
            if time.time() > float(row[2]):
                await session.execute(
                    text("DELETE FROM quiz_sessions WHERE user_id=:u"), {"u": user_id}
                )
                raise _BizError("⏰ 答题超时，本局结束喵~ 发送 /闯关 再来一局")
            data = json.loads(row[1])
            streak = int(row[0])
            correct = mapping[letter] == int(data["answer"])
            if correct:
                streak += 1
                reward = int(data["difficulty"]) * 10
                bonus = 0
                if streak % self.QUIZ_STREAK_BONUS_EVERY == 0:
                    bonus = self.QUIZ_STREAK_BONUS
                total = reward + bonus
                await self._add_points(session, user_id, total, "闯关答题")
                if bonus:
                    msg = f"✅ 回答正确！+{reward} 积分，连击 {streak} 达成额外 +{bonus}！🎉\n"
                else:
                    msg = f"✅ 回答正确！+{reward} 积分（连击 {streak}）\n"
                # 出下一题
                used = data.get("used", [])
                nxt = self._pick_question(used)
                ndata = {
                    "q": nxt["q"], "options": nxt["options"], "answer": nxt["answer"],
                    "difficulty": nxt["difficulty"], "used": used + [nxt["idx"]],
                }
                await session.execute(
                    text(
                        "UPDATE quiz_sessions SET question_index=question_index+1, streak=:s, "
                        "question_data=:d, expire_time=:t WHERE user_id=:u"
                    ),
                    {"s": streak, "d": json.dumps(ndata, ensure_ascii=False),
                     "t": time.time() + self.QUIZ_TIMEOUT, "u": user_id},
                )
                msg += self._format_question(nxt["q"], nxt["options"], streak)
                msg += f"\n⏰ 限时 {self.QUIZ_TIMEOUT} 秒喵~"
            else:
                await self._add_points(session, user_id, -self.QUIZ_WRONG_PENALTY, "闯关答错")
                await session.execute(
                    text("DELETE FROM quiz_sessions WHERE user_id=:u"), {"u": user_id}
                )
                msg = (f"❌ 回答错误，扣 {self.QUIZ_WRONG_PENALTY} 积分，连击清零喵~\n"
                       f"正确答案是：{['A','B','C'][int(data['answer'])]}. {data['options'][int(data['answer'])]}\n"
                       f"发送 /闯关 再来一局吧~")
            return True, msg, None

        ok, msg, _ = await self._tx(fn)
        if ok and msg:
            yield event.plain_result(msg)

    # ============================================================
    #  功能三：BOSS 战
    # ============================================================
    @filter.command("攻击")
    async def boss_attack(self, event: AstrMessageEvent):
        """/攻击 —— 消耗5积分攻击BOSS"""
        ok_gate, msg_gate = await self._check_group_gate(event, "攻击")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            # 攻击专属 10 秒冷却（查最近一次攻击时间）
            last_row = (
                await session.execute(
                    text("SELECT MAX(attack_time) FROM boss_damage WHERE user_id=:u"),
                    {"u": user_id},
                )
            ).first()
            now = time.time()
            if last_row and last_row[0] is not None and now - float(last_row[0]) < self.ATTACK_COOLDOWN:
                left = round(self.ATTACK_COOLDOWN - (now - float(last_row[0])), 1)
                raise _BizError(f"攻击冷却中，请 {left} 秒后再试喵~")
            # 检查余额
            bal = await self._balance(session, user_id)
            if bal < self.ATTACK_COST:
                raise _BizError(f"积分不足喵~ 攻击需要 {self.ATTACK_COST} 积分，你只有 {bal} 积分")
            # 惰性重置过期 BOSS
            await self._ensure_boss_reset(session)
            # 扣费 + 记录伤害
            await self._add_points(session, user_id, -self.ATTACK_COST, "BOSS攻击")
            # 检查消费达标提醒
            should_remind = await self._check_spend_reward(session, user_id, event.get_group_id())
            damage = random.randint(self.ATTACK_DAMAGE_MIN, self.ATTACK_DAMAGE_MAX)
            await session.execute(
                text(
                    "INSERT INTO boss_damage(user_id, damage, attack_time) VALUES(:u, :d, :t)"
                ),
                {"u": user_id, "d": damage, "t": now},
            )
            row = (
                await session.execute(
                    text("SELECT current_hp, pool FROM boss WHERE id=1")
                )
            ).first()
            hp = int(row[0]) - damage
            if hp <= 0:
                # BOSS 死亡：按伤害比例分配积分池
                stats = (
                    await session.execute(
                        text(
                            "SELECT b.user_id, u.user_name, SUM(b.damage) AS dmg "
                            "FROM boss_damage b LEFT JOIN users u ON u.user_id=b.user_id "
                            "GROUP BY b.user_id, u.user_name ORDER BY dmg DESC"
                        )
                    )
                ).all()
                total_dmg = sum(int(s[2]) for s in stats)
                pool = int(row[1])
                shares = []
                for uid, user_name, dmg in stats:
                    share = int(pool * int(dmg) / total_dmg) if total_dmg else 0
                    if share > 0:
                        await self._add_points(session, uid, share, "BOSS击败分红")
                        shares.append((user_name or "未知玩家", share))
                # 重置 BOSS
                today = date.today().isoformat()
                await session.execute(
                    text("UPDATE boss SET current_hp=:hp, pool=:p, reset_date=:d WHERE id=1"),
                    {"hp": self.BOSS_MAX_HP, "p": self.BOSS_POOL, "d": today},
                )
                await session.execute(text("DELETE FROM boss_damage"))
                share_txt = "，".join(f"{u} +{s}" for u, s in shares[:5])
                return True, (
                    f"💥 BOSS 被击杀了！你造成了 {damage} 点致命伤害！\n"
                    f"🏆 分红结果：{share_txt}\n"
                    f"🔄 新 BOSS 已刷新（{self.BOSS_MAX_HP} 血，奖池 {self.BOSS_POOL}）"
                ), should_remind
            await session.execute(
                text("UPDATE boss SET current_hp=:hp WHERE id=1"), {"hp": hp}
            )
            return True, f"⚔️ 你对 BOSS 造成了 {damage} 点伤害！BOSS 剩余血量：{hp}/{self.BOSS_MAX_HP}", should_remind

        ok, msg, should_remind = await self._tx(fn)
        yield event.plain_result(msg)
        # 事务外发送提醒
        if ok and should_remind:
            group_id = event.get_group_id()
            if group_id:
                try:
                    yield event.plain_result(
                        f"[CQ:at,qq={user_id}] 🎉 累计消费达到 {self.SPEND_REWARD_THRESHOLD} 积分！\n"
                        f"发送 /兑换礼品 花费 {self.SPEND_REWARD_THRESHOLD} 积分即可兑换小礼品一份喵~"
                    )
                except Exception:
                    pass

    @filter.command("BOSS状态")
    async def boss_status(self, event: AstrMessageEvent):
        """/BOSS状态"""
        ok_gate, msg_gate = await self._check_group_gate(event, "BOSS状态")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return

        async def fn(session):
            await self._ensure_boss_reset(session)
            row = (
                await session.execute(
                    text("SELECT current_hp, pool FROM boss WHERE id=1")
                )
            ).first()
            hp = int(row[0])
            today_start = datetime.combine(date.today(), datetime.min.time()).timestamp()
            agg = (
                await session.execute(
                    text(
                        "SELECT COALESCE(SUM(damage),0), COUNT(DISTINCT user_id) "
                        "FROM boss_damage WHERE attack_time >= :t"
                    ),
                    {"t": today_start},
                )
            ).first()
            return True, (
                f"👹 BOSS 状态\n血量：{max(hp,0)}/{self.BOSS_MAX_HP}\n"
                f"今日总伤害：{int(agg[0])}\n参与人数：{int(agg[1])}\n"
                f"🎁 死亡奖池：{int(row[1])} 积分\n发送 /攻击 参战喵~"
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("BOSS排行")
    async def boss_rank(self, event: AstrMessageEvent):
        """/BOSS排行 —— 今日伤害前10"""
        ok_gate, msg_gate = await self._check_group_gate(event, "BOSS排行")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return

        async def fn(session):
            await self._ensure_boss_reset(session)
            today_start = datetime.combine(date.today(), datetime.min.time()).timestamp()
            rows = (
                await session.execute(
                    text(
                        "SELECT b.user_id, u.user_name, SUM(b.damage) AS dmg "
                        "FROM boss_damage b LEFT JOIN users u ON u.user_id=b.user_id "
                        "WHERE b.attack_time >= :t GROUP BY b.user_id, u.user_name "
                        "ORDER BY dmg DESC LIMIT 10"
                    ),
                    {"t": today_start},
                )
            ).all()
            if not rows:
                return True, "今天还没有人攻击 BOSS 喵~ 发送 /攻击 抢首刀！", None
            lines = ["👹 今日 BOSS 伤害排行 TOP10"]
            for i, r in enumerate(rows, 1):
                name = r[1] or "未知玩家"
                lines.append(f"{i}. {name} —— {int(r[2])} 伤害")
            return True, "\n".join(lines), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    # ============================================================
    #  功能四：大乐透
    # ============================================================
    @filter.command("买彩票", alias={"彩票"})
    async def lottery_buy(self, event: AstrMessageEvent):
        """/买彩票 [积分数量] —— 购买1注随机号码，每人每期限购10注"""
        ok_gate, msg_gate = await self._check_group_gate(event, "买彩票")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()
        cost = self.LOTTERY_DEFAULT_COST
        args = self._strip_command(event, "买彩票")
        if not args:
            args = self._strip_command(event, "彩票")
        if args:
            try:
                cost = int(args.split()[0])
                if cost <= 0:
                    raise ValueError
            except ValueError:
                yield event.plain_result("积分数量得是正整数喵~")
                return
        today = date.today().isoformat()
        platform_id = event.get_platform_id()
        group_id = event.get_group_id()

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            cnt = (
                await session.execute(
                    text("SELECT COUNT(*) FROM lottery WHERE user_id=:u AND period=:p"),
                    {"u": user_id, "p": today},
                )
            ).first()
            if int(cnt[0]) >= self.LOTTERY_LIMIT_PER_DAY:
                raise _BizError(f"每人每期限购 {self.LOTTERY_LIMIT_PER_DAY} 注喵~")
            bal = await self._balance(session, user_id)
            if bal < cost:
                raise _BizError(f"积分不足喵~ 需要 {cost} 积分，你只有 {bal} 积分")
            numbers = sorted(random.sample(range(1, 101), 5))
            await self._add_points(session, user_id, -cost, "购买彩票")
            # 检查消费达标提醒
            should_remind = await self._check_spend_reward(session, user_id, event.get_group_id())
            await session.execute(
                text(
                    "INSERT INTO lottery(user_id, numbers, cost, period, platform_id, group_id) "
                    "VALUES(:u, :n, :c, :p, :pid, :gid)"
                ),
                {"u": user_id, "n": json.dumps(numbers), "c": cost,
                 "p": today, "pid": platform_id, "gid": group_id},
            )
            return True, (
                f"🎰 购彩成功！你的号码：{' '.join(map(str, numbers))}\n"
                f"花费 {cost} 积分，今日已购 {int(cnt[0]) + 1}/{self.LOTTERY_LIMIT_PER_DAY} 注\n"
                f"⏰ 每日 20:00 开奖，祝好运喵~"
            ), should_remind

        ok, msg, should_remind = await self._tx(fn)
        yield event.plain_result(msg)
        # 事务外发送提醒
        if ok and should_remind:
            group_id = event.get_group_id()
            if group_id:
                try:
                    yield event.plain_result(
                        f"[CQ:at,qq={user_id}] 🎉 累计消费达到 {self.SPEND_REWARD_THRESHOLD} 积分！\n"
                        f"发送 /兑换礼品 花费 {self.SPEND_REWARD_THRESHOLD} 积分即可兑换小礼品一份喵~"
                    )
                except Exception:
                    pass

    @filter.command("彩票奖池")
    async def lottery_pool_status(self, event: AstrMessageEvent):
        """/彩票奖池"""
        ok_gate, msg_gate = await self._check_group_gate(event, "彩票奖池")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        today = date.today().isoformat()

        async def fn(session):
            bought = (
                await session.execute(
                    text("SELECT COALESCE(SUM(cost),0), COUNT(DISTINCT user_id) FROM lottery WHERE period=:p"),
                    {"p": today},
                )
            ).first()
            carry = 0
            prev = (date.today() - timedelta(days=1)).isoformat()
            c_row = (
                await session.execute(
                    text("SELECT pool FROM lottery_pool WHERE period=:p"), {"p": prev}
                )
            ).first()
            if c_row:
                carry = int(c_row[0])
            pool = int(bought[0]) + self.LOTTERY_BASE_POOL + carry
            return True, (
                f"🎰 大乐透奖池（{today}）\n"
                f"当前奖池：{pool} 积分（购买 {int(bought[0])} + 保底 {self.LOTTERY_BASE_POOL} + 上期结转 {carry}）\n"
                f"参与人数：{int(bought[1])}\n"
                f"⏰ 每日 20:00 开奖，发送 /买彩票 参与喵~"
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    # ============================================================
    #  功能五：谁是卧底（群聊）
    # ============================================================
    @filter.command("卧底开始")
    async def uc_start(self, event: AstrMessageEvent):
        """/卧底开始 [人数] —— 发起卧底游戏报名"""
        if event.is_private_chat():
            yield event.plain_result("卧底游戏需要在群里玩喵~")
            return
        ok_gate, msg_gate = await self._check_group_gate(event, "卧底开始")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        group_id = event.get_group_id()
        invoker = event.get_sender_id()
        platform_id = event.get_platform_id()
        target = self.UC_DEFAULT_PLAYERS
        args = self._strip_command(event, "卧底开始")
        if args:
            try:
                target = int(args.split()[0])
                if target < self.UC_MIN_PLAYERS or target > self.UC_MAX_PLAYERS:
                    raise ValueError
            except ValueError:
                yield event.plain_result(f"人数需要是 {self.UC_MIN_PLAYERS}-{self.UC_MAX_PLAYERS} 的整数喵~")
                return

        async def fn(session):
            remaining = await self._enforce_cooldown(session, invoker)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            exist = (
                await session.execute(
                    text("SELECT id FROM undercover_games WHERE group_id=:g AND status IN ('waiting','speech','voting')"),
                    {"g": group_id},
                )
            ).first()
            if exist:
                raise _BizError("本群已有进行中的卧底游戏喵~")
            votes = json.dumps({"target": target, "eliminated": [], "votes": {}}, ensure_ascii=False)
            await session.execute(
                text(
                    "INSERT INTO undercover_games(group_id, status, players, civilian_word, undercover_word, "
                    "undercover_id, votes, round, current_speaker_index, phase, platform_id, updated_at) "
                    "VALUES(:g, 'waiting', :p, '', '', '', :v, 1, 0, 'lobby', :pid, :t)"
                ),
                {"g": group_id, "p": json.dumps([invoker]), "v": votes,
                 "pid": platform_id, "t": time.time()},
            )
            # 报名超时自动取消
            job = self._scheduler.add_job(
                self._uc_lobby_timeout, "date",
                run_date=datetime.now(TZ) + timedelta(seconds=self.UC_LOBBY_SECONDS),
                id=f"uc_lobby_{group_id}", replace_existing=True,
                args=[group_id],
            )
            self._uc_jobs[f"lobby_{group_id}"] = job
            return True, (
                f"🕵️ 卧底游戏报名开始！目标 {target} 人（当前 1/{target}）\n"
                f"发送 /加入卧底 报名喵~ 报名满自动开局，{self.UC_LOBBY_SECONDS} 秒内未满则取消"
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("加入卧底")
    async def uc_join(self, event: AstrMessageEvent):
        """/加入卧底 —— 报名卧底游戏"""
        if event.is_private_chat():
            yield event.plain_result("卧底游戏需要在群里玩喵~")
            return
        ok_gate, msg_gate = await self._check_group_gate(event, "加入卧底")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        group_id = event.get_group_id()
        user_id = event.get_sender_id()

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            row = (
                await session.execute(
                    text("SELECT players, votes FROM undercover_games WHERE group_id=:g AND status='waiting'"),
                    {"g": group_id},
                )
            ).first()
            if not row:
                raise _BizError("本群没有等待中的卧底游戏喵~ 发送 /卧底开始 发起")
            players = json.loads(row[0])
            votes_data = json.loads(row[1])
            target = int(votes_data.get("target", self.UC_DEFAULT_PLAYERS))
            if user_id in players:
                raise _BizError("你已经报名啦喵~")
            if len(players) >= target:
                raise _BizError("报名已满，等待开局喵~")
            players.append(user_id)
            if len(players) >= target:
                # 满员自动开局
                await self._uc_launch(session, group_id, players, votes_data)
                job = self._uc_jobs.pop(f"lobby_{group_id}", None)
                if job:
                    try:
                        job.remove()
                    except Exception:
                        pass
                return True, "🕵️ 报名满员，卧底游戏开始！", None
            await session.execute(
                text("UPDATE undercover_games SET players=:p, updated_at=:t WHERE group_id=:g"),
                {"p": json.dumps(players), "t": time.time(), "g": group_id},
            )
            return True, f"✅ 报名成功！当前 {len(players)}/{target} 人喵~", None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    async def _uc_launch(self, session, group_id: str, players: list, votes_data: dict):
        """满员后正式开局：发词、宣布第一位发言人。必须在事务内调用"""
        pair = random.choice(WORD_PAIRS)
        undercover_id = random.choice(players)
        civilian_word, undercover_word = pair
        now = time.time()
        await session.execute(
            text(
                "UPDATE undercover_games SET status='speech', phase='speech', players=:p, "
                "civilian_word=:cw, undercover_word=:uw, undercover_id=:ui, "
                "votes=:v, round=1, current_speaker_index=0, updated_at=:t WHERE group_id=:g"
            ),
            {"p": json.dumps(players), "cw": civilian_word, "uw": undercover_word,
             "ui": undercover_id, "v": json.dumps(votes_data, ensure_ascii=False),
             "t": now, "g": group_id},
        )
        # 私聊发词（尽力而为，失败则公开提示）
        pid_row = (
            await session.execute(
                text("SELECT platform_id FROM undercover_games WHERE group_id=:g"), {"g": group_id}
            )
        ).first()
        platform_id = pid_row[0] if pid_row else ""
        for uid in players:
            word = undercover_word if uid == undercover_id else civilian_word
            ok_sent = await self._send_private(platform_id, uid, f"🕵️ 你的卧底词语是：【{word}】喵~ 别让卧底发现你！")
            if not ok_sent:
                await self._send_group_chain(platform_id, group_id, [
                    At(qq=str(uid)),
                    Plain(f" 私聊发词失败，你的词是：【{word}】（注意保密喵~）"),
                ])
        await self._uc_schedule_next(session, group_id)

    def _alive_players(self, players: list, eliminated: list) -> list:
        return [p for p in players if p not in eliminated]

    async def _uc_schedule_next(self, session, group_id: str):
        """安排下一个发言人（或进入投票）。必须在事务内调用，且调用前需读取最新游戏数据"""
        row = (
            await session.execute(
                text("SELECT players, votes, current_speaker_index, phase, status, round, platform_id FROM undercover_games WHERE group_id=:g"),
                {"g": group_id},
            )
        ).first()
        if not row or row[4] not in ("speech", "voting"):
            return
        players = json.loads(row[0])
        votes_data = json.loads(row[1])
        eliminated = votes_data.get("eliminated", [])
        alive = self._alive_players(players, eliminated)
        idx = int(row[2])
        phase = row[3]
        current_round = int(row[5])
        platform_id = row[6] or ""
        if phase == "speech":
            if idx >= len(alive):
                # 本轮发言结束 → 进入投票
                await session.execute(
                    text("UPDATE undercover_games SET phase='voting', updated_at=:t WHERE group_id=:g"),
                    {"t": time.time(), "g": group_id},
                )
                await self._send_to_group(platform_id, group_id,
                    "🗳️ 发言结束，进入投票阶段！发送 /投票 @某人 投出你怀疑的卧底"
                    f"（限时 {self.UC_VOTE_SECONDS} 秒）")
                # 投票超时自动计票
                job = self._scheduler.add_job(
                    self._uc_vote_timer, "date",
                    run_date=datetime.now(TZ) + timedelta(seconds=self.UC_VOTE_SECONDS),
                    id=f"uc_vote_{group_id}", replace_existing=True, args=[group_id],
                )
                self._uc_jobs[f"vote_{group_id}"] = job
            else:
                speaker = alive[idx]
                await session.execute(
                    text("UPDATE undercover_games SET current_speaker_index=:i, updated_at=:t WHERE group_id=:g"),
                    {"i": idx + 1, "t": time.time(), "g": group_id},
                )
                try:
                    await self._send_to_session(
                        platform_id, _MessageType.GROUP_MESSAGE, group_id,
                        MessageChain([
                            Plain(f"🎤 第 {current_round} 轮发言，轮到："),
                            At(qq=speaker),
                            Plain(f"（限时 {self.UC_SPEECH_SECONDS} 秒）"),
                        ]),
                    )
                except Exception:
                    pass
                job = self._scheduler.add_job(
                    self._uc_speech_timer, "date",
                    run_date=datetime.now(TZ) + timedelta(seconds=self.UC_SPEECH_SECONDS),
                    id=f"uc_speech_{group_id}", replace_existing=True, args=[group_id],
                )
                self._uc_jobs[f"speech_{group_id}"] = job

    async def _uc_speech_timer(self, group_id: str):
        """发言倒计时结束：轮到下一位或进入投票"""
        async def fn(session):
            row = (
                await session.execute(
                    text("SELECT status, phase FROM undercover_games WHERE group_id=:g"), {"g": group_id}
                )
            ).first()
            if not row or row[0] != "speech":
                return True, "跳过", None
            await self._uc_schedule_next(session, group_id)
            return True, "下一位", None

        await self._tx(fn)

    async def _uc_vote_timer(self, group_id: str):
        """投票倒计时结束：在事务中自动计票"""
        async def fn(session):
            await self._uc_process_votes(session, group_id)
            return True, "投票计时结束", None

        await self._tx(fn)
        self._uc_jobs.pop(f"vote_{group_id}", None)

    async def _uc_lobby_timeout(self, group_id: str):
        """报名超时自动取消"""
        async def fn(session):
            row = (
                await session.execute(
                    text("SELECT status, players, platform_id FROM undercover_games WHERE group_id=:g"),
                    {"g": group_id},
                )
            ).first()
            if not row or row[0] != "waiting":
                return True, "跳过", None
            players = json.loads(row[1])
            platform_id = row[2] or ""
            await session.execute(
                text("DELETE FROM undercover_games WHERE group_id=:g"), {"g": group_id}
            )
            await self._send_to_group(platform_id, group_id,
                f"🕵️ 卧底报名超时取消喵~（仅 {len(players)} 人报名）")
            return True, "已取消", None

        ok, msg, _ = await self._tx(fn)
        self._uc_jobs.pop(f"lobby_{group_id}", None)

    @filter.command("投票")
    async def uc_vote(self, event: AstrMessageEvent):
        """/投票 @某人 —— 投票阶段投出卧底"""
        if event.is_private_chat():
            yield event.plain_result("卧底游戏需要在群里玩喵~")
            return
        if not self.feature_flags.get("enable_undercover", True):
            yield event.plain_result("谁是卧底玩法已在配置页关闭喵~")
            return
        ok_gate, msg_gate = await self._check_group_gate(event, "投票")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        group_id = event.get_group_id()
        voter = event.get_sender_id()
        target = self._extract_at(event)
        if not target:
            yield event.plain_result("用法：/投票 @某人 喵~")
            return

        async def fn(session):
            remaining = await self._enforce_cooldown(session, voter)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            row = (
                await session.execute(
                    text("SELECT status, phase, players, votes FROM undercover_games WHERE group_id=:g"),
                    {"g": group_id},
                )
            ).first()
            if not row or row[0] not in ("speech", "voting"):
                raise _BizError("本群没有进行中的卧底游戏喵~")
            if row[1] != "voting":
                raise _BizError("现在不是投票阶段喵~ 等发言结束后再投")
            players = json.loads(row[2])
            votes_data = json.loads(row[3])
            eliminated = votes_data.get("eliminated", [])
            alive = self._alive_players(players, eliminated)
            if voter not in alive:
                raise _BizError("你已出局，不能投票喵~")
            if target not in alive:
                raise _BizError("投票对象不合法喵~（只能投还在场的玩家）")
            if target == voter:
                raise _BizError("不能投自己喵~")
            votes_data.setdefault("votes", {})[voter] = target
            await session.execute(
                text("UPDATE undercover_games SET votes=:v, updated_at=:t WHERE group_id=:g"),
                {"v": json.dumps(votes_data, ensure_ascii=False), "t": time.time(), "g": group_id},
            )
            voted = len(votes_data["votes"])
            if voted >= len(alive):
                await self._uc_process_votes(session, group_id)
                return True, "投票完毕，正在计票喵~", None
            return True, f"✅ 已投票（{voted}/{len(alive)}）喵~", None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    async def _uc_process_votes(self, session, group_id: str):
        """统计票数、淘汰最高票者、判定胜负、进入下一轮。必须在事务内调用"""
        row = (
            await session.execute(
                text("SELECT players, votes, undercover_id, round, phase, status, platform_id, civilian_word, undercover_word FROM undercover_games WHERE group_id=:g"),
                {"g": group_id},
            )
        ).first()
        if not row or row[5] != "voting":
            return
        players = json.loads(row[0])
        votes_data = json.loads(row[1])
        undercover_id = row[2]
        current_round = int(row[3])
        platform_id = row[6] or ""
        civilian_word = row[7] or ""
        undercover_word = row[8] or ""
        eliminated = votes_data.get("eliminated", [])
        alive = self._alive_players(players, eliminated)
        votes = votes_data.get("votes", {})
        # 计票
        tally: dict[str, int] = {}
        for v in votes.values():
            tally[v] = tally.get(v, 0) + 1
        max_votes = max(tally.values()) if tally else 0
        top = [k for k, v in tally.items() if v == max_votes] if max_votes > 0 else []
        if len(top) == 1:
            out = top[0]
            eliminated.append(out)
            votes_data["eliminated"] = eliminated
            votes_data["votes"] = {}
            if out == undercover_id:
                # 卧底被投出：平民获胜
                await session.execute(
                    text("DELETE FROM undercover_games WHERE group_id=:g"), {"g": group_id}
                )
                await self._send_to_group(platform_id, group_id,
                    f"🔍 卧底【{out}】被投出局！平民获胜！🎉\n"
                    f"卧底词：【{undercover_word}】 平民词：【{civilian_word}】")
                self._cancel_uc_jobs(group_id)
                return
            alive_after = self._alive_players(players, eliminated)
            if len(alive_after) <= 2:
                # 卧底活到最后：卧底获胜
                await session.execute(
                    text("DELETE FROM undercover_games WHERE group_id=:g"), {"g": group_id}
                )
                await self._send_to_group(platform_id, group_id,
                    f"🕵️ 场上只剩 {len(alive_after)} 人，卧底【{undercover_id}】存活到最后，卧底获胜！🎭\n"
                    f"卧底词：【{undercover_word}】 平民词：【{civilian_word}】")
                self._cancel_uc_jobs(group_id)
                return
            # 平民出局，进入下一轮发言
            await session.execute(
                text(
                    "UPDATE undercover_games SET votes=:v, round=round+1, current_speaker_index=0, "
                    "phase='speech', status='speech', updated_at=:t WHERE group_id=:g"
                ),
                {"v": json.dumps(votes_data, ensure_ascii=False), "t": time.time(), "g": group_id},
            )
            await self._send_to_group(platform_id, group_id,
                f"🚪 玩家【{out}】被投出局！场上还剩 {len(alive_after)} 人，进入第 {current_round + 1} 轮发言！")
            await self._uc_schedule_next(session, group_id)
        else:
            # 平票：无人出局
            votes_data["votes"] = {}
            await session.execute(
                text(
                    "UPDATE undercover_games SET votes=:v, round=round+1, current_speaker_index=0, "
                    "phase='speech', status='speech', updated_at=:t WHERE group_id=:g"
                ),
                {"v": json.dumps(votes_data, ensure_ascii=False), "t": time.time(), "g": group_id},
            )
            await self._send_to_group(platform_id, group_id,
                f"🤝 平票！本轮无人出局，进入第 {current_round + 1} 轮发言喵~")
            await self._uc_schedule_next(session, group_id)

    def _cancel_uc_jobs(self, group_id: str):
        for key in (f"speech_{group_id}", f"vote_{group_id}", f"lobby_{group_id}"):
            job = self._uc_jobs.pop(key, None)
            if job:
                try:
                    job.remove()
                except Exception:
                    pass

    @filter.command("卧底结束")
    @filter.permission_type(PermissionType.ADMIN)
    async def uc_end(self, event: AstrMessageEvent):
        """/卧底结束 —— 管理员强制结束"""
        if event.is_private_chat():
            yield event.plain_result("卧底游戏需要在群里玩喵~")
            return
        group_id = event.get_group_id()

        async def fn(session):
            row = (
                await session.execute(
                    text("SELECT id FROM undercover_games WHERE group_id=:g AND status IN ('waiting','speech','voting')"),
                    {"g": group_id},
                )
            ).first()
            if not row:
                raise _BizError("本群没有进行中的卧底游戏喵~")
            await session.execute(
                text("DELETE FROM undercover_games WHERE group_id=:g"), {"g": group_id}
            )
            self._cancel_uc_jobs(group_id)
            return True, "🕵️ 卧底游戏已强制结束喵~", None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    async def _get_group_member(self, event: AstrMessageEvent, user_id: str):
        """查询目标是否仍在当前群，返回成员信息或 None。"""
        try:
            group = await event.get_group(event.get_group_id())
            if group and group.members:
                target = str(user_id)
                for member in group.members:
                    if str(member.user_id) == target:
                        return member
        except Exception as exc:
            self.logger.warning(f"查询群成员失败: {exc}")
        return None

    def _extract_at(self, event: AstrMessageEvent) -> Optional[str]:
        """从消息中提取被 @ 的 QQ（兼容 At 组件与纯文本数字）"""
        try:
            for comp in event.get_messages():
                if isinstance(comp, At):
                    return str(comp.qq)
        except Exception:
            pass
        m = re.search(r"(\d{5,})", event.get_message_str())
        return m.group(1) if m else None

    def _strip_command(self, event: AstrMessageEvent, command: str) -> str:
        """从事件消息中提取指令参数。

        兼容不同 AstrBot 版本的 message_str 差异：命令词可能带/不带斜杠、
        消息可能带 @机器人 尾巴、可能含全角空格，统一清理后返回参数部分。
        """
        text = ""
        try:
            text = str(event.message_str or "")
        except Exception:
            text = ""
        if not text:
            try:
                text = str(event.get_message_str() or "")
            except Exception:
                text = ""
        if not text:
            try:
                parts = []
                for comp in event.get_messages():
                    t = getattr(comp, "get_text", None)
                    parts.append(t() if t else str(comp))
                text = " ".join(parts)
            except Exception:
                pass
        cmd = command.lstrip("/")
        variants = [command, cmd, "/" + cmd]
        # 兼容只保留子指令文本的事件对象；实际注册仍只接受 /前缀。
        if " " in cmd:
            child = cmd.split(" ", 1)[1]
            variants.extend([child, "/" + child])
        for variant in variants:
            if variant and variant in text:
                text = text.split(variant, 1)[1]
                break
        # 全角空格转半角，去掉首尾与连续空白
        return " ".join(text.replace("　", " ").split())

    # ============================================================
    #  功能六：掷骰比大小
    # ============================================================
    async def _dice_count(self, session, user_id: str, today: str) -> int:
        row = (await session.execute(text(
            "SELECT count FROM dice_records WHERE user_id=:u AND date=:d"
        ), {"u": user_id, "d": today})).first()
        return int(row[0]) if row else 0

    async def _increase_dice_count(self, session, user_id: str, today: str) -> None:
        await session.execute(text(
            "INSERT INTO dice_records(user_id, date, count) VALUES(:u, :d, 1) "
            "ON CONFLICT(user_id, date) DO UPDATE SET count=dice_records.count+1"
        ), {"u": user_id, "d": today})

    @filter.command("掷骰")
    async def dice_roll(self, event: AstrMessageEvent):
        """/掷骰 @群友 —— 与群友比大小，每日次数可在配置页调整。"""
        if event.is_private_chat():
            yield event.plain_result("掷骰只能在群里玩喵~")
            return
        ok_gate, msg_gate = await self._check_group_gate(event, "掷骰")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        challenger = str(event.get_sender_id()).strip()
        target = self._extract_at(event)
        if not target:
            yield event.plain_result("用法：/掷骰 @群友 喵~")
            return
        if target == challenger:
            yield event.plain_result("不能和自己掷骰喵~")
            return
        # 兼容 NapCat/OneBot：无需强依赖群成员查询接口，@ 到 QQ 即可参与。
        # 能取到群昵称则展示昵称，取不到也不阻断玩法。
        member = await self._get_group_member(event, target)
        target_name = str(getattr(member, "nickname", "") or "群友").strip()
        challenger_name = str(event.get_sender_name() or "你").strip()
        today = date.today().isoformat()

        async with self._dice_lock:
            async def fn(session):
                challenger_count = await self._dice_count(session, challenger, today)
                target_count = await self._dice_count(session, target, today)
                if challenger_count >= self.DICE_DAILY_LIMIT:
                    raise _BizError(f"你今天已经掷骰 {self.DICE_DAILY_LIMIT} 次啦喵~")
                if target_count >= self.DICE_DAILY_LIMIT:
                    raise _BizError(f"{target_name} 今天已经达到掷骰次数上限喵~")
                await self._ensure_user(session, challenger, challenger_name)
                await self._ensure_user(session, target, target_name)
                first = random.randint(1, 6)
                second = random.randint(1, 6)
                await self._increase_dice_count(session, challenger, today)
                await self._increase_dice_count(session, target, today)
                chain = [Plain(f"🎲 你掷出了 {first}，"), At(qq=target), Plain(f" {target_name} 掷出了 {second}\n")]
                if first > second:
                    await self._add_points(session, challenger, 10, "掷骰获胜")
                    chain.append(Plain("🎉 你赢了！获得10积分！"))
                elif first < second:
                    await self._add_points(session, target, 10, "掷骰获胜")
                    chain.extend([At(qq=target), Plain(f" 赢了！获得10积分！")])
                else:
                    await self._add_points(session, challenger, 5, "掷骰平局")
                    await self._add_points(session, target, 5, "掷骰平局")
                    chain.append(Plain("🤝 平局！各得5积分！"))
                return True, "ok", chain

            ok, msg, data = await self._tx(fn)
        if ok and data:
            # AstrBot 官方 chain_result 接收组件列表，不能再套一层 MessageChain。
            yield event.chain_result(data)
        else:
            yield event.plain_result(msg)

    # ============================================================
    #  功能：积分转账
    # ============================================================
    def _parse_transfer_args(self, event: AstrMessageEvent, args: list[str]):
        """解析转账参数，返回 (目标QQ, 金额, 是否显式@了人)。

        兼容两种目标写法：群聊 @张三（At 组件）和纯 QQ 号（私聊/群聊均可）。
        金额取参数中最后一个纯数字；目标取 At 组件优先，其次第一个 5 位以上数字。
        """
        at_qq = self._extract_at(event)
        nums = [a for a in args if a.isdigit()]
        amount = int(nums[-1]) if nums else None
        target = at_qq
        if not target and len(nums) >= 2:
            # 没有 At 组件时，第一个数字视为目标 QQ（金额取最后一个）
            target = nums[0]
        explicit_at = bool(at_qq)
        return target, amount, explicit_at

    @filter.command("转账")
    async def transfer_points(self, event: AstrMessageEvent):
        """/转账 @群友 或 QQ号 [积分] —— 转账积分给其他玩家，收取10%手续费。"""
        is_private = event.is_private_chat()
        args = self._strip_command(event, "转账").split()
        target, amount, explicit_at = self._parse_transfer_args(event, args)

        # 目标校验：群聊必须 @，私聊必须给 QQ 号
        if not target:
            if is_private:
                yield event.plain_result("❌ 请提供目标用户QQ号，如：/转账 123456 50")
            else:
                yield event.plain_result("❌ 请@要转账的群友，如：/转账 @张三 50")
            return
        sender = str(event.get_sender_id()).strip()
        if target == sender:
            yield event.plain_result("❌ 不能转账给自己！")
            return
        # 金额校验：1-5000 积分
        if amount is None or not (self.TRANSFER_MIN <= amount <= self.TRANSFER_MAX):
            yield event.plain_result("❌ 请输入有效的转账金额（1-5000积分）")
            return

        # 群聊时顺带查一下目标昵称（查不到也不阻断，兜底用 QQ 号）
        target_name = ""
        if not is_private:
            member = await self._get_group_member(event, target)
            if member:
                target_name = str(getattr(member, "nickname", "") or "").strip()

        fee = int(amount * self.TRANSFER_FEE_RATE)  # 手续费：10% 向下取整
        total = amount + fee

        async def fn(session):
            # 冷却检查：查本表最近一次转账时间（独立于全局指令冷却，互不影响）
            row = (await session.execute(text(
                "SELECT MAX(create_time) FROM transfer_records WHERE from_user=:u"
            ), {"u": sender})).first()
            if row and row[0] is not None:
                wait = self.TRANSFER_COOLDOWN - (time.time() - float(row[0]))
                if wait > 0:
                    raise _BizError(f"⏳ 操作太快，请等待 {int(wait) + 1} 秒后再试")
            # 每日次数检查：按北京时间当天 0 点起统计
            midnight = datetime.now(TZ).replace(
                hour=0, minute=0, second=0, microsecond=0
            ).timestamp()
            row = (await session.execute(text(
                "SELECT COUNT(*) FROM transfer_records "
                "WHERE from_user=:u AND create_time>=:t"
            ), {"u": sender, "t": midnight})).first()
            used = int(row[0]) if row else 0
            if used >= self.TRANSFER_DAILY_LIMIT:
                raise _BizError("❌ 今日转账次数已达上限（10次）")
            # 目标用户校验：私聊要求对方已在积分系统注册；群聊里对方是本群成员则自动建档
            # 注意：db_name 是 fn 内局部变量；直接对外层 target_name 赋值会让它变成
            # 局部变量（闭包陷阱），读取时触发 UnboundLocalError
            db_name = ""
            row = (await session.execute(text(
                "SELECT user_name FROM users WHERE user_id=:u"
            ), {"u": target})).first()
            if not row:
                if is_private:
                    raise _BizError("❌ 目标用户不存在")
                if not target_name:
                    raise _BizError("❌ 目标用户不存在")
                await self._ensure_user(session, target, target_name)
            else:
                db_name = str(row[0] or "").strip()
            # 余额校验：必须 >= 转账金额 + 手续费
            balance = await self._balance(session, sender)
            if balance < total:
                raise _BizError(
                    f"❌ 积分不足！本次转账需扣除 {total} 积分"
                    f"（转账{amount}+手续费{fee}），当前余额：{balance}积分"
                )
            # 转出方扣除 转账金额+手续费，收入记 0、支出记 total
            await self._add_points(session, sender, -total, "transfer_out",
                                   earned=0, spent=total)
            # 接收方到账 转账金额
            await self._add_points(session, target, amount, "transfer_in",
                                   earned=amount, spent=0)
            # 手续费流入管理员账户；未配置 fee_receiver 时直接回收
            if fee > 0:
                if self.FEE_RECEIVER:
                    await self._add_points(session, self.FEE_RECEIVER, fee, "fee_income",
                                           earned=fee, spent=0)
                    fee_note = f"💸 手续费：{fee}积分（10%已转入管理员账户）\n"
                else:
                    fee_note = f"💸 手续费：{fee}积分\n"
            else:
                fee_note = ""
            # 写转账记录（用北京时间时间戳，便于冷却/每日次数统计）
            await session.execute(text(
                "INSERT INTO transfer_records(from_user, to_user, amount, fee, total, create_time) "
                "VALUES(:f, :t, :a, :fee, :tot, :time)"
            ), {"f": sender, "t": target, "a": amount, "fee": fee,
                "tot": total, "time": time.time()})
            new_balance = await self._balance(session, sender)
            remaining = self.TRANSFER_DAILY_LIMIT - used - 1
            should_remind = await self._check_spend_reward(session, sender,
                                                           event.get_group_id())
            display_name = target_name or db_name or target
            if is_private:
                msg = (f"✅ 转账成功！用户 {display_name} 收到 {amount}积分\n"
                       f"{fee_note}"
                       f"你实际扣除：{total}积分\n"
                       f"当前余额：{new_balance}积分\n"
                       f"今日剩余转账次数：{remaining}次")
                chain = None
            else:
                # 群聊用真实 CQ 码（At 组件）@目标用户
                msg = (f"✅ 转账成功！@{display_name} 收到 {amount}积分\n"
                       f"{fee_note}"
                       f"你实际扣除：{total}积分\n"
                       f"当前余额：{new_balance}积分\n"
                       f"今日剩余转账次数：{remaining}次")
                chain = [Plain("✅ 转账成功！"), At(qq=target),
                         Plain(f" 收到 {amount}积分\n{fee_note}"
                               f"你实际扣除：{total}积分\n"
                               f"当前余额：{new_balance}积分\n"
                               f"今日剩余转账次数：{remaining}次")]
            return True, msg, (chain, should_remind)

        ok, msg, data = await self._tx(fn)
        if is_private:
            yield event.plain_result(msg)
        elif ok and data and data[0]:
            yield event.chain_result(data[0])
        else:
            yield event.plain_result(msg)
        # 事务外发送消费达标提醒（与其它玩法保持一致）
        if ok and data and data[1]:
            try:
                yield event.plain_result(
                    f"🎉 累计消费达到 {self.SPEND_REWARD_THRESHOLD} 积分！\n"
                    f"发送 /兑换礼品 花费 {self.SPEND_REWARD_THRESHOLD} 积分即可兑换小礼品一份喵~"
                )
            except Exception:
                pass

    # ============================================================
    #  功能：银行系统
    # ============================================================
    async def _get_bank(self, session, user_id: str):
        """查询银行账户（事务内调用），返回 (活期余额, 累计利息) 或 None。"""
        row = (await session.execute(text(
            "SELECT current_balance, total_interest FROM bank_accounts WHERE user_id=:u"
        ), {"u": user_id})).first()
        return row

    @filter.command("开户")
    async def bank_open(self, event: AstrMessageEvent):
        """/开户 —— 开通银行账户（免费），享受每日活期利息"""
        ok_gate, msg_gate = await self._check_group_gate(event, "开户")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = str(event.get_sender_id()).strip()

        async def fn(session):
            await self._enforce_cooldown(session, user_id)
            await self._ensure_user(session, user_id)
            if await self._get_bank(session, user_id):
                raise _BizError("🏦 你已经开过户啦，直接 /存钱 就行喵~")
            await session.execute(text(
                "INSERT INTO bank_accounts(user_id, current_balance, total_interest) "
                "VALUES(:u, 0, 0)"
            ), {"u": user_id})
            return True, (
                "🏦 银行开户成功！\n"
                f"活期利率：{self.CURRENT_INTEREST_RATE:.0%}/天\n"
                "每日结算自动到账"
            ), None

        _, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    def _parse_bank_amount(self, args: list) -> Optional[int]:
        """解析存/取金额：取第一个纯数字参数，无效返回 None。"""
        for tok in args:
            if tok.isdigit():
                return int(tok)
        return None

    @filter.command("存钱")
    async def bank_deposit(self, event: AstrMessageEvent):
        """/存钱 [积分] —— 将钱包积分存入银行活期账户"""
        ok_gate, msg_gate = await self._check_group_gate(event, "存钱")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = str(event.get_sender_id()).strip()
        args = self._strip_command(event, "存钱").split()
        amount = self._parse_bank_amount(args)
        if amount is None or amount <= 0:
            yield event.plain_result("❌ 请输入有效的存入金额，如：/存钱 100")
            return

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            if not await self._get_bank(session, user_id):
                raise _BizError("🏦 你还没有银行账户，先发送 /开户 开通喵~")
            # 钱包原子扣款（余额条件防透支），存入银行
            await self._add_points(session, user_id, -amount, "bank_deposit",
                                   earned=0, spent=amount)
            await session.execute(text(
                "UPDATE bank_accounts SET current_balance=current_balance+:a WHERE user_id=:u"
            ), {"a": amount, "u": user_id})
            # 银行流水：存款
            await session.execute(text(
                "INSERT INTO bank_transactions(user_id, type, amount, create_time) "
                "VALUES(:u, 'deposit', :a, :t)"
            ), {"u": user_id, "a": amount, "t": time.time()})
            bank = await self._get_bank(session, user_id)
            estimate = int(bank[0] * self.CURRENT_INTEREST_RATE)
            return True, (
                f"💰 存入 {amount} 积分到活期账户成功！\n"
                f"当前活期余额：{bank[0]}积分\n"
                f"预计每日收益：{estimate}积分"
            ), None

        _, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("取钱")
    async def bank_withdraw(self, event: AstrMessageEvent):
        """/取钱 [积分] —— 从银行活期账户取出积分到钱包"""
        ok_gate, msg_gate = await self._check_group_gate(event, "取钱")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = str(event.get_sender_id()).strip()
        args = self._strip_command(event, "取钱").split()
        amount = self._parse_bank_amount(args)
        if amount is None or amount <= 0:
            yield event.plain_result("❌ 请输入有效的取出金额，如：/取钱 100")
            return

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            bank = await self._get_bank(session, user_id)
            if not bank:
                raise _BizError("🏦 你还没有银行账户，先发送 /开户 开通喵~")
            if bank[0] < amount:
                raise _BizError(f"❌ 银行余额不足！当前活期余额：{bank[0]}积分")
            # 银行扣款（余额条件防并发超取），转入钱包
            result = await session.execute(text(
                "UPDATE bank_accounts SET current_balance=current_balance-:a "
                "WHERE user_id=:u AND current_balance-:a >= 0"
            ), {"a": amount, "u": user_id})
            if result.rowcount != 1:
                raise _BizError(f"❌ 银行余额不足！当前活期余额：{bank[0]}积分")
            await self._add_points(session, user_id, amount, "bank_withdraw",
                                   earned=amount, spent=0)
            # 银行流水：取款
            await session.execute(text(
                "INSERT INTO bank_transactions(user_id, type, amount, create_time) "
                "VALUES(:u, 'withdraw', :a, :t)"
            ), {"u": user_id, "a": amount, "t": time.time()})
            bank = await self._get_bank(session, user_id)
            estimate = int(bank[0] * self.CURRENT_INTEREST_RATE)
            return True, (
                f"💵 取出 {amount} 积分到钱包成功！\n"
                f"当前活期余额：{bank[0]}积分\n"
                f"预计每日收益：{estimate}积分"
            ), None

        _, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("我的银行")
    async def bank_overview(self, event: AstrMessageEvent):
        """/我的银行 —— 查看银行账户总览"""
        ok_gate, msg_gate = await self._check_group_gate(event, "我的银行")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = str(event.get_sender_id()).strip()

        async def fn(session):
            await self._enforce_cooldown(session, user_id)
            bank = await self._get_bank(session, user_id)
            if not bank:
                raise _BizError("🏦 你还没有银行账户，先发送 /开户 开通喵~")
            estimate = int(bank[0] * self.CURRENT_INTEREST_RATE)
            return True, (
                "🏦 银行账户总览\n"
                f"💳 活期余额：{bank[0]}积分\n"
                f"📈 今日活期收益：{estimate}积分\n"
                f"💰 累计利息：{bank[1]}积分"
            ), None

        _, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    async def _daily_bank_settlement(self):
        """每日凌晨 0 点银行结算：玩家活期利息 + 管理员额外收益（独立发放）。

        - 玩家利息 = 活期余额 × CURRENT_INTEREST_RATE（向下取整，全额到账钱包）
        - 管理员额外收益 = 每个账户活期余额 × ADMIN_EXTRA_RATE 的总和，流入 fee_receiver
        """
        if not self.feature_flags.get("enable_bank", True):
            return
        rate = self.CURRENT_INTEREST_RATE
        extra_rate = self.ADMIN_EXTRA_RATE
        receiver = self.FEE_RECEIVER

        async def fn(session):
            rows = (await session.execute(text(
                "SELECT user_id, current_balance FROM bank_accounts WHERE current_balance > 0"
            ))).all()
            total_interest = 0
            total_admin_extra = 0
            for uid, balance in rows:
                # 玩家利息：全额到账钱包，累计进 total_interest
                interest = int(int(balance) * rate)
                if interest > 0:
                    await self._add_points(session, str(uid), interest, "bank_interest",
                                           earned=interest, spent=0)
                    await session.execute(text(
                        "UPDATE bank_accounts SET total_interest=total_interest+:i "
                        "WHERE user_id=:u"
                    ), {"i": interest, "u": str(uid)})
                    # 银行流水：利息
                    await session.execute(text(
                        "INSERT INTO bank_transactions(user_id, type, amount, create_time) "
                        "VALUES(:u, 'interest', :a, :t)"
                    ), {"u": str(uid), "a": interest, "t": time.time()})
                    total_interest += interest
                # 管理员额外收益：独立发放，不影响玩家利息
                admin_extra = int(int(balance) * extra_rate)
                if admin_extra > 0:
                    total_admin_extra += admin_extra
            # 汇总一次性发放给手续费接收账户（与收税同源，缺省第一个管理员）
            if total_admin_extra > 0 and receiver:
                await self._add_points(session, receiver, total_admin_extra, "bank_admin_extra",
                                       earned=total_admin_extra, spent=0)
                # 银行流水：管理员额外收益（总额一条）
                await session.execute(text(
                    "INSERT INTO bank_transactions(user_id, type, amount, create_time) "
                    "VALUES(:u, 'admin_extra', :a, :t)"
                ), {"u": receiver, "a": total_admin_extra, "t": time.time()})
            return True, "ok", (total_interest, total_admin_extra if receiver else 0)

        ok, _, data = await self._tx(fn)
        if not ok or not data or (data[0] <= 0 and data[1] <= 0):
            return
        broadcast_chain = [Plain(
            "🏦 银行日结完成！\n"
            f"共发放玩家利息：{data[0]} 积分\n"
            f"管理员额外收益：{data[1]} 积分"
        )]
        # 广播到所有已开启玩法的群（与排行榜播报同一群来源）
        try:
            async with self._session() as session:
                groups = (await session.execute(text(
                    "SELECT group_id, platform_id FROM group_settings WHERE enabled=1"
                ))).all()
        except Exception:
            groups = []
        platform_ids = []
        try:
            manager = getattr(self.context, "platform_manager", None)
            if manager and hasattr(manager, "get_insts"):
                platform_ids = [str(p.meta().id) for p in manager.get_insts() if p.meta().id]
            elif manager and hasattr(manager, "platform_insts"):
                platform_ids = [str(p.meta().id) for p in manager.platform_insts if p.meta().id]
        except Exception:
            platform_ids = []
        for group_id, platform_id in groups:
            if not group_id:
                continue
            targets = [str(platform_id)] if platform_id else platform_ids
            for target_platform in targets:
                try:
                    await self._send_group_chain(target_platform, str(group_id), broadcast_chain)
                except Exception:
                    self.logger.exception(f"银行日结播报发送失败：{group_id}")

    async def _daily_bank_report(self):
        """每晚指定时间发送银行日结流水 + 系统总流水报告到配置的群聊。"""
        if not self.feature_flags.get("enable_bank", True):
            return
        if not self.BANK_REPORT_GROUP:
            return  # 未配置发送群聊则不发送
        # 统计窗口：北京时间今日 0 点 ~ 明日 0 点（银行流水与积分流水均存时间戳）
        day_start = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        t0, t1 = day_start.timestamp(), day_end.timestamp()
        today = day_start.date().isoformat()

        async def fn(session):
            # ===== 银行流水（bank_transactions 按类型汇总今日记录）=====
            bank_stats = {"deposit": (0, 0), "withdraw": (0, 0),
                          "interest": (0, 0), "admin_extra": (0, 0)}
            rows = (await session.execute(text(
                "SELECT type, COUNT(*), COALESCE(SUM(amount),0) FROM bank_transactions "
                "WHERE create_time >= :t0 AND create_time < :t1 GROUP BY type"
            ), {"t0": t0, "t1": t1})).all()
            for rtype, cnt, total in rows:
                if rtype in bank_stats:
                    bank_stats[rtype] = (int(cnt), int(total))
            # 当前银行总存款与开户数
            row = (await session.execute(text(
                "SELECT COALESCE(SUM(current_balance),0), COUNT(*) FROM bank_accounts"
            ))).first()
            total_bank, total_users = int(row[0]), int(row[1])
            # ===== 系统总流水（point_transactions 今日，剔除银行存取避免重复计入）=====
            row = (await session.execute(text(
                "SELECT COALESCE(SUM(amount),0) FROM point_transactions "
                "WHERE amount > 0 AND create_time >= :t0 AND create_time < :t1 "
                "AND operation != 'bank_withdraw'"
            ), {"t0": t0, "t1": t1})).first()
            total_income = int(row[0])
            row = (await session.execute(text(
                "SELECT COALESCE(SUM(-amount),0) FROM point_transactions "
                "WHERE amount < 0 AND create_time >= :t0 AND create_time < :t1 "
                "AND operation != 'bank_deposit'"
            ), {"t0": t0, "t1": t1})).first()
            total_expense = int(row[0])
            # 今日转账手续费（管理员 fee_income 流水）
            row = (await session.execute(text(
                "SELECT COALESCE(SUM(amount),0) FROM point_transactions "
                "WHERE operation='fee_income' AND create_time >= :t0 AND create_time < :t1"
            ), {"t0": t0, "t1": t1})).first()
            transfer_fee_total = int(row[0])
            # 今日税收（用户 tax 流水）
            row = (await session.execute(text(
                "SELECT COALESCE(SUM(-amount),0) FROM point_transactions "
                "WHERE operation='tax' AND create_time >= :t0 AND create_time < :t1"
            ), {"t0": t0, "t1": t1})).first()
            tax_total = int(row[0])
            # 系统总积分池 = 所有用户钱包余额 + 银行存款总和
            row = (await session.execute(text(
                "SELECT COALESCE(SUM(balance),0) FROM users"
            ))).first()
            total_user_balance = int(row[0])
            system_total_pool = total_user_balance + total_bank
            return True, "ok", {
                "deposit": bank_stats["deposit"], "withdraw": bank_stats["withdraw"],
                "interest": bank_stats["interest"], "admin_extra": bank_stats["admin_extra"],
                "total_bank": total_bank, "total_users": total_users,
                "income": total_income, "expense": total_expense,
                "fee": transfer_fee_total, "tax": tax_total,
                "pool": system_total_pool,
            }

        ok, _, data = await self._tx(fn)
        if not ok or not data:
            return
        dep_cnt, dep_total = data["deposit"]
        wd_cnt, wd_total = data["withdraw"]
        it_cnt, it_total = data["interest"]
        ae_cnt, ae_total = data["admin_extra"]
        net_flow = data["income"] - data["expense"]
        msg = (
            "📊 【银行日结流水】\n"
            f"日期：{today}\n"
            "─────────────\n"
            f"💳 今日存款：{dep_total} 积分（{dep_cnt}笔）\n"
            f"💸 今日取款：{wd_total} 积分（{wd_cnt}笔）\n"
            f"📈 今日发放利息：{it_total} 积分\n"
            f"💰 管理员额外收益：{ae_total} 积分\n"
            "─────────────\n"
            f"📊 当前银行总存款：{data['total_bank']} 积分\n"
            f"👥 银行总用户数：{data['total_users']} 人\n\n"
            "─────────────\n"
            "💰 【系统总流水】\n"
            f"📈 总收入：{data['income']} 积分（签到/闯关/速算/掷骰/活跃/炸弹等）\n"
            f"💸 总支出：{data['expense']} 积分（转盘/BOSS/大乐透/卧底/抽卡/转账等）\n"
            f"📊 净流通：{net_flow:+d} 积分\n"
            f"💳 转账手续费：{data['fee']} 积分\n"
            f"📊 税收：{data['tax']} 积分\n"
            "─────────────\n"
            f"📊 系统总积分池：{data['pool']} 积分"
        )
        broadcast_chain = [Plain(msg)]
        for group_id in self.BANK_REPORT_GROUP:
            try:
                await self._send_group_chain("", str(group_id), broadcast_chain)
            except Exception:
                self.logger.exception(f"银行流水报告发送失败：{group_id}")

    # ============================================================
    #  功能七：群活跃奖励
    # ============================================================
    async def _load_activity_counts(self):
        """启动时从数据库恢复今日发言统计，避免插件更新后活跃计数清零。"""
        today = datetime.now(TZ).date().isoformat()
        try:
            async with self._session() as session:
                rows = (await session.execute(text(
                    "SELECT group_key, user_id, user_name, count FROM activity_stats "
                    "WHERE date=:d"
                ), {"d": today})).all()
            for gk, uid, name, cnt in rows:
                bucket = self._activity_counts.setdefault(
                    str(gk), {"date": today, "users": {}}
                )
                bucket["users"][str(uid)] = {
                    "name": str(name or uid), "count": int(cnt or 0)
                }
            if rows:
                self.logger.info(f"已恢复 {len(rows)} 条今日群活跃统计")
        except Exception:
            self.logger.exception("恢复群活跃统计失败")

    async def _persist_activity(self, key: str, today: str, user_id: str, user_name: str):
        """把一次发言计数落库（失败不影响消息处理）。"""
        try:
            async with self._session() as session:
                async with session.begin():
                    await session.execute(text(
                        "INSERT INTO activity_stats(group_key, date, user_id, user_name, count) "
                        "VALUES(:k, :d, :u, :n, 1) "
                        "ON CONFLICT(group_key, date, user_id) DO UPDATE SET "
                        "count=activity_stats.count+1, user_name=:n"
                    ), {"k": key, "d": today, "u": user_id, "n": user_name})
        except Exception:
            self.logger.exception("群活跃统计落库失败")

    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def count_group_activity(self, event: AstrMessageEvent):
        """统计群聊发言，系统消息也按一条消息计数。"""
        group_id = str(event.get_group_id() or "").strip()
        user_id = str(event.get_sender_id() or "").strip()
        if not group_id or not user_id or user_id == str(event.get_self_id() or ""):
            return
        today = datetime.now(TZ).date().isoformat()
        key = f"{event.get_platform_id()}:{group_id}"
        user_name = str(event.get_sender_name() or user_id).strip()
        async with self._activity_lock:
            bucket = self._activity_counts.setdefault(key, {"date": today, "users": {}})
            if bucket["date"] != today:
                bucket["date"] = today
                bucket["users"] = {}
            entry = bucket["users"].setdefault(user_id, {"name": user_name, "count": 0})
            entry["name"] = user_name or entry["name"]
            entry["count"] += 1
        # 写透到数据库，插件重启/更新后可恢复
        await self._persist_activity(key, today, user_id, user_name)

    async def _settle_activity_rewards(self):
        """每天22:00按群结算发言前三名并清空统计。"""
        if not self.feature_flags.get("enable_activity", True):
            return  # 配置页关闭群活跃奖励，跳过结算
        today = datetime.now(TZ).date().isoformat()
        # 顺手清理过期日期的统计
        try:
            async with self._session() as session:
                async with session.begin():
                    await session.execute(text(
                        "DELETE FROM activity_stats WHERE date < :d"
                    ), {"d": today})
        except Exception:
            self.logger.exception("清理过期群活跃统计失败")
        async with self._activity_lock:
            snapshots = [(key, bucket) for key, bucket in self._activity_counts.items()
                         if bucket.get("date") == today and bucket.get("users")]
        for key, bucket in snapshots:
            platform_id, group_id = key.split(":", 1)
            ranking = sorted(bucket["users"].items(), key=lambda item: item[1]["count"], reverse=True)[:3]
            rewards = (50, 30, 10)

            async def fn(session):
                chain = [Plain("🔥 群活跃奖励结算")]
                for rank, ((user_id, info), reward) in enumerate(zip(ranking, rewards), 1):
                    await self._ensure_user(session, user_id, info["name"])
                    await self._add_points(session, user_id, reward, "群活跃第%d名" % rank)
                    chain.extend([
                        Plain(f"\n第{rank}名 "),
                        At(qq=str(user_id)),
                        Plain(f" {info['name']}：{info['count']} 条，+{reward} 积分"),
                    ])
                return True, "ok", chain

            ok, _, chain = await self._tx(fn)
            if ok and chain:
                await self._send_group_chain(platform_id, group_id, chain)
                async with self._activity_lock:
                    current = self._activity_counts.get(key)
                    if current is bucket:
                        current["users"] = {}
                # 同步清理数据库里该群今日统计
                try:
                    async with self._session() as session:
                        async with session.begin():
                            await session.execute(text(
                                "DELETE FROM activity_stats WHERE group_key=:k AND date=:d"
                            ), {"k": key, "d": today})
                except Exception:
                    self.logger.exception("清理群活跃统计失败")

    # ============================================================
    #  功能八：管理指令 / 签到 / 排行
    # ============================================================
    async def _grant_points(self, event: AstrMessageEvent, negative: bool):
        """/加积分|减积分 @用户 数量（仅配置页管理员QQ可用）"""
        sender = str(event.get_sender_id())
        if sender not in self.ADMIN_QQ:
            yield event.plain_result("仅配置的管理员可使用该指令喵~ 请在插件配置页「管理员QQ」中添加")
            return
        user_id = self._extract_at(event)
        cmd = "减积分" if negative else "加积分"
        command_names = [f"积分 {cmd}", cmd]
        if negative:
            command_names.insert(1, "积分 扣积分")
            command_names.append("扣积分")
        args = ""
        for command_name in command_names:
            args = self._strip_command(event, command_name)
            if args:
                break
        parts = args.split()
        amount = None
        # 目标 QQ 也可能是纯数字，因此数量取最后一个数字参数。
        for p in reversed(parts):
            if p.isdigit():
                amount = int(p)
                break
        if not user_id:
            yield event.plain_result(f"用法：/{cmd} @用户 数量 喵~")
            return
        if amount is None or amount <= 0:
            yield event.plain_result("数量需要是正整数喵~")
            return
        delta = -amount if negative else amount
        target = user_id

        async def fn(session):
            await self._ensure_user(session, target)
            await self._add_points(session, target, delta, "管理员加分" if delta > 0 else "管理员扣分")
            new_bal = await self._balance(session, target)
            return True, f"✅ 已给 {target} {'加上' if delta > 0 else '扣除'} {abs(delta)} 积分，当前积分：{new_bal} 喵~", None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("加积分")
    async def grant_add(self, event: AstrMessageEvent):
        async for result in self._grant_points(event, negative=False):
            yield result

    @filter.command("减积分", alias={"扣积分"})
    async def grant_sub(self, event: AstrMessageEvent):
        async for result in self._grant_points(event, negative=True):
            yield result

    async def _reset_user_data(self, event: AstrMessageEvent, initialize: bool):
        """清零指定玩家账户统计与积分流水。"""
        sender = str(event.get_sender_id())
        if sender not in self.ADMIN_QQ:
            yield event.plain_result("仅配置的管理员可使用该指令喵~ 请在插件配置页「管理员QQ」中添加")
            return
        target = self._extract_at(event)
        action = "初始化" if initialize else "清除数据"
        if not target:
            yield event.plain_result(f"用法：/{action} @玩家 喵~")
            return

        async def fn(session):
            exists = (await session.execute(
                text("SELECT user_id FROM users WHERE user_id=:u"), {"u": target}
            )).first()
            if not exists and not initialize:
                raise _BizError("玩家不存在，无法清除数据喵~")
            await self._ensure_user(session, target)
            await session.execute(text(
                "UPDATE users SET balance=0, total_earned=0, total_spent=0, "
                "sign_in_date=NULL, sign_in_streak=0 WHERE user_id=:u"
            ), {"u": target})
            await session.execute(
                text("DELETE FROM point_transactions WHERE user_id=:u"), {"u": target}
            )
            return True, f"✅ 已{action}玩家 {target} 的余额、累计积分、签到数据和流水喵~", None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("清除数据")
    async def clear_user_data(self, event: AstrMessageEvent):
        async for result in self._reset_user_data(event, initialize=False):
            yield result

    @filter.command("初始化")
    async def initialize_user_data(self, event: AstrMessageEvent):
        async for result in self._reset_user_data(event, initialize=True):
            yield result

    async def _show_points(self, event: AstrMessageEvent):
        """查询并返回个人积分账户。"""
        user_id = event.get_sender_id()

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            await self._ensure_user(session, user_id)
            row = (await session.execute(text(
                "SELECT user_name, balance, total_earned, total_spent, sign_in_streak "
                "FROM users WHERE user_id=:u"
            ), {"u": user_id})).first()
            name = row[0] or "未知玩家"
            msg = (
                f"💰 玩家：{name}\n"
                f"当前积分：{int(row[1])}\n"
                f"累计收入：{int(row[2])}\n"
                f"累计支出：{int(row[3])}\n"
                f"连续签到：{int(row[4])} 天"
            )
            # 附带银行账户信息（未开户不显示）
            bank = await self._get_bank(session, user_id)
            if bank:
                estimate = int(bank[0] * self.CURRENT_INTEREST_RATE)
                msg += f"\n💳 银行存款：{bank[0]}积分\n📈 今日活期收益：{estimate}积分"
            return True, msg, None

        ok, msg, _ = await self._tx(fn)
        return event.plain_result(msg)

    @filter.command("积分")
    @filter.custom_filter(_ExactPointsCommandFilter)
    async def points_root(self, event: AstrMessageEvent):
        """/—— 查询自己的积分账户"""
        yield await self._show_points(event)

    @filter.command("查询")
    async def points(self, event: AstrMessageEvent):
        """/查询 —— 查询自己的积分账户"""
        yield await self._show_points(event)

    async def _query_user_points(self, event: AstrMessageEvent):
        target_id = self._extract_at(event)
        if not target_id:
            yield event.plain_result("用法：/查积分 @玩家 喵~")
            return

        async def fn(session):
            row = (await session.execute(text(
                "SELECT user_name, balance, total_earned, total_spent, sign_in_streak "
                "FROM users WHERE user_id=:u"
            ), {"u": target_id})).first()
            if not row:
                raise _BizError("这个玩家还没有积分数据喵~")
            name = row[0] or "未知玩家"
            return True, (
                f"💰 玩家：{name}\n"
                f"当前积分：{int(row[1])}\n"
                f"累计收入：{int(row[2])}\n"
                f"累计支出：{int(row[3])}\n"
                f"连续签到：{int(row[4])} 天"
            ), None

        _, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("查积分", alias={"查"})
    async def query_other_points(self, event: AstrMessageEvent):
        """/查积分 @玩家 —— 查询其他玩家积分"""
        async for result in self._query_user_points(event):
            yield result

    @filter.command("排行")
    async def rank(self, event: AstrMessageEvent):
        """/排行 —— 全服积分排行榜 TOP10"""
        ok_gate, msg_gate = await self._check_group_gate(event, "排行")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            rows = (
                await session.execute(
                    text("SELECT user_id, user_name, balance FROM users ORDER BY balance DESC LIMIT 10")
                )
            ).all()
            if not rows:
                return True, "排行榜还空着呢，快去赚积分喵~", None
            lines = ["🏆 全服积分排行榜 TOP10"]
            medals = ["🥇", "🥈", "🥉"]
            for i, r in enumerate(rows, 1):
                prefix = medals[i - 1] if i <= 3 else f"{i}."
                name = r[1] or "未知玩家"
                lines.append(f"{prefix} {name} —— {int(r[2])} 积分")
            return True, "\n".join(lines), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    # ============================================================
    #  功能9：数字炸弹
    # ============================================================
    @filter.command("炸弹开始")
    async def bomb_start(self, event: AstrMessageEvent):
        """数字炸弹：群内开始游戏"""
        ok_gate, msg_gate = await self._check_group_gate(event, "炸弹开始")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("数字炸弹只能在群聊中玩喵~")
            return
        
        if group_id in self._bomb_games:
            yield event.plain_result("本群炸弹游戏进行中，请先结束当前游戏喵~")
            return

        # 积分门槛：低于 BOMB_MIN_BALANCE 不给玩（踩雷扣分可能为负）
        user_id = event.get_sender_id()
        async with self._session() as session:
            bal = await self._balance(session, user_id)
        if bal < self.BOMB_MIN_BALANCE:
            yield event.plain_result(
                f"积分不足 {self.BOMB_MIN_BALANCE}，不能玩炸弹喵~（当前积分：{bal}）"
            )
            return

        target = random.randint(self.BOMB_MIN, self.BOMB_MAX)
        self._bomb_games[group_id] = {
            "target": target,
            "min": self.BOMB_MIN,
            "max": self.BOMB_MAX,
            "participants": set(),
            "platform_id": event.get_platform_id(),
        }
        
        yield event.plain_result(
            f"💣 数字炸弹游戏开始！\n"
            f"范围：{self.BOMB_MIN}-{self.BOMB_MAX}\n"
            f"请发送 /猜 [数字] 进行猜测喵~"
        )

    @filter.command("猜")
    async def bomb_guess(self, event: AstrMessageEvent):
        """数字炸弹：猜数字"""
        ok_gate, msg_gate = await self._check_group_gate(event, "猜")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        
        group_id = event.get_group_id()
        if not group_id or group_id not in self._bomb_games:
            yield event.plain_result("本群还没有进行中的炸弹游戏喵~")
            return
        
        msg = event.get_message_str().strip()
        args = self._strip_command(event, "猜")
        if not args:
            yield event.plain_result("用法：/猜 [数字]")
            return

        try:
            guess = int(args.split()[0])
        except ValueError:
            yield event.plain_result("请输入有效的数字喵~")
            return

        game = self._bomb_games[group_id]
        user_id = event.get_sender_id()

        # 积分门槛：低于 BOMB_MIN_BALANCE 不给猜（踩雷会扣分）
        async with self._session() as session:
            bal = await self._balance(session, user_id)
        if bal < self.BOMB_MIN_BALANCE:
            yield event.plain_result(
                f"积分不足 {self.BOMB_MIN_BALANCE}，不能玩炸弹喵~（当前积分：{bal}）"
            )
            return

        # 记录参与者
        game["participants"].add(user_id)

        if guess < game["min"] or guess > game["max"]:
            yield event.plain_result(f"请在范围 {game['min']}-{game['max']} 内猜测喵~")
            return

        # 猜中炸弹
        if guess == game["target"]:
            participants = list(game["participants"])
            participants.remove(user_id)  # 移除踩雷者

            async def fn(session):
                # 扣除踩雷者积分
                await self._ensure_user(session, user_id)
                await self._add_points(session, user_id, -self.BOMB_PENALTY, f"数字炸弹踩雷")
                loser_balance = await self._balance(session, user_id)

                # 给其他参与者加分
                for pid in participants:
                    await self._ensure_user(session, pid)
                    await self._add_points(session, pid, self.BOMB_REWARD, f"数字炸弹获胜")

                return True, (loser_balance, participants), None

            # 兼容修复：事务结果可能在 msg 或 data 槽位，且避免解包数量不符崩溃
            # （修复 "too many values to unpack (expected 2)"）
            ok, tx_msg, tx_data = await self._tx(fn)
            payload = tx_data if tx_data is not None else tx_msg
            if not ok or not isinstance(payload, tuple) or len(payload) < 2:
                yield event.plain_result(
                    tx_msg if isinstance(tx_msg, str) and tx_msg else "数据库开小差了喵~"
                )
                return
            loser_balance, participants = payload[0], payload[1]
            
            result = MessageChain([
                Plain(f"💥 BOOM！"),
                At(user_id),
                Plain(f" 踩到炸弹了！\n"),
                Plain(f"扣除 {self.BOMB_PENALTY} 积分，当前余额：{loser_balance}\n"),
            ])
            
            if participants:
                result.extend([Plain(f"其他参与者各获得 {self.BOMB_REWARD} 积分：\n")])
                for i, pid in enumerate(participants):
                    if i > 0:
                        result.append(Plain("、"))
                    result.append(At(pid))
            
            yield event.message_result(result)
            
            # 清理游戏
            del self._bomb_games[group_id]
            return
        
        # 缩小范围
        if guess < game["target"]:
            game["min"] = guess + 1
            yield event.plain_result(f"⬆️ 小了！范围：{game['min']}-{game['max']}")
        else:
            game["max"] = guess - 1
            yield event.plain_result(f"⬇️ 大了！范围：{game['min']}-{game['max']}")

    @filter.command("炸弹结束")
    async def bomb_end(self, event: AstrMessageEvent):
        """数字炸弹：管理员强制结束"""
        if not await self._is_admin(event):
            yield event.plain_result("只有管理员可以强制结束游戏喵~")
            return
        
        group_id = event.get_group_id()
        if not group_id or group_id not in self._bomb_games:
            yield event.plain_result("本群没有进行中的炸弹游戏喵~")
            return
        
        del self._bomb_games[group_id]
        yield event.plain_result("数字炸弹游戏已结束喵~")

    # ============================================================
    #  功能10：速算挑战
    # ============================================================
    @filter.command("速算")
    async def math_challenge(self, event: AstrMessageEvent):
        """速算挑战：出题"""
        ok_gate, msg_gate = await self._check_group_gate(event, "速算")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        
        user_id = event.get_sender_id()
        today = date.today().isoformat()
        
        async def fn(session):
            # 检查每日次数
            row = (await session.execute(
                text("SELECT count FROM math_daily_count WHERE user_id=:u AND date=:d"),
                {"u": user_id, "d": today}
            )).first()
            
            count = row[0] if row else 0
            if count >= self.MATH_DAILY_LIMIT:
                raise _BizError(f"今天已经玩了 {self.MATH_DAILY_LIMIT} 次，明天再来喵~")
            
            # 生成题目
            difficulty, question_str, answer = self._generate_math_question()
            reward = {
                "简单": self.MATH_REWARD_EASY,
                "中等": self.MATH_REWARD_MEDIUM,
                "困难": self.MATH_REWARD_HARD,
            }[difficulty]
            
            # 保存会话
            expire_time = time.time() + self.MATH_TIMEOUT
            await session.execute(
                text(
                    "INSERT OR REPLACE INTO math_challenges(user_id, question, answer, difficulty, expire_time) "
                    "VALUES(:u, :q, :a, :d, :e)"
                ),
                {"u": user_id, "q": question_str, "a": str(answer), "d": difficulty, "e": expire_time}
            )
            
            self._math_sessions[user_id] = {
                "question": question_str,
                "answer": answer,
                "difficulty": difficulty,
                "reward": reward,
                "expire": expire_time,
            }
            
            return True, (question_str, difficulty, reward), None
        
        ok, data, _ = await self._tx(fn)
        if not ok:
            yield event.plain_result(data)
            return
        
        question_str, difficulty, reward = data
        yield event.plain_result(
            f"🧮 {question_str} = ？\n"
            f"难度：{difficulty}（答对得 {reward} 积分）\n"
            f"限时 {self.MATH_TIMEOUT} 秒，直接回复数字答案喵~"
        )

    @filter.event_message_type(EventMessageType.ALL)
    async def math_answer_listener(self, event: AstrMessageEvent):
        """监听速算答案"""
        user_id = event.get_sender_id()
        if user_id not in self._math_sessions:
            return
        
        msg = event.get_message_str().strip()
        if not msg.lstrip('-').isdigit():
            return
        
        session_data = self._math_sessions.pop(user_id)
        if time.time() > session_data["expire"]:
            yield event.plain_result(f"⏰ 超时了！正确答案是 {session_data['answer']} 喵~")
            return
        
        user_answer = msg
        correct_answer = str(session_data["answer"])
        
        if user_answer == correct_answer:
            reward = session_data["reward"]
            today = date.today().isoformat()
            
            async def fn(session):
                await self._ensure_user(session, user_id)
                await self._add_points(session, user_id, reward, f"速算挑战（{session_data['difficulty']}）")
                balance = await self._balance(session, user_id)
                
                # 更新每日次数
                await session.execute(
                    text(
                        "INSERT INTO math_daily_count(user_id, date, count) VALUES(:u, :d, 1) "
                        "ON CONFLICT(user_id, date) DO UPDATE SET count=count+1"
                    ),
                    {"u": user_id, "d": today}
                )
                
                # 清理挑战记录
                await session.execute(
                    text("DELETE FROM math_challenges WHERE user_id=:u"), {"u": user_id}
                )
                
                return True, balance, None
            
            ok, balance, _ = await self._tx(fn)
            yield event.plain_result(f"✅ 正确！+{reward} 积分！当前余额：{balance}")
        else:
            yield event.plain_result(f"❌ 错了！正确答案是 {correct_answer} 喵~")
            
            # 清理数据库记录
            async def cleanup(session):
                await session.execute(
                    text("DELETE FROM math_challenges WHERE user_id=:u"), {"u": user_id}
                )
                return True, None, None
            
            await self._tx(cleanup)

    def _generate_math_question(self):
        """生成速算题目，返回 (难度, 题目字符串, 答案)"""
        difficulty_roll = random.random()
        
        if difficulty_roll < 0.5:  # 50% 简单
            difficulty = "简单"
            a = random.randint(1, 50)
            b = random.randint(1, 50)
            op = random.choice(["+", "-"])
            if op == "+":
                question = f"{a} + {b}"
                answer = a + b
            else:
                question = f"{a} - {b}"
                answer = a - b
        
        elif difficulty_roll < 0.85:  # 35% 中等
            difficulty = "中等"
            a = random.randint(1, 100)
            b = random.randint(1, 100)
            op = random.choice(["+", "-", "×"])
            if op == "+":
                question = f"{a} + {b}"
                answer = a + b
            elif op == "-":
                question = f"{a} - {b}"
                answer = a - b
            else:
                b = random.randint(2, 12)  # 乘法用小数字
                question = f"{a} × {b}"
                answer = a * b
        
        else:  # 15% 困难
            difficulty = "困难"
            a = random.randint(10, 50)
            b = random.randint(2, 20)
            op = random.choice(["×", "÷"])
            if op == "×":
                question = f"{a} × {b}"
                answer = a * b
            else:
                # 确保整除
                answer = random.randint(5, 50)
                b = random.randint(2, 10)
                a = answer * b
                question = f"{a} ÷ {b}"
        
        return difficulty, question, answer

    # ============================================================
    #  功能11：谁是欧皇（抽卡系统）
    # ============================================================
    @filter.command("抽卡")
    async def gacha_draw(self, event: AstrMessageEvent):
        """抽卡：消耗10积分抽一张卡"""
        ok_gate, msg_gate = await self._check_group_gate(event, "抽卡")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        
        user_id = event.get_sender_id()
        
        async def fn(session):
            await self._ensure_user(session, user_id)
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            
            balance = await self._balance(session, user_id)
            if balance < self.CARD_COST:
                raise _BizError(f"积分不足喵~ 抽卡需要 {self.CARD_COST} 积分")
            
            # 扣除积分
            await self._add_points(session, user_id, -self.CARD_COST, "抽卡")
            # 检查消费达标提醒
            should_remind = await self._check_spend_reward(session, user_id, event.get_group_id())
            
            # 抽卡逻辑
            rarity, card_name = self._draw_card()
            
            # 保存卡牌
            row = (await session.execute(
                text("SELECT count FROM cards WHERE user_id=:u AND card_name=:c"),
                {"u": user_id, "c": card_name}
            )).first()
            
            if row:
                await session.execute(
                    text("UPDATE cards SET count=count+1 WHERE user_id=:u AND card_name=:c"),
                    {"u": user_id, "c": card_name}
                )
                is_new = False
                count = row[0] + 1
            else:
                await session.execute(
                    text("INSERT INTO cards(user_id, card_name, rarity, count) VALUES(:u, :c, :r, 1)"),
                    {"u": user_id, "c": card_name, "r": rarity}
                )
                is_new = True
                count = 1
            
            new_balance = await self._balance(session, user_id)
            
            # 检查是否集齐所有稀有度
            complete_check = (await session.execute(
                text("SELECT DISTINCT rarity FROM cards WHERE user_id=:u"), {"u": user_id}
            )).fetchall()
            collected_rarities = set(r[0] for r in complete_check)
            all_rarities = set(self.CARD_POOL.keys())
            
            # 判断是否首次集齐（检查是否已经领过奖励）
            already_rewarded = (await session.execute(
                text("SELECT 1 FROM point_transactions WHERE user_id=:u AND operation='集齐卡牌奖励'"),
                {"u": user_id}
            )).first()
            
            is_complete = (collected_rarities == all_rarities) and not already_rewarded
            
            return True, (rarity, card_name, is_new, count, new_balance, is_complete), should_remind
        
        ok, data, should_remind = await self._tx(fn)
        if not ok:
            yield event.plain_result(data)
            return
        
        rarity, card_name, is_new, count, new_balance, is_complete = data
        
        rarity_emoji = {"N": "⚪", "R": "🔵", "SR": "🟣", "SSR": "🟡"}
        emoji = rarity_emoji.get(rarity, "⚪")
        
        result = f"{emoji} 抽到了 {card_name}！"
        if is_new:
            result += " (NEW!)"
        else:
            result += f" (已拥有 {count} 张)"
        result += f"\n当前余额：{new_balance}"
        
        if is_complete:
            # 发放集齐奖励
            async def reward_fn(session):
                await self._add_points(session, user_id, self.CARD_COMPLETE_REWARD, "集齐卡牌奖励")
                final_balance = await self._balance(session, user_id)
                return True, final_balance, None
            
            ok, final_balance, _ = await self._tx(reward_fn)
            result += f"\n🎉 恭喜集齐所有稀有度！获得 {self.CARD_COMPLETE_REWARD} 积分奖励！\n当前余额：{final_balance}"
        
        yield event.plain_result(result)
        
        # 事务外发送提醒
        if ok and should_remind:
            group_id = event.get_group_id()
            if group_id:
                try:
                    yield event.plain_result(
                        f"[CQ:at,qq={user_id}] 🎉 累计消费达到 {self.SPEND_REWARD_THRESHOLD} 积分！\n"
                        f"发送 /兑换礼品 花费 {self.SPEND_REWARD_THRESHOLD} 积分即可兑换小礼品一份喵~"
                    )
                except Exception:
                    pass

    def _draw_card(self):
        """抽卡逻辑，返回 (稀有度, 卡名)"""
        roll = random.random()
        cumulative = 0.0
        
        for rarity, (prob, cards) in self.CARD_POOL.items():
            cumulative += prob
            if roll < cumulative:
                card_name = random.choice(cards)
                return rarity, card_name
        
        # 兜底（理论上不会到这里）
        return "N", random.choice(self.CARD_POOL["N"][1])

    @filter.command("图鉴")
    async def gacha_collection(self, event: AstrMessageEvent):
        """查看卡牌收集进度"""
        ok_gate, msg_gate = await self._check_group_gate(event, "图鉴")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        
        user_id = event.get_sender_id()
        
        async def fn(session):
            rows = (await session.execute(
                text("SELECT rarity, card_name, count FROM cards WHERE user_id=:u ORDER BY rarity, card_name"),
                {"u": user_id}
            )).fetchall()
            
            if not rows:
                return True, None, None
            
            # 按稀有度分组
            by_rarity = {"N": [], "R": [], "SR": [], "SSR": []}
            for r in rows:
                rarity, card_name, count = r
                by_rarity[rarity].append((card_name, count))
            
            collected_rarities = set(r[0] for r in rows)
            all_rarities = set(self.CARD_POOL.keys())
            is_complete = collected_rarities == all_rarities
            
            return True, (by_rarity, is_complete), None
        
        ok, data, _ = await self._tx(fn)
        
        if data is None:
            yield event.plain_result("你还没有收集任何卡牌喵~ 发送 /抽卡 开始收集吧！")
            return
        
        by_rarity, is_complete = data
        
        lines = ["📖 卡牌图鉴"]
        rarity_emoji = {"N": "⚪", "R": "🔵", "SR": "🟣", "SSR": "🟡"}
        
        for rarity in ["N", "R", "SR", "SSR"]:
            cards = by_rarity[rarity]
            emoji = rarity_emoji[rarity]
            if cards:
                lines.append(f"\n{emoji} {rarity} 稀有度：")
                for card_name, count in cards:
                    lines.append(f"  • {card_name} ×{count}")
            else:
                lines.append(f"\n{emoji} {rarity} 稀有度：暂未收集")
        
        total = sum(len(v) for v in by_rarity.values())
        all_cards_count = sum(len(cards) for _, (_, cards) in self.CARD_POOL.items())
        
        lines.append(f"\n收集进度：{total}/{all_cards_count}")
        if is_complete:
            lines.append("✅ 已集齐所有稀有度！")
        
        yield event.plain_result("\n".join(lines))

    # ============================================================
    #  功能12：赞助积分系统（人工审核版，仅限私聊）
    # ============================================================
    @filter.command("赞助")
    async def sponsor_info(self, event: AstrMessageEvent):
        """查看赞助积分方式（仅私聊）"""
        if not event.is_private_chat():
            yield event.plain_result("❌ 赞助功能仅支持私聊使用，请添加机器人好友后操作")
            return
        
        # 从配置读取上传的收款码路径列表
        sponsor_qrcode_list = self.config.get("sponsor_qrcode", [])
        # AstrBot file 类型通常返回 list，兼容旧配置中的单字符串。
        if isinstance(sponsor_qrcode_list, str):
            sponsor_qrcode_list = [sponsor_qrcode_list] if sponsor_qrcode_list.strip() else []
        if not isinstance(sponsor_qrcode_list, list) or not sponsor_qrcode_list:
            yield event.plain_result(
                "❌ 赞助功能未配置收款码\n\n"
                "💡 请在 AstrBot 插件配置页上传收款码图片，点击保存后重载插件"
            )
            return
        
        # 取第一个文件路径。AstrBot 4.27 的 file 文件保存在 data/plugin_data/point_games，
        # 兼容旧版保存在插件目录的情况。
        sponsor_rel_path = str(sponsor_qrcode_list[0]).strip()
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = []
        if os.path.isabs(sponsor_rel_path):
            candidates.append(sponsor_rel_path)
        else:
            candidates.append(os.path.join(plugin_dir, sponsor_rel_path))
        try:
            from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path
            candidates.append(os.path.join(
                get_astrbot_plugin_data_path(), "point_games", sponsor_rel_path
            ))
        except Exception:
            pass
        # 兼容配置里残留的旧 plugins/point_games 绝对路径。
        if "/data/plugins/point_games/" in sponsor_rel_path:
            candidates.append(sponsor_rel_path.replace(
                "/data/plugins/point_games/", "/data/plugin_data/point_games/"
            ))
        sponsor_abs_path = next((p for p in candidates if os.path.isfile(p)), "")
        if not sponsor_abs_path:
            self.logger.error(f"收款码文件不存在，尝试路径: {candidates}")
            yield event.plain_result(
                "❌ 收款码文件不存在，请在配置页删除旧文件后重新上传并保存"
            )
            return
        
        msg = (
            f"💰 赞助积分：1元={self.SPONSOR_RATE}积分\n"
            f"📱 请扫码支付，支付时务必备注您的QQ号\n"
            f"📸 支付完成后，请发送 /赞助审核 并引用（回复）订单截图\n"
            f"⏳ 管理员审核后积分将自动到账，请耐心等待\n"
            f"⚠️ 请务必在支付备注中填写您的QQ号，否则无法核实\n"
            f"⚠️ 截图需清晰显示订单号和金额，截图P图或伪造将被永久拉黑"
        )
        yield event.plain_result(msg)
        
        # 直接发送配置页上传的本地图片路径。
        yield event.image_result(sponsor_abs_path)

    @filter.command("赞助审核")
    async def sponsor_apply(self, event: AstrMessageEvent):
        """提交赞助申请（引用订单截图，仅私聊）"""
        user_id = str(event.get_sender_id())
        
        if not event.is_private_chat():
            yield event.plain_result("❌ 赞助功能仅支持私聊使用，请添加机器人好友后操作")
            return
        
        if not self.SPONSOR_ADMIN_QQ_LIST:
            yield event.plain_result("❌ 赞助功能未配置管理员，请联系管理员")
            return
        
        # 从当前消息链中寻找引用组件；AstrMessageEvent 没有 get_reply()。
        reply_component = next(
            (comp for comp in event.get_messages() if isinstance(comp, Reply)), None
        )
        if reply_component is None:
            yield event.plain_result("❌ 请引用您的支付订单截图\n示例：/赞助审核（回复图片消息）")
            return
        
        reply_chain = list(getattr(reply_component, "chain", None) or [])
        image_component = next(
            (comp for comp in reply_chain if isinstance(comp, Image)), None
        )
        if image_component is None:
            yield event.plain_result("❌ 请引用包含图片的支付订单截图")
            return
        
        # 优先使用引用消息中的图片组件；同时保留回复链，供平台发送原图。
        forwarded_chain = [image_component]
        
        async def fn(session):
            # 检查是否有pending申请
            pending = (await session.execute(
                text("SELECT id FROM sponsor_requests WHERE user_id=:u AND status='pending'"),
                {"u": user_id}
            )).first()
            
            if pending:
                raise _BizError("⏳ 您有正在审核的申请，请勿重复提交")
            
            # 插入申请记录
            await session.execute(
                text("INSERT INTO sponsor_requests(user_id, status, create_time) VALUES(:u, 'pending', :t)"),
                {"u": user_id, "t": time.time()}
            )
            
            return True, "ok", None
        
        ok, msg, _ = await self._tx(fn)
        if not ok:
            yield event.plain_result(msg)
            return
        
        # 转发给所有管理员
        for admin_qq in self.SPONSOR_ADMIN_QQ_LIST:
            try:
                # 发送提醒文本
                admin_msg = (
                    f"📢 赞助申请提醒\n"
                    f"申请人QQ：{user_id}\n"
                    f"申请时间：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"请使用以下指令处理：\n"
                    f"/赞助通过 {user_id} [积分数量]\n"
                    f"/赞助拒绝 {user_id} [理由]"
                )
                platform_id = event.get_platform_id()
                await self._send_to_session(
                    platform_id, _MessageType.FRIEND_MESSAGE, str(admin_qq),
                    MessageChain([Plain(admin_msg)])
                )
                # 转发引用的原图组件，避免调用不存在的 get_reply/get_message API。
                await self._send_to_session(
                    platform_id, _MessageType.FRIEND_MESSAGE, str(admin_qq),
                    MessageChain(forwarded_chain)
                )
            except Exception as e:
                self.logger.warning(f"转发赞助申请给管理员 {admin_qq} 失败：{e}")
        
        # 群聊@管理员（如有配置）
        if self.SPONSOR_GROUP_ID:
            try:
                ats = "".join([f"[CQ:at,qq={qq}]" for qq in self.SPONSOR_ADMIN_QQ_LIST])
                group_msg = f"📢 赞助申请提醒\n申请人：{user_id}\n请管理员及时处理 {ats}"
                await self.context.send_msg(_MessageType.GROUP_MESSAGE, self.SPONSOR_GROUP_ID, group_msg)
            except Exception as e:
                self.logger.warning(f"群聊提醒管理员失败：{e}")
        
        yield event.plain_result("✅ 已收到您的赞助申请，截图已转发给管理员\n⏳ 请耐心等待审核")

    @filter.command("赞助通过")
    async def sponsor_approve(self, event: AstrMessageEvent):
        """管理员审核通过"""
        admin_id = str(event.get_sender_id())
        
        if admin_id not in self.SPONSOR_ADMIN_QQ_LIST:
            yield event.plain_result("❌ 权限不足，仅管理员可执行")
            return
        
        # 兼容 AstrBot 传入带/或不带/的命令文本。
        args = self._strip_command(event, "赞助通过").split()
        if len(args) < 2:
            yield event.plain_result("❌ 格式错误：/赞助通过 [QQ号] [积分数量]")
            return
        
        target_id = args[0].strip()
        try:
            points = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 积分数量必须是数字")
            return
        
        if points <= 0:
            yield event.plain_result("❌ 积分数量必须大于0")
            return
        
        async def fn(session):
            # 检查是否有pending申请
            pending = (await session.execute(
                text("SELECT id FROM sponsor_requests WHERE user_id=:u AND status='pending' ORDER BY id DESC LIMIT 1"),
                {"u": target_id}
            )).first()
            
            if not pending:
                raise _BizError(f"❌ 用户 {target_id} 没有待审核的赞助申请")
            
            # 仅更新本次最新待审核申请，避免意外处理历史记录。
            await session.execute(
                text("UPDATE sponsor_requests SET status='approved', admin_id=:a, handle_time=:t, amount=:p WHERE id=:id"),
                {"a": admin_id, "t": time.time(), "p": points, "id": pending[0]}
            )
            
            # 发放积分
            await self._ensure_user(session, target_id)
            await self._add_points(session, target_id, points, "sponsor")
            new_balance = await self._balance(session, target_id)
            
            return True, new_balance, None
        
        ok, new_balance, _ = await self._tx(fn)
        if not ok:
            yield event.plain_result(new_balance)
            return
        
        # 通知用户
        try:
            user_msg = f"✅ 您的赞助申请已通过！\n已添加 {points} 积分到账\n当前余额：{new_balance} 积分"
            await self.context.send_msg(_MessageType.FRIEND_MESSAGE, target_id, user_msg)
        except Exception as e:
            self.logger.warning(f"通知用户 {target_id} 失败：{e}")
        
        yield event.plain_result(f"✅ 已为 {target_id} 增加 {points} 积分")

    @filter.command("赞助拒绝")
    async def sponsor_reject(self, event: AstrMessageEvent):
        """管理员拒绝申请"""
        admin_id = str(event.get_sender_id())
        
        if admin_id not in self.SPONSOR_ADMIN_QQ_LIST:
            yield event.plain_result("❌ 权限不足，仅管理员可执行")
            return
        
        # 兼容 AstrBot 传入带/或不带/的命令文本。
        args = self._strip_command(event, "赞助拒绝").split(maxsplit=1)
        if not args:
            yield event.plain_result("❌ 格式错误：/赞助拒绝 [QQ号] [理由]")
            return
        
        target_id = args[0].strip()
        reason = args[1].strip() if len(args) > 1 else "未提供理由"
        
        async def fn(session):
            # 检查是否有pending申请
            pending = (await session.execute(
                text("SELECT id FROM sponsor_requests WHERE user_id=:u AND status='pending' ORDER BY id DESC LIMIT 1"),
                {"u": target_id}
            )).first()
            
            if not pending:
                raise _BizError(f"❌ 用户 {target_id} 没有待审核的赞助申请")
            
            # 仅更新本次最新待审核申请，避免意外处理历史记录。
            await session.execute(
                text("UPDATE sponsor_requests SET status='rejected', admin_id=:a, handle_time=:t, remark=:r WHERE id=:id"),
                {"a": admin_id, "t": time.time(), "r": reason, "id": pending[0]}
            )
            
            return True, "ok", None
        
        ok, msg, _ = await self._tx(fn)
        if not ok:
            yield event.plain_result(msg)
            return
        
        # 通知用户
        try:
            user_msg = f"❌ 您的赞助申请被拒绝\n理由：{reason}\n如有疑问请联系管理员"
            await self.context.send_msg(_MessageType.FRIEND_MESSAGE, target_id, user_msg)
        except Exception as e:
            self.logger.warning(f"通知用户 {target_id} 失败：{e}")
        
        yield event.plain_result(f"❌ 已拒绝 {target_id} 的赞助申请")

    @filter.command("赞助列表")
    async def sponsor_list(self, event: AstrMessageEvent):
        """查看待审核申请（管理员）"""
        admin_id = str(event.get_sender_id())
        
        if admin_id not in self.SPONSOR_ADMIN_QQ_LIST:
            yield event.plain_result("❌ 权限不足，仅管理员可执行")
            return
        
        async def fn(session):
            rows = (await session.execute(
                text("SELECT user_id, create_time FROM sponsor_requests WHERE status='pending' ORDER BY create_time DESC LIMIT 20")
            )).fetchall()
            
            return True, rows, None
        
        ok, rows, _ = await self._tx(fn)
        
        if not rows:
            yield event.plain_result("当前没有待审核的赞助申请")
            return
        
        lines = ["📋 待审核赞助申请："]
        for user_id, create_time in rows:
            time_str = datetime.fromtimestamp(float(create_time), TZ).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"• {user_id} - {time_str}")
        
        yield event.plain_result("\n".join(lines))

    async def sign_in(self, event: AstrMessageEvent):
        """兼容旧代码调用；实际群消息由 daily_car_checkin 统一处理。"""
        yield event.plain_result(await self._sign_in_text(event))

    async def _sign_in_text(self, event: AstrMessageEvent) -> str:
        """执行积分签到并返回结果，供座驾签到监听器合并输出。"""
        ok_gate, msg_gate = await self._check_group_gate(event, "签到")
        if not ok_gate:
            return msg_gate
        user_id = event.get_sender_id()
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            # 先查后建：is_new 用于判断首次签到（users 表此前无该用户记录）
            row = (
                await session.execute(
                    text("SELECT sign_in_date, sign_in_streak FROM users WHERE user_id=:u"),
                    {"u": user_id},
                )
            ).first()
            is_new = row is None
            # 首次签到判定：users 无记录，或存在记录但从未签到过（sign_in_date 为空）
            # 避免玩家先玩过其他玩法导致"永远不算新人"而领不到送竿
            first_sign_in = row is None or row[0] is None
            await self._ensure_user(session, user_id)
            if row and row[0] == today:
                raise _BizError("今天已经签到过啦，明天再来喵~")
            streak = 1
            if row and row[0] == yesterday:
                streak = int(row[1]) + 1
            reward = random.randint(self.SIGN_IN_MIN, self.SIGN_IN_MAX)
            bonus = self.SIGN_IN_WEEK_BONUS if streak % 7 == 0 else 0
            await self._add_points(session, user_id, reward + bonus, "每日签到")
            await session.execute(
                text("UPDATE users SET sign_in_date=:d, sign_in_streak=:s WHERE user_id=:u"),
                {"d": today, "s": streak, "u": user_id},
            )
            msg = f"📝 签到成功！+{reward} 积分，已连续签到 {streak} 天"
            if bonus:
                msg += f"\n🎉 连续签到 {streak} 天额外 +{bonus} 积分！"
            if first_sign_in:
                # 首次签到：免费赠送 1 号鱼竿（已拥有鱼竿则不重复赠送）
                has_rod = (await session.execute(text(
                    "SELECT 1 FROM fishing_rods WHERE user_id=:u LIMIT 1"
                ), {"u": user_id})).first()
                if not has_rod:
                    await session.execute(text(
                        "INSERT INTO fishing_rods(user_id, slot, status, created_at) "
                        "VALUES(:u, :s, 'idle', :t)"
                    ), {"u": user_id, "s": 1, "t": time.time()})
                    msg = (f"🎣 签到成功！获得 {reward} 积分！\n"
                           f"🎁 首次签到奖励：免费领取一根鱼竿！\n"
                           f"发送 /挂机钓鱼 即可开始挂机赚钱")
            msg += f"\n当前积分：{await self._balance(session, user_id)} 喵~"
            return True, msg, None

        _, msg, _ = await self._tx(fn)
        return msg

    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    @filter.regex(re.compile(r"(?i)^(?:签到|jrzj|今日座驾)\s*$"))
    async def daily_car_checkin(self, event: AstrMessageEvent):
        """群内发送 签到、jrzj 或 今日座驾，合并输出签到和座驾。"""
        sign_text = await self._sign_in_text(event)
        car_text = await self._daily_car_text(event)
        yield event.plain_result(f"{sign_text}\n\n{car_text}")
        event.stop_event()

    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    @filter.regex(DAILY_CAR_ADD_PATTERN)
    @filter.permission_type(PermissionType.ADMIN)
    async def add_daily_car(self, event: AstrMessageEvent):
        """群管理员发送 添加车辆 车型，将车型写入每日座驾车池。"""
        match = DAILY_CAR_ADD_PATTERN.match(event.get_message_str().strip())
        car_name = self._normalize_car_text(match.group("car")) if match else ""
        if not car_name:
            yield event.plain_result("格式：添加车辆 车辆名称")
            event.stop_event()
            return
        if car_name in self.daily_car_pool:
            yield event.plain_result("这辆车已经在车池里了")
            event.stop_event()
            return
        try:
            await self._save_daily_car_config([*self.daily_car_pool, car_name])
            yield event.plain_result(f"已添加车辆：{car_name}")
        except _BizError as e:
            yield event.plain_result(e.msg)
        event.stop_event()

    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    @filter.regex(re.compile(r"^查看车池$"))
    async def view_daily_car_pool(self, event: AstrMessageEvent):
        """群成员发送 查看车池，列出每日座驾车辆池。"""
        message = "车池为空" if not self.daily_car_pool else "当前车池：\n" + "\n".join(
            self._format_car_entry(car) for car in self.daily_car_pool
        )
        yield event.plain_result(message)
        event.stop_event()

    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    @filter.regex(DAILY_CAR_DELETE_PATTERN)
    @filter.permission_type(PermissionType.ADMIN)
    async def delete_daily_car(self, event: AstrMessageEvent):
        """群管理员发送 删除车辆 车型，从每日座驾车池移除。"""
        match = DAILY_CAR_DELETE_PATTERN.match(event.get_message_str().strip())
        car_name = self._normalize_car_text(match.group("car")) if match else ""
        if not car_name:
            yield event.plain_result("格式：删除车辆 车辆名称")
            event.stop_event()
            return
        if car_name not in self.daily_car_pool:
            yield event.plain_result("车池里没有这辆车")
            event.stop_event()
            return
        try:
            await self._save_daily_car_config([car for car in self.daily_car_pool if car != car_name])
            yield event.plain_result(f"已删除车辆：{car_name}")
        except _BizError as e:
            yield event.plain_result(e.msg)
        event.stop_event()

    # ============================================================
    #  WebUI 面板（API + 页面）
    # ============================================================
    def _register_web_apis(self):
        ctx = self.context
        if not hasattr(ctx, "register_web_api"):
            self.logger.warning("当前 AstrBot 版本不支持 register_web_api，WebUI 面板不可用")
            return
        ctx.register_web_api("/point_games/dashboard", self._web_dashboard, ["GET"], "积分游戏面板（独立窗口）")
        ctx.register_web_api("/point_games/api/whoami", self._web_whoami, ["GET"], "当前面板用户")
        ctx.register_web_api("/point_games/api/stats", self._web_stats, ["GET"], "积分游戏总览")
        ctx.register_web_api("/point_games/api/leaderboard", self._web_leaderboard, ["GET"], "积分排行榜")
        ctx.register_web_api("/point_games/api/users", self._web_users, ["GET"], "用户列表")
        ctx.register_web_api("/point_games/api/user_detail", self._web_user_detail, ["GET"], "玩家积分明细")
        ctx.register_web_api("/point_games/api/boss", self._web_boss, ["GET"], "BOSS 状态")
        ctx.register_web_api("/point_games/api/lottery", self._web_lottery, ["GET"], "彩票信息")
        ctx.register_web_api("/point_games/api/transactions", self._web_transactions, ["GET"], "积分流水明细")
        ctx.register_web_api("/point_games/api/groups", self._web_groups, ["GET"], "群设置列表")
        ctx.register_web_api("/point_games/api/groups/toggle", self._web_group_toggle, ["POST"], "开关群玩法")
        ctx.register_web_api("/point_games/api/config/mode", self._web_mode_set, ["POST"], "切换全局模式")
        ctx.register_web_api("/point_games/api/admin/grant", self._web_grant, ["POST"], "WebUI 加/扣积分")

    def _web_admin_ok(self) -> bool:
        """WebUI 管理操作已开放给所有已登录面板用户（AstrBot 面板登录即视为可信）"""
        return True

    async def _web_dashboard(self):
        from fastapi.responses import HTMLResponse
        import os
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception:
            html = "<h1>dashboard.html 缺失</h1><p>请确认插件目录下存在 dashboard.html</p>"
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")

    async def _web_whoami(self):
        from astrbot.api.web import json_response, request as web_request
        try:
            req = web_request
            username = getattr(req, "username", "") or ""
        except Exception:
            username = ""
        return json_response({"username": username, "is_admin": True})

    async def _web_stats(self):
        from astrbot.api.web import json_response
        today = date.today().isoformat()

        async def fn(session):
            user_cnt = (await session.execute(text("SELECT COUNT(*) FROM users"))).first()
            txn_today = (
                await session.execute(
                    text("SELECT COALESCE(SUM(amount),0) FROM point_transactions WHERE create_time >= :t"),
                    {"t": datetime.combine(date.today(), datetime.min.time()).timestamp()},
                )
            ).first()
            spin_cnt = (
                await session.execute(
                    text("SELECT COUNT(*) FROM point_transactions WHERE operation='幸运转盘'")
                )
            ).first()
            boss_row = (await session.execute(text("SELECT current_hp FROM boss WHERE id=1"))).first()
            bought = (
                await session.execute(
                    text("SELECT COALESCE(SUM(cost),0), COUNT(DISTINCT user_id) FROM lottery WHERE period=:p"), {"p": today}
                )
            ).first()
            carry = 0
            prev = (date.today() - timedelta(days=1)).isoformat()
            c_row = (await session.execute(text("SELECT pool FROM lottery_pool WHERE period=:p"), {"p": prev})).first()
            if c_row:
                carry = int(c_row[0])
            uc_cnt = (
                await session.execute(text("SELECT COUNT(*) FROM undercover_games WHERE status IN ('waiting','speech','voting')"))
            ).first()
            return True, "ok", {
                "users": int(user_cnt[0]),
                "today_transactions": int(txn_today[0]),
                "spin_total": int(spin_cnt[0]),
                "boss_hp": int(boss_row[0]) if boss_row else 0,
                "lottery_pool": int(bought[0]) + self.LOTTERY_BASE_POOL + carry,
                "lottery_participants": int(bought[1]),
                "active_undercover": int(uc_cnt[0]),
            }

        ok, _, data = await self._tx(fn)
        return json_response(data if data else {})

    async def _web_leaderboard(self):
        from astrbot.api.web import json_response

        async def fn(session):
            rows = (
                await session.execute(
                    text("SELECT user_id, user_name, balance, total_earned, total_spent, sign_in_streak FROM users ORDER BY balance DESC LIMIT 50")
                )
            ).all()
            return True, "ok", [
                {"user_id": r[0], "user_name": r[1] or "未知玩家", "balance": int(r[2]), "total_earned": int(r[3]),
                 "total_spent": int(r[4]), "sign_in_streak": int(r[5])}
                for r in rows
            ]

        ok, _, data = await self._tx(fn)
        return json_response(data if data else [])

    async def _web_users(self):
        from astrbot.api.web import json_response, request as web_request
        try:
            req = web_request
            params = getattr(req, "query", None) or getattr(req, "query_params", {})
        except Exception:
            params = {}
        page = max(1, int(params.get("page", 1)))
        page_size = min(50, max(5, int(params.get("page_size", 20))))
        keyword = str(params.get("search", "") or "").strip()

        async def fn(session):
            if keyword:
                total = (
                    await session.execute(text("SELECT COUNT(*) FROM users WHERE user_id LIKE :k OR user_name LIKE :k"), {"k": f"%{keyword}%"})
                ).first()
                rows = (
                    await session.execute(
                        text("SELECT user_id, user_name, balance, total_earned, total_spent, sign_in_date, sign_in_streak FROM users WHERE user_id LIKE :k OR user_name LIKE :k ORDER BY balance DESC LIMIT :n OFFSET :o"),
                        {"k": f"%{keyword}%", "n": page_size, "o": (page - 1) * page_size},
                    )
                ).all()
            else:
                total = (await session.execute(text("SELECT COUNT(*) FROM users"))).first()
                rows = (
                    await session.execute(
                        text("SELECT user_id, user_name, balance, total_earned, total_spent, sign_in_date, sign_in_streak FROM users ORDER BY balance DESC LIMIT :n OFFSET :o"),
                        {"n": page_size, "o": (page - 1) * page_size},
                    )
                ).all()
            return True, "ok", {
                "total": int(total[0]),
                "page": page,
                "page_size": page_size,
                "users": [
                    {"user_id": r[0], "user_name": r[1] or "未知玩家", "balance": int(r[2]), "total_earned": int(r[3]),
                     "total_spent": int(r[4]), "sign_in_date": r[5], "sign_in_streak": int(r[6])}
                    for r in rows
                ],
            }

        ok, _, data = await self._tx(fn)
        return json_response(data if data else {})

    async def _web_user_detail(self):
        from astrbot.api.web import json_response, error_response, request as web_request
        try:
            req = web_request
            params = getattr(req, "query", None) or getattr(req, "query_params", {})
            user_id = str(params.get("user_id", "")).strip()
        except Exception:
            user_id = ""
        if not user_id:
            return error_response("缺少 user_id")

        async def fn(session):
            user = (await session.execute(text(
                "SELECT user_id, user_name, balance, total_earned, total_spent, sign_in_streak "
                "FROM users WHERE user_id=:u"
            ), {"u": user_id})).first()
            if not user:
                return False, "玩家不存在", None
            rows = (await session.execute(text(
                "SELECT amount, earned, spent, balance_after, operation, create_time "
                "FROM point_transactions WHERE user_id=:u ORDER BY id DESC LIMIT 100"
            ), {"u": user_id})).all()
            return True, "ok", {
                "user_id": user[0], "user_name": user[1] or "未知玩家", "balance": int(user[2]),
                "total_earned": int(user[3]), "total_spent": int(user[4]),
                "sign_in_streak": int(user[5]),
                "transactions": [
                    {"amount": int(r[0]), "earned": int(r[1] or 0), "spent": int(r[2] or 0),
                     "balance_after": int(r[3] or 0), "operation": r[4],
                     "detail": f"收入 +{int(r[1] or 0)}，支出 -{int(r[2] or 0)}，净变化 {int(r[0])}，余额 {int(r[3] or 0)}",
                     "time": datetime.fromtimestamp(float(r[5])).strftime("%Y-%m-%d %H:%M:%S") if r[5] else ""}
                    for r in rows
                ],
            }

        ok, msg, data = await self._tx(fn)
        if not ok:
            return error_response(msg, 404)
        return json_response(data)

    async def _web_boss(self):
        from astrbot.api.web import json_response

        async def fn(session):
            await self._ensure_boss_reset(session)
            row = (await session.execute(text("SELECT current_hp, pool, reset_date FROM boss WHERE id=1"))).first()
            agg = (await session.execute(text("SELECT COALESCE(SUM(damage),0), COUNT(DISTINCT user_id) FROM boss_damage"))).first()
            top = (
                await session.execute(
                    text("SELECT b.user_id, u.user_name, SUM(b.damage) AS dmg FROM boss_damage b LEFT JOIN users u ON u.user_id=b.user_id GROUP BY b.user_id, u.user_name ORDER BY dmg DESC LIMIT 10")
                )
            ).all()
            return True, "ok", {
                "hp": int(row[0]) if row else 0,
                "max_hp": self.BOSS_MAX_HP,
                "pool": int(row[1]) if row else 0,
                "reset_date": row[2] if row else None,
                "today_damage": int(agg[0]),
                "participants": int(agg[1]),
                "top": [{"user_id": r[0], "user_name": r[1] or "未知玩家", "damage": int(r[2])} for r in top],
            }

        ok, _, data = await self._tx(fn)
        return json_response(data if data else {})

    async def _web_lottery(self):
        from astrbot.api.web import json_response
        today = date.today().isoformat()

        async def fn(session):
            bought = (
                await session.execute(
                    text("SELECT COALESCE(SUM(cost),0), COUNT(DISTINCT user_id), COUNT(*) FROM lottery WHERE period=:p"),
                    {"p": today},
                )
            ).first()
            carry = 0
            prev = (date.today() - timedelta(days=1)).isoformat()
            c_row = (await session.execute(text("SELECT pool FROM lottery_pool WHERE period=:p"), {"p": prev})).first()
            if c_row:
                carry = int(c_row[0])
            last_rows = (
                await session.execute(
                    text("SELECT user_id, numbers, cost, period FROM lottery ORDER BY id DESC LIMIT 10")
                )
            ).all()
            return True, "ok", {
                "pool": int(bought[0]) + self.LOTTERY_BASE_POOL + carry,
                "bought": int(bought[0]),
                "participants": int(bought[1]),
                "tickets": int(bought[2]),
                "limit_per_day": self.LOTTERY_LIMIT_PER_DAY,
                "base_pool": self.LOTTERY_BASE_POOL,
                "carry": carry,
                "recent": [
                    {"user_id": r[0], "numbers": json.loads(r[1]), "cost": int(r[2]), "period": r[3]}
                    for r in last_rows
                ],
            }

        ok, _, data = await self._tx(fn)
        return json_response(data if data else {})

    async def _web_transactions(self):
        from astrbot.api.web import json_response
        try:
            from astrbot.api.web import request as web_request
            req = web_request
            params = req.query if hasattr(req, "query") else {}
        except Exception:
            params = {}
        limit = min(100, max(5, int(params.get("limit", 20))))

        async def fn(session):
            rows = (
                await session.execute(
                    text(
                        "SELECT t.user_id, u.user_name, t.amount, t.earned, t.spent, "
                        "t.balance_after, t.operation, t.create_time "
                        "FROM point_transactions t LEFT JOIN users u ON u.user_id=t.user_id "
                        "ORDER BY t.id DESC LIMIT :n"
                    ),
                    {"n": limit},
                )
            ).all()
            return True, "ok", [
                {"user_id": r[0], "user_name": r[1] or "未知玩家", "amount": int(r[2]),
                 "earned": int(r[3] or 0), "spent": int(r[4] or 0), "balance_after": int(r[5] or 0),
                 "operation": r[6],
                 "detail": f"收入 +{int(r[3] or 0)}，支出 -{int(r[4] or 0)}，净变化 {int(r[2])}，余额 {int(r[5] or 0)}",
                 "time": datetime.fromtimestamp(float(r[7])).strftime("%Y-%m-%d %H:%M:%S") if r[7] else ""}
                for r in rows
            ]

        ok, _, data = await self._tx(fn)
        return json_response(data if data else [])

    async def _web_groups(self):
        from astrbot.api.web import json_response

        async def fn(session):
            mode = await self._get_config_value(session, "group_mode", self.DEFAULT_GROUP_MODE)
            rows = (
                await session.execute(text("SELECT group_id, enabled, updated_at FROM group_settings ORDER BY updated_at DESC LIMIT 100"))
            ).all()
            return True, "ok", {
                "mode": mode,
                "groups": [
                    {"group_id": r[0], "enabled": int(r[1]),
                     "updated_at": datetime.fromtimestamp(float(r[2])).strftime("%Y-%m-%d %H:%M:%S") if r[2] else ""}
                    for r in rows
                ],
            }

        ok, _, data = await self._tx(fn)
        return json_response(data if data else {})

    async def _web_group_toggle(self):
        from astrbot.api.web import json_response, error_response, request as web_request
        if not self._web_admin_ok():
            return error_response("无权限：当前面板用户不在管理名单中", 403)
        try:
            req = web_request
            body = await req.json()
            group_id = str(body.get("group_id", "")).strip()
            enabled = 1 if body.get("enabled") else 0
            platform_id = str(body.get("platform_id", "")).strip()
        except Exception as e:
            return error_response(f"参数错误：{e}")
        if not group_id:
            return error_response("缺少 group_id")

        async def fn(session):
            await session.execute(
                text(
                    "INSERT INTO group_settings(group_id, enabled, updated_at, platform_id) VALUES(:g, :e, :t, :p) "
                    "ON CONFLICT(group_id) DO UPDATE SET enabled=:e, updated_at=:t, platform_id=:p"
                ),
                {"g": group_id, "e": enabled, "t": time.time(), "p": platform_id},
            )
            return True, "ok", None

        ok, msg, _ = await self._tx(fn)
        return json_response({"ok": ok, "message": msg})

    async def _web_mode_set(self):
        from astrbot.api.web import json_response, error_response, request as web_request
        if not self._web_admin_ok():
            return error_response("无权限：当前面板用户不在管理名单中", 403)
        try:
            req = web_request
            body = await req.json()
            mode = str(body.get("mode", "")).strip()
        except Exception as e:
            return error_response(f"参数错误：{e}")
        if mode not in ("whitelist", "blacklist"):
            return error_response("mode 只能是 whitelist 或 blacklist")

        async def fn(session):
            await self._set_config_value(session, "group_mode", mode)
            return True, "ok", None

        ok, msg, _ = await self._tx(fn)
        return json_response({"ok": ok, "message": msg})

    async def _web_grant(self):
        from astrbot.api.web import json_response, error_response, request as web_request
        if not self._web_admin_ok():
            return error_response("无权限：当前面板用户不在管理名单中", 403)
        try:
            req = web_request
            body = await req.json()
            user_id = str(body.get("user_id", "")).strip()
            amount = int(body.get("amount", 0))
        except Exception as e:
            return error_response(f"参数错误：{e}")
        if not user_id:
            return error_response("缺少 user_id")
        if amount == 0:
            return error_response("amount 不能为 0")

        async def fn(session):
            await self._ensure_user(session, user_id)
            await self._add_points(session, user_id, amount, "管理员加分" if amount > 0 else "管理员扣分")
            new_bal = await self._balance(session, user_id)
            return True, f"ok", {"user_id": user_id, "balance": new_bal}

        ok, msg, data = await self._tx(fn)
        if not ok:
            return error_response(msg)
        return json_response(data)

    @filter.command("兑换礼品")
    async def redeem_gift(self, event: AstrMessageEvent):
        """/兑换礼品 —— 花费 10000 积分兑换小礼品一份，兑换后联系管理员领取"""
        ok_gate, msg_gate = await self._check_group_gate(event, "兑换礼品")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()

        async def fn(session):
            await self._ensure_user(session, user_id)
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            bal = await self._balance(session, user_id)
            if bal < self.SPEND_REWARD_THRESHOLD:
                raise _BizError(
                    f"积分不足喵~ 兑换礼品需要 {self.SPEND_REWARD_THRESHOLD} 积分，"
                    f"你只有 {bal} 积分"
                )
            # 扣积分并记录流水，同时累计兑换次数
            await self._add_points(
                session, user_id, -self.SPEND_REWARD_THRESHOLD, "兑换礼品"
            )
            await session.execute(text(
                "UPDATE users SET gift_redeemed=gift_redeemed+1 WHERE user_id=:u"
            ), {"u": user_id})
            new_bal = await self._balance(session, user_id)
            return True, (
                f"🎁 兑换成功！已花费 {self.SPEND_REWARD_THRESHOLD} 积分，"
                f"当前积分：{new_bal}\n请联系管理员领取小礼品喵~"
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    # ============================================================
    #  钓鱼系统
    # ============================================================
    def _fishing_roll_event(self) -> str:
        """按 FISHING_EVENTS 概率表随机判定一次挂机事件"""
        roll = random.uniform(0, 100)
        cumulative = 0.0
        for name, prob in FISHING_EVENTS:
            cumulative += prob
            if roll <= cumulative:
                return name
        return "空钩"

    def _fishing_pick_fish(self):
        """按概率加权随机抽一条鱼，返回 (鱼名, 售价, 稀有度, 单条概率%)。

        鱼类配置概率合计约 76.0052%，剩余部分视为钓上杂物（返回 None，一无所得）。
        """
        roll = random.uniform(0, 100)
        cumulative = 0.0
        for name, (price, rarity, prob) in FISH_POOL.items():
            cumulative += prob
            if roll <= cumulative:
                return name, price, rarity, prob
        return None  # 杂物：水面漂过一片水草，一无所得

    async def _fishing_ensure_stats(self, session, user_id: str) -> None:
        """确保钓鱼统计行存在，并惰性重置过期计数（必须在事务内调用）"""
        today = date.today().isoformat()
        row = (await session.execute(
            text("SELECT today_date FROM fishing_stats WHERE user_id=:u"), {"u": user_id}
        )).first()
        if not row:
            await session.execute(
                text("INSERT INTO fishing_stats(user_id, today_date) VALUES(:u, :d)"),
                {"u": user_id, "d": today},
            )
        elif row[0] != today:
            await session.execute(
                text("UPDATE fishing_stats SET today_count=0, today_date=:d WHERE user_id=:u"),
                {"u": user_id, "d": today},
            )

    async def _fishing_bait_count(self, session, user_id: str) -> int:
        """查询当前鱼饵数量（必须在事务内调用）"""
        row = (await session.execute(
            text("SELECT count FROM fishing_baits WHERE user_id=:u"), {"u": user_id}
        )).first()
        return int(row[0] or 0) if row else 0

    async def _get_broadcast_groups(self) -> list[tuple[str, str]]:
        """获取已开启玩法的群列表（group_settings 优先，platform_manager 全平台兜底）"""
        try:
            async with self._session() as session:
                rows = (await session.execute(text(
                    "SELECT group_id, platform_id FROM group_settings WHERE enabled=1"
                ))).all()
            groups = [(str(p or ""), str(g)) for g, p in rows]
            if not groups:
                self.logger.warning("没有已开启玩法的群（group_settings 为空），无法兜底播报")
            return groups
        except Exception:
            self.logger.exception("获取播报群列表失败")
            return []

    async def _get_platform_ids(self) -> list[str]:
        """获取当前所有平台实例 ID（AstrBot 兼容写法）"""
        ids: list[str] = []
        try:
            manager = getattr(self.context, "platform_manager", None)
            if manager and hasattr(manager, "get_insts"):
                ids = [str(p.meta().id) for p in manager.get_insts() if p.meta().id]
            elif manager and hasattr(manager, "platform_insts"):
                ids = [str(p.meta().id) for p in manager.platform_insts if p.meta().id]
        except Exception:
            pass
        return ids

    async def _send_with_fallback(
        self, platform_id: str, group_id: str, chain: list, tag: str
    ) -> bool:
        """多重路径发送播报。

        配置了 fishing_broadcast_groups 时只发配置的群（所有平台实例都试）；
        否则按「竿里存的平台ID → 当前所有平台实例 → 已开启玩法的群」重试。
        """
        targets: list[tuple[str, str]] = []
        if self.FISHING_BROADCAST_GROUPS:
            # 配置了播报群：定向发送到配置的群
            pids = await self._get_platform_ids() or [str(platform_id or "")]
            for group in self.FISHING_BROADCAST_GROUPS:
                for pid in pids:
                    targets.append((pid, group))
            for t_platform, t_group in targets:
                try:
                    await self._send_group_chain(t_platform, t_group, chain)
                except Exception:
                    self.logger.exception(
                        f"{tag}发送到播报群失败（{t_platform}:{t_group}）"
                    )
            return True
        if group_id:
            targets.append((str(platform_id), str(group_id)))
            for pid in await self._get_platform_ids():
                if pid and (pid, str(group_id)) not in targets:
                    targets.append((pid, str(group_id)))
        for fb_platform, fb_group in await self._get_broadcast_groups():
            if (fb_platform, fb_group) not in targets:
                targets.append((fb_platform, fb_group))
        for t_platform, t_group in targets:
            try:
                await self._send_group_chain(t_platform, t_group, chain)
                if (t_platform, t_group) != (str(platform_id), str(group_id)):
                    self.logger.info(f"{tag}已通过兜底路径送达（{t_platform}:{t_group}）")
                return True
            except Exception:
                self.logger.exception(f"{tag}发送失败（{t_platform}:{t_group}）")
        self.logger.warning(f"{tag}所有发送路径均失败（群号：{group_id or '空'}）")
        return False

    async def _fishing_check(self):
        """定时任务：每 30 分钟判定一次所有挂机中的鱼竿。

        每根竿消耗 1 个鱼饵后随机判定事件：
        上钩的鱼先进 fishing_pending，等玩家 /收鱼 进鱼篓；
        高价值鱼 / 至高传说直接全群广播（真实 At 组件）。
        """
        async def fn(session):
            rods = (await session.execute(text(
                "SELECT r.id, r.user_id, r.slot, r.platform_id, r.group_id, "
                "COALESCE(NULLIF(u.user_name, ''), r.user_id) "
                "FROM fishing_rods r LEFT JOIN users u ON u.user_id = r.user_id "
                "WHERE r.status='fishing'"
            ))).all()
            if not rods:
                return False, "没有挂机中的鱼竿", None
            broadcasts: list[tuple[str, str, list]] = []   # (platform_id, group_id, 消息链)
            notices: list[tuple[str, str, str]] = []       # (platform_id, group_id, 事件播报文本)
            for rod in rods:
                rid, uid, slot, platform_id, group_id, user_name = rod
                group_id = str(group_id or "")

                def notify(text_line: str):
                    """本群事件播报（不艾特，只说谁遇到了什么事）"""
                    if group_id:
                        notices.append((platform_id, group_id, f"🎣 {user_name} {text_line}"))
                await self._fishing_ensure_stats(session, uid)
                # 判定前消耗 1 个鱼饵，没鱼饵自动收杆
                bait = await self._fishing_bait_count(session, uid)
                if bait <= 0:
                    await session.execute(
                        text("UPDATE fishing_rods SET status='idle' WHERE id=:i"), {"i": rid}
                    )
                    notify("的鱼饵用完了，自动收杆休息啦~")
                    continue
                await session.execute(
                    text("UPDATE fishing_baits SET count=count-1 WHERE user_id=:u"), {"u": uid}
                )
                # 幸运日 buff：有效期内空钩视为上钩
                st = (await session.execute(
                    text("SELECT lucky_day_expire FROM fishing_stats WHERE user_id=:u"),
                    {"u": uid},
                )).first()
                lucky_active = bool(st and st[0] and float(st[0]) > time.time())
                event = self._fishing_roll_event()
                if event == "空钩" and lucky_active:
                    event = "正常上钩"
                # 本次判定统计（每次判定消耗 1 鱼饵）
                await session.execute(text(
                    "UPDATE fishing_stats SET total_baits_used=total_baits_used+1, "
                    "today_count=today_count+1 WHERE user_id=:u"
                ), {"u": uid})
                if event in ("正常上钩", "双鱼上钩"):
                    # 上钩：鱼先进入 pending，等 /收鱼（也可能钓上杂物一无所得）
                    caught = 2 if event == "双鱼上钩" else 1
                    fish_names: list[str] = []
                    junk = 0
                    for _ in range(caught):
                        picked = self._fishing_pick_fish()
                        if picked is None:
                            junk += 1
                            continue  # 杂物
                        name, price, rarity, prob = picked
                        fish_names.append(f"{name}（{price}积分）")
                        await session.execute(text(
                            "INSERT INTO fishing_pending(user_id, fish_name, catch_time) "
                            "VALUES(:u, :n, :t)"
                        ), {"u": uid, "n": name, "t": time.time()})
                        await session.execute(text(
                            "UPDATE fishing_stats SET total_caught=total_caught+1 WHERE user_id=:u"
                        ), {"u": uid})
                        # 全群广播：售价 > 1000 或至高传说
                        if price > self.FISHING_BROADCAST_PRICE or rarity == "至高传说":
                            chain = [At(qq=str(uid))]
                            if rarity == "至高传说":
                                chain.append(Plain(
                                    f" 🌟🌟🌟 钓到了 {name}（价值{price}积分！概率{prob}%！！！）\n"
                                    f"此乃万中无一之奇迹！"
                                ))
                            else:
                                chain.append(Plain(
                                    f" 🎉🎉🎉 钓到了 {name}（价值{price}积分！概率{prob}%！！！）"
                                ))
                            if group_id:
                                broadcasts.append((platform_id, group_id, chain))
                    if junk and not fish_names:
                        notify("感觉有东西咬钩，拉上来一只破靴子，一无所得…")
                    elif fish_names:
                        prefix = "一次钓上两条！" if caught == 2 and fish_names else ""
                        notify(f"{prefix}有鱼上钩啦，{('、'.join(fish_names))} 进了鱼篓！")
                elif event == "神秘宝箱":
                    amount = random.randint(self.FISHING_BOX_MIN, self.FISHING_BOX_MAX)
                    await self._add_points(session, uid, amount, "钓鱼宝箱")
                    notify(f"捞到一个神秘宝箱，开出 {amount} 积分！")
                elif event == "幸运日":
                    expire = time.time() + self.FISHING_LUCKY_HOURS * 3600
                    await session.execute(text(
                        "UPDATE fishing_stats SET lucky_day=lucky_day+1, lucky_day_expire=:e "
                        "WHERE user_id=:u"
                    ), {"u": uid, "e": expire})
                    notify(f"时来运转！获得 {self.FISHING_LUCKY_HOURS} 小时幸运buff，期间必定上钩！")
                elif event in ("鱼竿断裂", "海怪来袭"):
                    await session.execute(
                        text("UPDATE fishing_rods SET status='broken' WHERE id=:i"), {"i": rid}
                    )
                    if event == "鱼竿断裂":
                        notify("啪！鱼竿断了，记得 /修鱼竿 哦~")
                    else:
                        notify("被海怪吓了一跳，鱼跑了，鱼竿也断了…")
                elif event == "大鱼拔河":
                    notify("和大鱼拔河输了，眼睁睁看它跑掉…")
                elif event == "暴风雨":
                    notify("遇上暴风雨，空手而归…")
                # 空钩：普通事件也播报一下
                elif event == "空钩":
                    notify("守了半天，只有鱼饵被啃了，啥也没钓到…")
            return True, "判定完成", (broadcasts, notices)

        ok, msg, data = await self._tx(fn)
        if not ok or not data:
            self.logger.warning(f"钓鱼判定未执行：{msg}")
            return
        broadcasts, notices = data
        self.logger.info(f"钓鱼判定完成：播报 {len(notices)} 条事件，{len(broadcasts)} 条高价广播")
        # 事务外发送全群广播，避免阻塞数据库
        for platform_id, group_id, chain in broadcasts:
            await self._send_with_fallback(platform_id, group_id, chain, "钓鱼高价广播")
        # 事件播报（不艾特）：按群合并成一条消息发送，发送失败自动兜底
        grouped: dict[tuple[str, str], list[str]] = {}
        for platform_id, group_id, text_line in notices:
            grouped.setdefault((platform_id, group_id), []).append(text_line)
        for (platform_id, group_id), lines in grouped.items():
            await self._send_with_fallback(
                platform_id, group_id, [Plain("\n".join(lines))], "钓鱼事件播报"
            )

    async def _fishing_daily_reset(self):
        """定时任务：每天凌晨 0 点重置今日统计（today_count / today_date）"""
        async def fn(session):
            await session.execute(text(
                "UPDATE fishing_stats SET today_count=0, today_date=:d"
            ), {"d": date.today().isoformat()})
            return True, "今日钓鱼统计已重置", None

        await self._tx(fn)

    async def _fishing_grant_titles(
        self, session, user_id: str, collected: set[str]
    ) -> list[str]:
        """图鉴收集奖励判定（必须在事务内调用），返回奖励提示列表。

        称号规则：
        - 钓到烛心 → 烛心持有者；钓到闲鱼 → 闲鱼之王（纯称号，无积分）
        - 同时拥有烛心和闲鱼 → 额外 1000 积分 + 至高传说之主（只发一次）
        - 集齐全部 102 种 → 5000 积分 + 万物之主（只发一次）
        """
        rewards: list[str] = []
        if {"烛心", "闲鱼"} <= collected:
            already = (await session.execute(text(
                "SELECT 1 FROM point_transactions WHERE user_id=:u AND operation='钓鱼至高奖励'"
            ), {"u": user_id})).first()
            if not already:
                await self._add_points(
                    session, user_id, self.FISHING_BOTH_LEGEND_REWARD, "钓鱼至高奖励"
                )
                rewards.append(
                    f"🏆 同时拥有烛心和闲鱼：获得「至高传说之主」称号 "
                    f"+{self.FISHING_BOTH_LEGEND_REWARD} 积分！"
                )
        if len(collected) >= len(FISH_POOL):
            already = (await session.execute(text(
                "SELECT 1 FROM point_transactions WHERE user_id=:u AND operation='钓鱼集齐奖励'"
            ), {"u": user_id})).first()
            if not already:
                await self._add_points(
                    session, user_id, self.FISHING_FULL_REWARD, "钓鱼集齐奖励"
                )
                rewards.append(
                    f"👑 集齐全部 {len(FISH_POOL)} 种鱼：获得「万物之主」称号 "
                    f"+{self.FISHING_FULL_REWARD} 积分！"
                )
        return rewards

    @filter.command("买鱼竿")
    async def fishing_buy_rod(self, event: AstrMessageEvent):
        """/买鱼竿 —— 花费 200 积分购买一根鱼竿（最多 5 根）"""
        ok_gate, msg_gate = await self._check_group_gate(event, "买鱼竿")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()

        async def fn(session):
            await self._ensure_user(session, user_id)
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            cnt = (await session.execute(text(
                "SELECT COUNT(*) FROM fishing_rods WHERE user_id=:u"
            ), {"u": user_id})).first()
            if int(cnt[0]) >= self.MAX_RODS:
                raise _BizError(f"鱼竿已经满 {self.MAX_RODS} 根啦，不能再买了喵~")
            slots = {int(r[0]) for r in (await session.execute(text(
                "SELECT slot FROM fishing_rods WHERE user_id=:u"
            ), {"u": user_id})).all()}
            slot = next(i for i in range(1, self.MAX_RODS + 1) if i not in slots)
            bal = await self._balance(session, user_id)
            if bal < self.ROD_COST:
                raise _BizError(
                    f"积分不足喵~ 买鱼竿需要 {self.ROD_COST} 积分，你只有 {bal} 积分"
                )
            await self._add_points(session, user_id, -self.ROD_COST, "buy_rod")
            await session.execute(text(
                "INSERT INTO fishing_rods(user_id, slot, status, created_at) "
                "VALUES(:u, :s, 'idle', :t)"
            ), {"u": user_id, "s": slot, "t": time.time()})
            new_bal = await self._balance(session, user_id)
            return True, (
                f"🎣 购买成功！获得 {slot} 号鱼竿，花费 {self.ROD_COST} 积分，"
                f"当前积分：{new_bal} 喵~"
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("买鱼饵")
    async def fishing_buy_bait(self, event: AstrMessageEvent):
        """/买鱼饵 [数量] —— 10 积分/个购买鱼饵，不填数量默认买 1 个"""
        ok_gate, msg_gate = await self._check_group_gate(event, "买鱼饵")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()
        count = 1
        args = self._strip_command(event, "买鱼饵")
        if args:
            try:
                count = int(args.split()[0])
                if count <= 0:
                    raise ValueError
            except ValueError:
                yield event.plain_result("鱼饵数量得是正整数喵~")
                return

        async def fn(session):
            await self._ensure_user(session, user_id)
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            cost = count * self.BAIT_COST
            bal = await self._balance(session, user_id)
            if bal < cost:
                raise _BizError(
                    f"积分不足喵~ 买 {count} 个鱼饵需要 {cost} 积分，你只有 {bal} 积分"
                )
            await self._add_points(session, user_id, -cost, "buy_bait")
            await session.execute(text(
                "INSERT INTO fishing_baits(user_id, count) VALUES(:u, :c) "
                "ON CONFLICT(user_id) DO UPDATE SET count=fishing_baits.count+:c"
            ), {"u": user_id, "c": count})
            bait = await self._fishing_bait_count(session, user_id)
            new_bal = await self._balance(session, user_id)
            return True, (
                f"🪱 购买成功！获得 {count} 个鱼饵（花费 {cost} 积分），"
                f"现有鱼饵 {bait} 个，当前积分：{new_bal} 喵~"
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("挂机钓鱼")
    async def fishing_start(self, event: AstrMessageEvent):
        """/挂机钓鱼 [编号] —— 让鱼竿开始挂机，不填编号则全部待机鱼竿一起挂机"""
        ok_gate, msg_gate = await self._check_group_gate(event, "挂机钓鱼")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()
        platform_id = str(event.get_platform_id() or "")
        group_id = str(event.get_group_id() or "")
        args = self._strip_command(event, "挂机钓鱼")

        async def fn(session):
            await self._fishing_ensure_stats(session, user_id)
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            rods = (await session.execute(text(
                "SELECT id, slot, status FROM fishing_rods WHERE user_id=:u ORDER BY slot"
            ), {"u": user_id})).all()
            if not rods:
                raise _BizError("你还没有鱼竿，先 /买鱼竿 喵~")
            # 选出目标鱼竿
            if args:
                try:
                    slot = int(args.split()[0])
                except ValueError:
                    raise _BizError("鱼竿编号得是数字喵~")
                matched = [r for r in rods if int(r[1]) == slot]
                if not matched:
                    raise _BizError(f"没有 {slot} 号鱼竿喵~ 发 /鱼竿列表 查看你的鱼竿")
                rod = matched[0]
                if rod[2] == "fishing":
                    raise _BizError(f"{slot} 号鱼竿已经在挂机啦喵~")
                if rod[2] == "broken":
                    raise _BizError(f"{slot} 号鱼竿断了，先 /修鱼竿 {slot} 喵~")
                targets = [rod]
            else:
                targets = [r for r in rods if r[2] == "idle"]
                if not targets:
                    raise _BizError("没有待机的鱼竿喵~（挂机中或损坏的竿不能用）")
            bait = await self._fishing_bait_count(session, user_id)
            if bait <= 0:
                raise _BizError("没有鱼饵啦，先 /买鱼饵 再来钓鱼喵~")
            # 鱼饵不足以全覆盖时只启动部分鱼竿（每次判定每竿消耗 1 个鱼饵）
            start_n = min(len(targets), bait)
            for rod in targets[:start_n]:
                await session.execute(text(
                    "UPDATE fishing_rods SET status='fishing', platform_id=:p, group_id=:g "
                    "WHERE id=:i"
                ), {"p": platform_id, "g": group_id, "i": rod[0]})
            msg = (
                f"🎣 {start_n} 根鱼竿开始挂机啦！每 {self.CHECK_INTERVAL} 分钟判定一次，"
                f"每次每竿消耗 1 个鱼饵，钓到的鱼用 /收鱼 收取喵~"
            )
            if start_n < len(targets):
                msg += f"\n（鱼饵只够 {start_n} 根竿，剩下的先补鱼饵喵~）"
            return True, msg, None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("收鱼")
    async def fishing_collect(self, event: AstrMessageEvent):
        """/收鱼 —— 把 pending 里的鱼收进鱼篓，并记录图鉴/判定收集奖励"""
        ok_gate, msg_gate = await self._check_group_gate(event, "收鱼")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()

        async def fn(session):
            await self._fishing_ensure_stats(session, user_id)
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            pending = (await session.execute(text(
                "SELECT fish_name, COUNT(*) FROM fishing_pending WHERE user_id=:u "
                "GROUP BY fish_name"
            ), {"u": user_id})).all()
            if not pending:
                raise _BizError("还没钓到鱼喵~ 挂机中的鱼竿每 30 分钟判定一次，等等再来")
            total = 0
            new_species: list[str] = []
            details: list[str] = []
            for name, cnt in pending:
                name = str(name)
                cnt = int(cnt)
                total += cnt
                price, rarity, _prob = FISH_POOL.get(name, (0, "未知", 0.0))
                # 并入鱼篓
                await session.execute(text(
                    "INSERT INTO fishing_inventory(user_id, fish_name, count) "
                    "VALUES(:u, :n, :c) "
                    "ON CONFLICT(user_id, fish_name) DO UPDATE SET "
                    "count=fishing_inventory.count+:c"
                ), {"u": user_id, "n": name, "c": cnt})
                # 记录图鉴（钓到过即收集，卖鱼不影响进度）
                result = await session.execute(text(
                    "INSERT OR IGNORE INTO fishing_collection(user_id, fish_name, first_time) "
                    "VALUES(:u, :n, :t)"
                ), {"u": user_id, "n": name, "t": time.time()})
                if result.rowcount == 1:
                    new_species.append(f"{name}（{rarity}·{price}积分）")
                details.append(f"{name}×{cnt}")
            await session.execute(
                text("DELETE FROM fishing_pending WHERE user_id=:u"), {"u": user_id}
            )
            # 图鉴收集奖励判定（烛心/闲鱼/集齐）
            collected = {str(r[0]) for r in (await session.execute(text(
                "SELECT fish_name FROM fishing_collection WHERE user_id=:u"
            ), {"u": user_id})).all()}
            rewards = await self._fishing_grant_titles(session, user_id, collected)
            msg = f"🐟 收鱼成功！本次进篓 {total} 条：{'、'.join(details)}喵~"
            if new_species:
                msg += f"\n✨ 图鉴新收录：{'、'.join(new_species)}"
            for line in rewards:
                msg += f"\n{line}"
            return True, msg, None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("卖鱼")
    async def fishing_sell(self, event: AstrMessageEvent):
        """/卖鱼 —— 一键卖出鱼篓里所有鱼，按鱼类售价换算积分"""
        ok_gate, msg_gate = await self._check_group_gate(event, "卖鱼")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()

        async def fn(session):
            await self._fishing_ensure_stats(session, user_id)
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            rows = (await session.execute(text(
                "SELECT fish_name, count FROM fishing_inventory WHERE user_id=:u"
            ), {"u": user_id})).all()
            if not rows:
                raise _BizError("鱼篓里没有鱼可以卖喵~ 先 /挂机钓鱼 再来")
            total = 0
            fish_cnt = 0
            details: list[str] = []
            for name, cnt in rows:
                name = str(name)
                cnt = int(cnt or 0)
                price = FISH_POOL.get(name, (0,))[0]
                total += price * cnt
                fish_cnt += cnt
                details.append(f"{name}×{cnt}")
            # 卖鱼收入进账并记录流水（operation='sell_fish'）
            await self._add_points(session, user_id, total, "sell_fish", earned=total)
            await session.execute(text(
                "UPDATE fishing_stats SET total_income=total_income+:t WHERE user_id=:u"
            ), {"u": user_id, "t": total})
            await session.execute(
                text("DELETE FROM fishing_inventory WHERE user_id=:u"), {"u": user_id}
            )
            new_bal = await self._balance(session, user_id)
            return True, (
                f"💰 卖鱼成功！共卖出 {fish_cnt} 条：{'、'.join(details)}\n"
                f"收入 {total} 积分，当前积分：{new_bal} 喵~"
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("鱼图鉴")
    async def fishing_book(self, event: AstrMessageEvent):
        """/鱼图鉴 —— 查看已收集鱼类种类与总进度（共 102 种）"""
        ok_gate, msg_gate = await self._check_group_gate(event, "鱼图鉴")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()

        async def fn(session):
            collected = {str(r[0]) for r in (await session.execute(text(
                "SELECT fish_name FROM fishing_collection WHERE user_id=:u"
            ), {"u": user_id})).all()}
            lines = [f"📖 鱼图鉴：已收集 {len(collected)}/{len(FISH_POOL)} 种喵~"]
            for rarity, (_total_prob, fishes) in FISH_TABLE.items():
                names = {n for n, _p in fishes}
                lines.append(f"{rarity}：{len(names & collected)}/{len(names)}")
            return True, "\n".join(lines), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("鱼竿列表")
    async def fishing_rod_list(self, event: AstrMessageEvent):
        """/鱼竿列表 —— 查看每根鱼竿的状态和鱼饵余量"""
        ok_gate, msg_gate = await self._check_group_gate(event, "鱼竿列表")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()
        status_text = {"idle": "待机", "fishing": "挂机中", "broken": "已损坏"}

        async def fn(session):
            rods = (await session.execute(text(
                "SELECT slot, status FROM fishing_rods WHERE user_id=:u ORDER BY slot"
            ), {"u": user_id})).all()
            if not rods:
                raise _BizError("你还没有鱼竿，先 /买鱼竿 喵~")
            bait = await self._fishing_bait_count(session, user_id)
            lines = [f"🎣 鱼竿列表（鱼饵余量：{bait} 个）"]
            for slot, status in rods:
                lines.append(f"{int(slot)} 号竿：{status_text.get(str(status), str(status))}")
            return True, "\n".join(lines), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("修鱼竿")
    async def fishing_repair(self, event: AstrMessageEvent):
        """/修鱼竿 [编号] —— 花费 50 积分修理损坏的鱼竿"""
        ok_gate, msg_gate = await self._check_group_gate(event, "修鱼竿")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()
        args = self._strip_command(event, "修鱼竿")
        if not args:
            yield event.plain_result("用法：/修鱼竿 编号 喵~ 发 /鱼竿列表 查看编号")
            return
        try:
            slot = int(args.split()[0])
        except ValueError:
            yield event.plain_result("鱼竿编号得是数字喵~")
            return

        async def fn(session):
            await self._fishing_ensure_stats(session, user_id)
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            rod = (await session.execute(text(
                "SELECT id, status FROM fishing_rods WHERE user_id=:u AND slot=:s"
            ), {"u": user_id, "s": slot})).first()
            if not rod:
                raise _BizError(f"没有 {slot} 号鱼竿喵~ 发 /鱼竿列表 查看你的鱼竿")
            if rod[1] != "broken":
                raise _BizError(f"{slot} 号鱼竿没坏，不用修喵~")
            bal = await self._balance(session, user_id)
            if bal < self.REPAIR_COST:
                raise _BizError(
                    f"积分不足喵~ 修鱼竿需要 {self.REPAIR_COST} 积分，你只有 {bal} 积分"
                )
            await self._add_points(session, user_id, -self.REPAIR_COST, "repair_rod")
            await session.execute(
                text("UPDATE fishing_rods SET status='idle' WHERE id=:i"), {"i": rod[0]}
            )
            new_bal = await self._balance(session, user_id)
            return True, (
                f"🔧 {slot} 号鱼竿修好啦！花费 {self.REPAIR_COST} 积分，"
                f"当前积分：{new_bal} 喵~"
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("钓鱼排行")
    async def fishing_rank(self, event: AstrMessageEvent):
        """/钓鱼排行 —— 显示累计卖鱼收入前十名"""
        ok_gate, msg_gate = await self._check_group_gate(event, "钓鱼排行")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return

        async def fn(session):
            rows = (await session.execute(text(
                "SELECT s.user_id, COALESCE(NULLIF(u.user_name, ''), s.user_id), s.total_income "
                "FROM fishing_stats s LEFT JOIN users u ON u.user_id = s.user_id "
                "WHERE s.total_income > 0 ORDER BY s.total_income DESC LIMIT :n"
            ), {"n": self.FISHING_RANK_SIZE})).all()
            if not rows:
                raise _BizError("还没有人有卖鱼收入喵~ 快去 /挂机钓鱼 抢占榜首！")
            medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, len(rows) + 1)]
            lines = [f"🐟 钓鱼总收入排行 TOP{len(rows)}"]
            for i, (uid, name, income) in enumerate(rows):
                lines.append(f"{medals[i]} {name} —— {int(income)} 积分")
            return True, "\n".join(lines), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("钓鱼统计")
    async def fishing_stats_cmd(self, event: AstrMessageEvent):
        """/钓鱼统计 —— 查看今日次数、鱼饵消耗、累计收入、最高价值鱼与称号"""
        ok_gate, msg_gate = await self._check_group_gate(event, "钓鱼统计")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()

        async def fn(session):
            await self._fishing_ensure_stats(session, user_id)
            row = (await session.execute(text(
                "SELECT total_caught, total_income, total_baits_used, today_count, "
                "lucky_day_expire FROM fishing_stats WHERE user_id=:u"
            ), {"u": user_id})).first()
            collected = {str(r[0]) for r in (await session.execute(text(
                "SELECT fish_name FROM fishing_collection WHERE user_id=:u"
            ), {"u": user_id})).all()}
            # 最高价值鱼：从图鉴里按售价取最高
            best_line = "暂无"
            if collected:
                best = max(collected, key=lambda n: FISH_POOL.get(n, (0,))[0])
                best_line = f"{best}（{FISH_POOL[best][0]}积分）"
            # 称号判定（烛心持有者 / 闲鱼之王 / 至高传说之主 / 万物之主）
            titles: list[str] = []
            if "烛心" in collected:
                titles.append("烛心持有者")
            if "闲鱼" in collected:
                titles.append("闲鱼之王")
            if {"烛心", "闲鱼"} <= collected:
                rewarded = (await session.execute(text(
                    "SELECT 1 FROM point_transactions WHERE user_id=:u "
                    "AND operation='钓鱼至高奖励'"
                ), {"u": user_id})).first()
                if rewarded:
                    titles.append("至高传说之主")
            if len(collected) >= len(FISH_POOL):
                rewarded = (await session.execute(text(
                    "SELECT 1 FROM point_transactions WHERE user_id=:u "
                    "AND operation='钓鱼集齐奖励'"
                ), {"u": user_id})).first()
                if rewarded:
                    titles.append("万物之主")
            lines = [
                "📊 钓鱼统计",
                f"今日钓鱼：{int(row[3] or 0)} 次",
                f"累计钓鱼：{int(row[0] or 0)} 条（消耗鱼饵 {int(row[2] or 0)} 个）",
                f"累计卖鱼收入：{int(row[1] or 0)} 积分",
                f"最高价值鱼：{best_line}",
                f"图鉴进度：{len(collected)}/{len(FISH_POOL)} 种",
            ]
            lucky_expire = float(row[4]) if row[4] else 0.0
            if lucky_expire > time.time():
                remain = int((lucky_expire - time.time()) / 60)
                lines.append(f"🍀 幸运日 buff 剩余 {remain} 分钟（必定上钩）")
            if titles:
                lines.append(f"🎖 称号：{'、'.join(titles)}")
            else:
                lines.append("🎖 称号：暂无（钓到烛心/闲鱼或集齐图鉴可获得）")
            return True, "\n".join(lines), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)


# 依赖声明（AstrBot 插件规范：文件末尾声明额外依赖）
__requirements__ = ["apscheduler"]
