# -*- coding: utf-8 -*-
"""
AstrBot 积分游戏插件
=========================
功能：幸运转盘 / 闯关答题 / BOSS 战 / 大乐透 / 谁是卧底 / 签到排行
特性：全群积分数据互通、全局排行榜、WebUI 管理面板、群黑白名单（默认全部关闭）

作者：Zxin_Pro    版本：1.5.6
仓库：https://github.com/Zxin-Pro/astrbot_plugin_point_games
"""

import asyncio
import json
import random
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import text

# ---------- AstrBot 框架导入 ----------
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import EventMessageType, PermissionType
from astrbot.api.message_components import At, AtAll, Plain
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
#  玩法帮助注册表
#  【扩展玩法】以后新增玩法时：
#   1. 在下方 COMMAND_HELP 加一行 (指令, 说明)
#   2. 在类里新增一个 @filter.command 处理器 + 对应的内部方法
#   3. 需要定时任务就在 initialize() 里 add_job
#   介绍指令 /积分游戏 会自动展示，无需改动其他代码
# ============================================================
COMMAND_HELP: list[tuple[str, str]] = [
    ("/积分游戏", "玩法介绍与指令列表"),
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
    ("/签到", "每日签到，连签7天额外+20"),
    ("/积分", "查看自己的积分、收入、支出与签到信息"),
    ("/排行", "全服积分排行榜"),
    ("/加积分 /扣积分", "调整积分（仅配置页管理员QQ）"),
    ("/本群玩法 开|关", "群管理员开关本群玩法"),
    ("/玩法模式 白名单|黑名单", "全局模式切换"),
    ("/本群状态", "查看本群与全局状态"),
]


class _BizError(Exception):
    """业务错误：抛出后事务回滚并返回友好提示"""

    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


@register(
    name="积分游戏",
    author="Zxin_Pro",
    desc="幸运转盘/闯关答题/BOSS战/大乐透/谁是卧底/签到排行，全群数据互通，支持WebUI面板与群黑白名单",
    version="1.5.6",
    repo="https://github.com/Zxin-Pro/astrbot_plugin_point_games",
)
class PointGamesPlugin(Star):
    """积分游戏：发送 /积分游戏 查看全部玩法说明"""

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
    # 谁是卧底
    UC_MIN_PLAYERS = 4
    UC_MAX_PLAYERS = 12
    UC_DEFAULT_PLAYERS = 6
    UC_SPEECH_SECONDS = 120         # 每轮发言限时（秒）
    UC_VOTE_SECONDS = 60            # 投票限时（秒）
    UC_LOBBY_SECONDS = 120          # 报名等待（秒）
    DEFAULT_GROUP_MODE = "whitelist"
    FEATURES = {
        "enable_spin": True,
        "enable_quiz": True,
        "enable_boss": True,
        "enable_lottery": True,
        "enable_undercover": True,
        "enable_sign_in": True,
        "enable_ranking": True,
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
        "排行": ("enable_ranking", "积分排行"),
        "签到": ("enable_sign_in", "签到"),
        "积分": ("enable_ranking", "积分账户"),
    }

    # ---------- 表结构定义 ----------
    TABLE_DDL = [
        """CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            sign_in_date TEXT,
            sign_in_streak INTEGER DEFAULT 0
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
            create_time TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pt_user ON point_transactions(user_id)",
        """CREATE TABLE IF NOT EXISTS group_settings (
            group_id TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            updated_at TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS plugin_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS lottery_pool (
            period TEXT PRIMARY KEY,
            pool INTEGER DEFAULT 0
        )""",
    ]

    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context, config)
        # AstrBot 会把 _conf_schema.json 中的配置作为 dict 注入这里。
        # 运行时配置只在插件加载时读取，修改后重新加载插件即可生效。
        self.config = config or {}
        self._apply_runtime_config(self.config)
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._uc_jobs: dict[str, Any] = {}      # group_id -> apscheduler Job（卧底计时器）
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

    async def _ensure_user(self, session, user_id: str):
        """确保用户存在，不存在则插入默认行"""
        await session.execute(
            text("INSERT OR IGNORE INTO users(user_id) VALUES(:u)"), {"u": user_id}
        )

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
        # amount=0 时也允许记录一笔纯统计流水，但正常玩法不会这样调用。
        await session.execute(
            text(
                "INSERT INTO point_transactions(user_id, amount, operation, create_time) "
                "VALUES(:u, :a, :op, :t)"
            ),
            {"u": user_id, "a": amount, "op": operation, "t": time.time()},
        )

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
        """创建所有数据表（幂等）"""
        async with self._session() as session:
            async with session.begin():
                for ddl in self.TABLE_DDL:
                    await session.execute(text(ddl))
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
                        detail_lines.append(f"@{uid} 命中{cnt}个，奖金 {per} 积分")
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
            text_lines = (
                [f"🎰 大乐透开奖（{today}）", f"开奖号码：{' '.join(map(str, winning))}",
                 f"本期奖池：{pool} 积分"]
                + detail_lines
                + (["很遗憾，无人中奖，奖池累计到明天喵~"] if not detail_lines else [])
            )
            # 广播到当日所有购买过的群
            seen: set = set()
            for t in tickets:
                pid, gid = t.platform_id or "", t.group_id or ""
                if gid and (pid, gid) not in seen:
                    seen.add((pid, gid))
                    await self._send_to_group(pid, gid, "\n".join(text_lines), at_all=True)
            return True, "开奖完成", {"winning": winning, "pool": pool}

        await self._tx(fn)

    async def _maintenance(self):
        """每分钟维护：清理超时闯关会话、超时卧底游戏"""
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
            return True, "维护完成", None

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
                    "INSERT INTO group_settings(group_id, enabled, updated_at) VALUES(:g, :e, :t) "
                    "ON CONFLICT(group_id) DO UPDATE SET enabled=:e, updated_at=:t"
                ),
                {"g": group_id, "e": 1 if enable else 0, "t": time.time()},
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
    @filter.command("积分游戏")
    async def intro(self, event: AstrMessageEvent):
        """/积分游戏 —— 玩法介绍与指令列表"""
        lines = ["🎮 积分游戏 v1.5.6 by Zxin_Pro", "━━━━━━━━━━━━━━"]
        for cmd, desc in COMMAND_HELP:
            lines.append(f"📌 {cmd}  {desc}")
        lines += [
            "━━━━━━━━━━━━━━",
            "🌐 全群积分互通，排行榜为全服排名",
            "🖥️ WebUI 面板：AstrBot 面板 → 插件 → 积分游戏 → 积分游戏面板",
            "✨ 更多玩法开发中，敬请期待喵~",
        ]
        yield event.plain_result("\n".join(lines))

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
            if net >= 0:
                msg = f"{emoji} 转盘结果：{roll} 点！返还 {refund} 积分（净赚 +{net}）当前积分：{new_bal} 喵~"
            else:
                msg = f"{emoji} 转盘结果：{roll} 点！返还 {refund} 积分（亏损 {abs(net)}）当前积分：{new_bal} 喵~"
            return True, msg, None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

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
                            "SELECT user_id, SUM(damage) AS dmg FROM boss_damage "
                            "GROUP BY user_id ORDER BY dmg DESC"
                        )
                    )
                ).all()
                total_dmg = sum(int(s[1]) for s in stats)
                pool = int(row[1])
                shares = []
                for uid, dmg in stats:
                    share = int(pool * int(dmg) / total_dmg) if total_dmg else 0
                    if share > 0:
                        await self._add_points(session, uid, share, "BOSS击败分红")
                        shares.append((uid, share))
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
                ), None
            await session.execute(
                text("UPDATE boss SET current_hp=:hp WHERE id=1"), {"hp": hp}
            )
            return True, f"⚔️ 你对 BOSS 造成了 {damage} 点伤害！BOSS 剩余血量：{hp}/{self.BOSS_MAX_HP}", None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

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
                        "SELECT user_id, SUM(damage) AS dmg FROM boss_damage "
                        "WHERE attack_time >= :t GROUP BY user_id ORDER BY dmg DESC LIMIT 10"
                    ),
                    {"t": today_start},
                )
            ).all()
            if not rows:
                return True, "今天还没有人攻击 BOSS 喵~ 发送 /攻击 抢首刀！", None
            lines = ["👹 今日 BOSS 伤害排行 TOP10"]
            for i, r in enumerate(rows, 1):
                lines.append(f"{i}. {r[0]} —— {int(r[1])} 伤害")
            return True, "\n".join(lines), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    # ============================================================
    #  功能四：大乐透
    # ============================================================
    @filter.command("买彩票")
    async def lottery_buy(self, event: AstrMessageEvent):
        """/买彩票 [积分数量] —— 购买1注随机号码，每人每期限购10注"""
        ok_gate, msg_gate = await self._check_group_gate(event, "买彩票")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()
        cost = self.LOTTERY_DEFAULT_COST
        args = self._strip_command(event, "买彩票")
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
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

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
                await self._send_to_group(platform_id, group_id, f"@{uid} 私聊发词失败，你的词是：【{word}】（注意保密喵~）")
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
        for variant in (command, cmd, "/" + cmd):
            if variant and variant in text:
                text = text.split(variant, 1)[1]
                break
        # 全角空格转半角，去掉首尾与连续空白
        return " ".join(text.replace("　", " ").split())

    # ============================================================
    #  功能六：管理指令 / 签到 / 排行
    # ============================================================
    async def _grant_points(self, event: AstrMessageEvent, negative: bool):
        """/加积分 @用户 数量 或 /扣积分 @用户 数量（仅配置页管理员QQ可用）"""
        sender = str(event.get_sender_id())
        if sender not in self.ADMIN_QQ:
            yield event.plain_result("仅配置的管理员可使用该指令喵~ 请在插件配置页「管理员QQ」中添加")
            return
        user_id = self._extract_at(event)
        cmd = "扣积分" if negative else "加积分"
        args = self._strip_command(event, cmd)
        parts = args.split()
        amount = None
        for p in parts:
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

    @filter.command("扣积分")
    async def grant_sub(self, event: AstrMessageEvent):
        async for result in self._grant_points(event, negative=True):
            yield result

    @filter.command("积分")
    async def points(self, event: AstrMessageEvent):
        """查看全局互通的个人积分账户"""
        user_id = event.get_sender_id()

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            await self._ensure_user(session, user_id)
            row = (await session.execute(text(
                "SELECT balance, total_earned, total_spent, sign_in_streak "
                "FROM users WHERE user_id=:u"
            ), {"u": user_id})).first()
            return True, (
                f"💰 用户：{user_id}\n"
                f"当前积分：{int(row[0])}\n"
                f"累计收入：{int(row[1])}\n"
                f"累计支出：{int(row[2])}\n"
                f"连续签到：{int(row[3])} 天"
            ), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

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
                    text("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
                )
            ).all()
            if not rows:
                return True, "排行榜还空着呢，快去赚积分喵~", None
            lines = ["🏆 全服积分排行榜 TOP10"]
            medals = ["🥇", "🥈", "🥉"]
            for i, r in enumerate(rows, 1):
                prefix = medals[i - 1] if i <= 3 else f"{i}."
                lines.append(f"{prefix} {r[0]} —— {int(r[1])} 积分")
            return True, "\n".join(lines), None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

    @filter.command("签到")
    async def sign_in(self, event: AstrMessageEvent):
        """/签到 —— 每日签到，连续7天额外+20"""
        ok_gate, msg_gate = await self._check_group_gate(event, "签到")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        user_id = event.get_sender_id()
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        async def fn(session):
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            await self._ensure_user(session, user_id)
            row = (
                await session.execute(
                    text("SELECT sign_in_date, sign_in_streak FROM users WHERE user_id=:u"),
                    {"u": user_id},
                )
            ).first()
            if row and row[0] == today:
                raise _BizError("今天已经签到过啦，明天再来喵~")
            streak = 1
            if row and row[0] == yesterday:
                streak = int(row[1]) + 1
            reward = random.randint(self.SIGN_IN_MIN, self.SIGN_IN_MAX)
            bonus = 0
            if streak % 7 == 0:
                bonus = self.SIGN_IN_WEEK_BONUS
            await self._add_points(session, user_id, reward + bonus, "每日签到")
            await session.execute(
                text(
                    "UPDATE users SET sign_in_date=:d, sign_in_streak=:s WHERE user_id=:u"
                ),
                {"d": today, "s": streak, "u": user_id},
            )
            msg = f"📝 签到成功！+{reward} 积分，已连续签到 {streak} 天"
            if bonus:
                msg += f"\n🎉 连续签到 {streak} 天额外 +{bonus} 积分！"
            bal = await self._balance(session, user_id)
            msg += f"\n当前积分：{bal} 喵~"
            return True, msg, None

        ok, msg, _ = await self._tx(fn)
        yield event.plain_result(msg)

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
        ctx.register_web_api("/point_games/api/boss", self._web_boss, ["GET"], "BOSS 状态")
        ctx.register_web_api("/point_games/api/lottery", self._web_lottery, ["GET"], "彩票信息")
        ctx.register_web_api("/point_games/api/transactions", self._web_transactions, ["GET"], "积分流水")
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
                    text("SELECT user_id, balance, total_earned, total_spent, sign_in_streak FROM users ORDER BY balance DESC LIMIT 50")
                )
            ).all()
            return True, "ok", [
                {"user_id": r[0], "balance": int(r[1]), "total_earned": int(r[2]),
                 "total_spent": int(r[3]), "sign_in_streak": int(r[4])}
                for r in rows
            ]

        ok, _, data = await self._tx(fn)
        return json_response(data if data else [])

    async def _web_users(self):
        from astrbot.api.web import json_response, request as web_request
        try:
            req = web_request
            params = req.query if hasattr(req, "query") else {}
        except Exception:
            params = {}
        page = max(1, int(params.get("page", 1)))
        page_size = min(50, max(5, int(params.get("page_size", 20))))
        keyword = str(params.get("search", "") or "").strip()

        async def fn(session):
            if keyword:
                total = (
                    await session.execute(text("SELECT COUNT(*) FROM users WHERE user_id LIKE :k"), {"k": f"%{keyword}%"})
                ).first()
                rows = (
                    await session.execute(
                        text("SELECT user_id, balance, total_earned, total_spent, sign_in_date, sign_in_streak FROM users WHERE user_id LIKE :k ORDER BY balance DESC LIMIT :n OFFSET :o"),
                        {"k": f"%{keyword}%", "n": page_size, "o": (page - 1) * page_size},
                    )
                ).all()
            else:
                total = (await session.execute(text("SELECT COUNT(*) FROM users"))).first()
                rows = (
                    await session.execute(
                        text("SELECT user_id, balance, total_earned, total_spent, sign_in_date, sign_in_streak FROM users ORDER BY balance DESC LIMIT :n OFFSET :o"),
                        {"n": page_size, "o": (page - 1) * page_size},
                    )
                ).all()
            return True, "ok", {
                "total": int(total[0]),
                "page": page,
                "page_size": page_size,
                "users": [
                    {"user_id": r[0], "balance": int(r[1]), "total_earned": int(r[2]),
                     "total_spent": int(r[3]), "sign_in_date": r[4], "sign_in_streak": int(r[5])}
                    for r in rows
                ],
            }

        ok, _, data = await self._tx(fn)
        return json_response(data if data else {})

    async def _web_boss(self):
        from astrbot.api.web import json_response

        async def fn(session):
            await self._ensure_boss_reset(session)
            row = (await session.execute(text("SELECT current_hp, pool, reset_date FROM boss WHERE id=1"))).first()
            agg = (await session.execute(text("SELECT COALESCE(SUM(damage),0), COUNT(DISTINCT user_id) FROM boss_damage"))).first()
            top = (
                await session.execute(
                    text("SELECT user_id, SUM(damage) AS dmg FROM boss_damage GROUP BY user_id ORDER BY dmg DESC LIMIT 10")
                )
            ).all()
            return True, "ok", {
                "hp": int(row[0]) if row else 0,
                "max_hp": self.BOSS_MAX_HP,
                "pool": int(row[1]) if row else 0,
                "reset_date": row[2] if row else None,
                "today_damage": int(agg[0]),
                "participants": int(agg[1]),
                "top": [{"user_id": r[0], "damage": int(r[1])} for r in top],
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
                    text("SELECT user_id, amount, operation, create_time FROM point_transactions ORDER BY id DESC LIMIT :n"),
                    {"n": limit},
                )
            ).all()
            return True, "ok", [
                {"user_id": r[0], "amount": int(r[1]), "operation": r[2],
                 "time": datetime.fromtimestamp(float(r[3])).strftime("%Y-%m-%d %H:%M:%S") if r[3] else ""}
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
        except Exception as e:
            return error_response(f"参数错误：{e}")
        if not group_id:
            return error_response("缺少 group_id")

        async def fn(session):
            await session.execute(
                text(
                    "INSERT INTO group_settings(group_id, enabled, updated_at) VALUES(:g, :e, :t) "
                    "ON CONFLICT(group_id) DO UPDATE SET enabled=:e, updated_at=:t"
                ),
                {"g": group_id, "e": enabled, "t": time.time()},
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


# 依赖声明（AstrBot 插件规范：文件末尾声明额外依赖）
__requirements__ = ["apscheduler"]
