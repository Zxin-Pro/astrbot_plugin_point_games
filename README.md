# astrbot_plugin_point_games

<div align="center">

**AstrBot 积分游戏合集插件**

幸运转盘 · 闯关答题 · BOSS战 · 大乐透 · 谁是卧底 · 数字炸弹 · 速算挑战 · 抽卡 · 钓鱼 · 银行 · 转账 · 收税 · WebUI 面板

版本：v2.18.6 ｜ 全群数据互通 ｜ 支持 WebUI 可视化管理

</div>

---

## 一、插件简介

这是一个面向 QQ 群聊的 **积分游戏合集插件**，基于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 开发。

- 🎮 **一个插件十几种玩法**：转盘、答题、BOSS、乐透、卧底、炸弹、速算、抽卡、钓鱼……全部集成
- 🏦 **完整经济系统**：积分流水、转账（带手续费）、银行存款日结利息、每日自动收税
- 🌐 **全群数据互通**：积分全服共享，不区分群
- ⚙️ **WebUI 可视化管理**：面板加/扣积分、查看数据，配置页分类清晰、在线修改
- 🔒 **群黑白名单**：白名单/黑名单两种模式，群管理员可独立开关本群玩法
- 💾 **数据持久化**：所有状态落库（SQLite），插件重启/更新不丢失

## 二、功能列表

### 💰 积分与签到

| 指令 | 说明 |
|---|---|
| `/积分` | 查看自己的积分、收入、支出与签到信息（含银行存款） |
| `/查询` | 同上 |
| `/查积分 @玩家` | 查询其他玩家的积分信息 |
| `/排行` | 全服积分排行榜 |
| `签到` / `jrzj` / `今日座驾` | 群内触发每日座驾并完成积分签到（连续7天有额外奖励），签到成功后附带输出**今日运势海报** |
| `群活跃奖励` | 每日22:00自动结算群内发言前三名，奖励 50/30/10 积分 |

### 🎡 玩法指令

| 指令 | 说明 |
|---|---|
| `/转盘 [积分]` | 幸运转盘，最高5倍返还 |
| `/闯关` | 答题闯关，答对得分答错扣分 |
| `/攻击` | 消耗5积分打BOSS，伤害100-500 |
| `/BOSS状态` | 查看BOSS血量与今日战况 |
| `/BOSS排行` | 今日伤害前十 |
| `/买彩票 [积分]` | 每日20:00开奖，每期限购10注 |
| `/彩票奖池` | 查看当前奖池与参与人数 |
| `/卧底开始 [人数]` | 谁是卧底（群聊，需报名） |
| `/加入卧底` | 报名卧底游戏 |
| `/投票 @某人` | 投票阶段投出卧底 |
| `/卧底结束` | 管理员强制结束 |
| `/炸弹开始` | 数字炸弹（1-100猜数字，猜中者-30，其他人+5） |
| `/猜 [数字]` | 炸弹游戏中猜数字 |
| `/炸弹结束` | 强制结束炸弹游戏（仅管理员） |
| `/速算` | 速算挑战（答对得5/15/30积分，每天10次） |
| `/掷骰 @群友` | 与群友比大小，胜者+10，平局各+5 |
| `/抽卡` | 消耗10积分抽卡（N/R/SR/SSR） |
| `/图鉴` | 查看已收集的卡牌和进度 |

### 🎣 钓鱼系统

| 指令 | 说明 |
|---|---|
| `/买鱼竿` | 200积分购买鱼竿（最多5根） |
| `/买鱼饵 [数量]` | 10积分/个购买鱼饵 |
| `/挂机钓鱼 [编号]` | 鱼竿挂机，每30分钟判定一次，全群播报事件 |
| `/收鱼` | 收取挂机钓到的鱼进鱼篓 |
| `/卖鱼` | 一键卖出鱼篓里所有鱼 |
| `/鱼图鉴` | 查看鱼类收集进度（共102种） |
| `/鱼竿列表` | 查看每根鱼竿状态 |
| `/修鱼竿 [编号]` | 50积分修理损坏的鱼竿 |
| `/钓鱼排行` | 累计卖鱼收入前十名 |
| `/钓鱼统计` | 查看自己的钓鱼数据与称号 |

### 🏦 银行 / 转账 / 税收

| 指令 | 说明 |
|---|---|
| `/开户` | 开通银行账户（免费，享每日5%活期利息） |
| `/存钱 [积分]` | 将钱包积分存入银行 |
| `/取钱 [积分]` | 从银行取出积分到钱包 |
| `/我的银行` | 查看活期余额与累计利息 |
| `/转账 @群友/QQ号 [积分]` | 向群友转账（1-5000，10%手续费，每日10次，10秒冷却） |
| `/兑换礼品` | 花费10000积分兑换小礼品一份（兑换后联系管理员领取） |
| `每日收税` | 凌晨0点自动收取余额0.1%税款（余额≥1000才扣，自动执行） |

### 🛠 管理指令

| 指令 | 说明 |
|---|---|
| `/加积分 @玩家 数量` | 增加积分（仅配置页管理员QQ） |
| `/减积分 @玩家 数量` | 扣除积分（仅管理员QQ） |
| `/清除数据 @玩家` | 清除指定玩家账户和流水（仅管理员） |
| `/初始化 @玩家` | 同上 |
| `/本群玩法 开\|关` | 群管理员开关本群玩法 |
| `/玩法模式 白名单\|黑名单` | 全局模式切换 |
| `/本群状态` | 查看本群与全局状态 |
| `/帮助` | 玩法介绍与指令列表 |

### 💖 赞助系统（仅私聊）

| 指令 | 说明 |
|---|---|
| `/赞助` | 查看赞助积分方式 |
| `/赞助审核` | 提交赞助申请（引用订单截图） |
| `/赞助通过 [QQ] [积分]` | 管理员审核通过 |
| `/赞助拒绝 [QQ] [理由]` | 管理员拒绝申请 |
| `/赞助列表` | 查看待审核申请（管理员） |

## 三、配置说明

在 AstrBot 管理面板 → 插件管理 → 本插件 → 配置 中在线修改。**所有配置项按分类排列，key 与默认值如下：**

### 📁 基础配置

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `admin_qq` | list | `[]` | 管理员QQ号，逗号分隔；可用加/扣积分等管理指令 |
| `fee_receiver` | string | `""` | 手续费接收者QQ；留空自动取第一个管理员 |
| `group_mode` | string | `whitelist` | 群玩法默认模式：whitelist=默认关闭 / blacklist=默认开启 |
| `group_whitelist` | list | `[]` | 白名单群号列表 |
| `group_blacklist` | list | `[]` | 黑名单群号列表 |
| `command_cooldown` | int | `3` | 普通指令冷却秒数 |

### 📁 功能开关

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enable_spin` | bool | `true` | 启用幸运转盘 |
| `enable_quiz` | bool | `true` | 启用闯关答题 |
| `enable_boss` | bool | `true` | 启用BOSS战 |
| `enable_lottery` | bool | `true` | 启用大乐透 |
| `enable_undercover` | bool | `true` | 启用谁是卧底 |
| `enable_bomb` | bool | `true` | 启用数字炸弹 |
| `enable_math` | bool | `true` | 启用速算挑战 |
| `enable_card` | bool | `true` | 启用抽卡系统 |
| `enable_fishing` | bool | `true` | 启用钓鱼系统 |
| `enable_sign_in` | bool | `true` | 启用每日签到 |
| `enable_ranking` | bool | `true` | 启用积分查询和排行榜 |
| `enable_activity` | bool | `true` | 启用群活跃奖励 |
| `enable_transfer` | bool | `true` | 启用积分转账 |
| `enable_tax` | bool | `true` | 启用每日自动收税 |
| `enable_bank` | bool | `true` | 启用银行系统 |

### 📁 经济系统

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `spin_default_cost` | int | `10` | 转盘默认消耗积分 |
| `spin_weight_0` | int | `40` | 转盘返还0倍的概率权重 |
| `spin_weight_50` | int | `30` | 转盘返还0.5倍的概率权重 |
| `spin_weight_80` | int | `15` | 转盘返还0.8倍的概率权重 |
| `spin_weight_120` | int | `10` | 转盘返还1.2倍的概率权重 |
| `spin_weight_200` | int | `4` | 转盘返还2倍的概率权重 |
| `spin_weight_500` | int | `1` | 转盘返还5倍的概率权重 |
| `spin_rate_0` | float | `0.0` | 转盘0倍档返还倍率 |
| `spin_rate_50` | float | `0.5` | 转盘0.5倍档返还倍率 |
| `spin_rate_80` | float | `0.8` | 转盘0.8倍档返还倍率 |
| `spin_rate_120` | float | `1.2` | 转盘1.2倍档返还倍率 |
| `spin_rate_200` | float | `2.0` | 转盘2倍档返还倍率 |
| `spin_rate_500` | float | `5.0` | 转盘5倍档返还倍率 |
| `dice_daily_limit` | int | `5` | 掷骰每日次数上限 |

### 📁 银行系统

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `bank_interest_rate` | float | `0.05` | 活期利率（每日），0.05=5%，凌晨0点结算到钱包 |
| `bank_admin_extra_rate` | float | `0.01` | 管理员额外收益：存款总额的1%/天发给 fee_receiver |
| `bank_report_time` | string | `"21:00"` | 每日银行流水报告时间（HH:MM） |
| `bank_report_group` | string | `""` | 流水报告发送群聊ID，逗号分隔；留空不发送 |

### 📁 税收系统

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `tax_rate` | float | `0.001` | 税率（余额的百分比），0.001=0.1%，向下取整 |
| `tax_min_balance` | int | `1000` | 起征余额，达到才扣税 |

### 📁 钓鱼系统

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `fishing_broadcast_groups` | list | `[]` | 播报群号列表；留空播报到挂机所在群（失败自动多重兜底） |

### 📁 闯关系统

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `quiz_timeout` | int | `60` | 每道题限时秒数 |
| `quiz_streak_bonus_every` | int | `5` | 连续答对多少题触发奖励 |
| `quiz_streak_bonus` | int | `20` | 连击额外奖励 |
| `quiz_wrong_penalty` | int | `5` | 答错扣分 |

### 📁 签到与群活跃

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `sign_in_min` | int | `1` | 签到随机积分下限 |
| `sign_in_max` | int | `10` | 签到随机积分上限 |
| `sign_in_week_bonus` | int | `20` | 连续签到每满7天额外奖励 |
| `activity_settle_hour` | int | `22` | 群活跃奖励结算小时 |
| `activity_settle_minute` | int | `0` | 群活跃奖励结算分钟 |
| `leaderboard_broadcast_hour` | int | `12` | 全服排行榜自动播报小时 |
| `leaderboard_broadcast_minute` | int | `0` | 全服排行榜自动播报分钟 |

### 📁 BOSS战

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `boss_max_hp` | int | `10000` | BOSS初始血量 |
| `boss_pool` | int | `500` | BOSS死亡分红积分池 |
| `attack_cost` | int | `5` | 每次攻击消耗积分 |
| `attack_cooldown` | int | `10` | 攻击冷却秒数 |
| `attack_damage_min` | int | `100` | 最低攻击伤害 |
| `attack_damage_max` | int | `500` | 最高攻击伤害 |
| `boss_reset_hour` | int | `0` | BOSS重置时间：小时 |
| `boss_reset_minute` | int | `0` | BOSS重置时间：分钟 |

### 📁 大乐透

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `lottery_default_cost` | int | `10` | 每注消耗积分 |
| `lottery_limit_per_day` | int | `10` | 每人每期限购注数 |
| `lottery_base_pool` | int | `100` | 奖池保底积分 |
| `lottery_prize_3` | float | `0.1` | 命中3个时奖池比例 |
| `lottery_prize_4` | float | `0.3` | 命中4个时奖池比例 |
| `lottery_prize_5` | float | `0.6` | 命中5个时奖池比例 |
| `lottery_draw_hour` | int | `20` | 开奖时间：小时 |
| `lottery_draw_minute` | int | `0` | 开奖时间：分钟 |

### 📁 谁是卧底

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `uc_min_players` | int | `4` | 卧底最少人数 |
| `uc_max_players` | int | `12` | 卧底最多人数 |
| `uc_default_players` | int | `6` | 卧底默认人数 |
| `uc_speech_seconds` | int | `120` | 每人发言限时秒数 |
| `uc_vote_seconds` | int | `60` | 投票限时秒数 |
| `uc_lobby_seconds` | int | `120` | 报名等待秒数 |

### 📁 数字炸弹

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `bomb_min` | int | `1` | 炸弹范围最小值 |
| `bomb_max` | int | `100` | 炸弹范围最大值 |
| `bomb_penalty` | int | `30` | 猜中扣分 |
| `bomb_reward` | int | `5` | 其他参与者奖励 |

### 📁 速算挑战

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `math_daily_limit` | int | `10` | 每日限玩次数 |
| `math_timeout` | int | `15` | 答题限时秒数 |
| `math_reward_easy` | int | `5` | 简单题奖励 |
| `math_reward_medium` | int | `15` | 中等题奖励 |
| `math_reward_hard` | int | `30` | 困难题奖励 |

### 📁 抽卡系统

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `card_cost` | int | `10` | 每次抽卡消耗积分 |
| `card_complete_reward` | int | `100` | 集齐所有稀有度奖励 |

### 📁 今日运势

签到成功后自动附带输出今日运势海报（融合自 [astrbot_plugin_jrys](https://github.com/NINIYOYYO/astrbot_plugin_jrys)，无独立指令）。同一用户当天运势固定；节假日自动提升大吉概率；图片生成失败时自动回退文字运势。

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enable_fortune` | bool | `true` | 启用今日运势（功能开关分类内） |
| `font_name` | string | `千图马克手写体.ttf` | 海报字体文件（插件 font/ 目录下） |
| `img_width` | int | `1080` | 海报宽度（像素） |
| `img_height` | int | `1920` | 海报高度（像素） |
| `avatar_size` | list | `[150, 150]` | 头像尺寸 [宽,高] |
| `avatar_position` | list | `[60, 1350]` | 头像位置 [x,y] |
| `avatar_cache_expiration` | int | `86400` | 头像缓存时长（秒） |
| `date_y_position` | int | `1300` | 日期文字Y坐标 |
| `summary_y_position` | int | `1400` | 运势摘要Y坐标 |
| `lucky_star_y_position` | int | `1500` | 幸运星Y坐标 |
| `sign_text_y_position` | int | `1600` | 签文Y坐标 |
| `unsign_text_y_position` | int | `1700` | 解签Y坐标 |
| `warning_text_y_position` | int | `1850` | 免责声明Y坐标 |
| `pre_cache_background_images` | bool | `false` | 预缓存背景图（出图更快） |
| `pre_cache_concurrency` | int | `3` | 预缓存并发数 |
| `cleanup_background_downloads` | bool | `true` | 清理按需下载的背景图 |
| `fixed_daily_fortune` | bool | `true` | 每日固定运势（同人同天结果一致） |
| `holiday_rates_enabled` | bool | `true` | 节假日运势高爆率 |
| `holidays` | list | `01-01` 等5个 | 节假日日期列表（MM-DD） |
| `normal_rates` | object | `40/40/20` | 日常爆率权重（大吉/中吉/凶运） |
| `holiday_rates` | object | `85/15/0` | 节假日爆率权重（大吉/中吉/凶运） |

### 📁 赞助系统

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `sponsor_qrcode` | file | `[]` | 赞助收款码图片（用户私聊 /赞助 时直接收到） |
| `sponsor_rate` | int | `100` | 积分兑换率（1元=N积分） |
| `sponsor_admin_qq` | list | `[]` | 赞助审核管理员QQ |
| `sponsor_group_id` | string | `""` | 赞助申请提醒群ID，留空仅私聊通知 |

### 📁 每日座驾

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `car_pool` | list | 内置5辆保时捷 | 每日座驾车辆池，每行一辆车 |
| `reply_template` | text | `🚗 {user_name}…` | 抽车后的回复模板，支持 `{user_name}` `{car}` `{date}` |

> 💡 配置修改后，在面板点击保存并重载插件即可生效。

## 四、数据库结构

数据存储于 AstrBot 数据目录下的 SQLite 数据库，共 25 张表：

| 表名 | 字段 | 说明 |
|---|---|---|
| `users` | user_id(PK), user_name, balance, total_earned, total_spent, sign_in_date, sign_in_streak, reward_reminded, gift_redeemed | 用户账户与余额 |
| `point_transactions` | id, user_id, amount, operation, earned, spent, balance_after, create_time | 积分流水（收入/支出/操作类型） |
| `cooldown` | user_id(PK), last_command_time | 指令冷却 |
| `group_settings` | group_id(PK), enabled, updated_at, platform_id | 群玩法开关状态 |
| `plugin_config` | key(PK), value | 插件内部持久化配置（如全局模式） |
| `dice_records` | user_id+date(PK), count | 掷骰每日次数 |
| `daily_cars` | user_id+date(PK), car_name | 每日座驾记录 |
| `quiz_sessions` | user_id(PK), question_index, streak, question_data, expire_time | 闯关答题进行中的会话 |
| `boss` | id(PK), current_hp, reset_date, pool | BOSS当前血量与分红池 |
| `boss_damage` | id, user_id, damage, attack_time | 玩家伤害记录 |
| `lottery` | id, user_id, numbers, cost, period, platform_id, group_id | 彩票购买记录 |
| `lottery_pool` | period(PK), pool | 每期奖池 |
| `undercover_games` | id, group_id, status, players, civilian_word, undercover_word, undercover_id, votes, round, current_speaker_index, phase, platform_id, updated_at | 卧底游戏状态 |
| `bomb_games` | group_id(PK), target_number, min_range, max_range, participants, platform_id, created_at | 炸弹游戏状态 |
| `math_challenges` | user_id(PK), question, answer, difficulty, expire_time | 速算进行中的题目 |
| `math_daily_count` | user_id+date(PK), count | 速算每日次数 |
| `cards` | user_id+card_name(PK), rarity, count | 抽卡收集 |
| `activity_stats` | group_key+date+user_id(PK), user_name, count | 群活跃发言统计（落库防重启丢失） |
| `sponsor_requests` | id, user_id, amount, status, admin_id, create_time, handle_time, remark | 赞助申请 |
| `fishing_rods` | id, user_id, slot, status, platform_id, group_id, created_at | 鱼竿（挂机时记录群来源用于播报） |
| `fishing_baits` | user_id(PK), count | 鱼饵数量 |
| `fishing_inventory` | id, user_id, fish_name, count | 鱼篓（未卖出的鱼） |
| `fishing_pending` | id, user_id, fish_name, catch_time | 挂机钓到待收取的鱼 |
| `fishing_collection` | user_id+fish_name(PK), first_time | 鱼类图鉴收集进度 |
| `fishing_stats` | user_id(PK), total_caught, total_income, total_baits_used, lucky_day, lucky_day_expire, today_count, today_date | 钓鱼统计与幸运日buff |
| `transfer_records` | id, from_user, to_user, amount, fee, total, create_time | 转账记录（含每日次数统计） |
| `tax_records` | id, user_id, amount, date, create_time | 每日收税记录 |
| `bank_accounts` | user_id(PK), current_balance, total_interest, created_at | 银行账户 |
| `bank_transactions` | id, user_id, type, amount, create_time | 银行流水（deposit/withdraw/interest/admin_extra） |

> 部分表配有索引（idx_*）加速查询，此处不一一列出。

## 五、常见问题

<details>
<summary><b>1. 钓鱼/收税/排行榜不播报怎么办？</b></summary>

按以下顺序排查：
1. 确认插件配置页 `enable_fishing` 等开关已打开；
2. 在配置页 `fishing_broadcast_groups` 直接填写播报群号（定向发送，最可靠）；
3. 查看日志搜索「钓鱼判定」，确认挂机判定在正常执行；
4. 若仍失败，插件会自动走多重兜底（竿里记录的群 → 所有平台实例 → 已开启玩法的群），查看日志中的「兜底路径」记录。

</details>

<details>
<summary><b>2. 修改配置后为什么不生效？</b></summary>

配置页修改并保存后，需要在 AstrBot 插件管理里**重载插件**才会应用（定时任务时间类配置尤其如此）。所有配置项都支持在线修改，重载后立即生效，数据不会丢失。
</details>

<details>
<summary><b>3. /加积分 提示无权限？</b></summary>

只有配置页「基础配置 → 管理员QQ号」中填写的 QQ 才能使用管理指令。多个QQ用逗号分隔，保存后重载插件。
</details>

<details>
<summary><b>4. 群里玩法开关不生效 / 想让某些群默认开启？</b></summary>

全局模式由 `group_mode` 控制：`whitelist`（默认，仅白名单群可玩）或 `blacklist`（除黑名单外都可玩）。切换可用指令 `/玩法模式 白名单|黑名单` 或改配置。单群开关由群管理员执行 `/本群玩法 开|关`。
</details>

<details>
<summary><b>5. 转账/银行/收税的积分去哪了？</b></summary>

- 转账手续费 10% 流入 `fee_receiver`（留空则给第一个管理员）；
- 每日收税扣除的税款同样流入手续费接收账户，可在流水（operation=tax_income）中核对；
- 银行利息凌晨0点结算到**钱包余额**（不进银行余额），管理员额外收益单独一笔发放。
</details>

<details>
<summary><b>6. 插件更新后群活跃奖励/游戏数据会丢失吗？</b></summary>

不会。群活跃统计（activity_stats）、钓鱼进度、银行账户等重要状态全部实时落库，插件重启或更新后自动恢复。
</details>

<details>
<summary><b>7. 转账提示「数据库开小差」或其他报错？</b></summary>

请先升级到 v2.15.4 及以上版本（已修复转账闭包变量问题）。仍报错请附上日志提 Issue。
</details>

<details>
<summary><b>8. 签到没有运势海报 / 只有文字运势？</b></summary>

海报生成依赖 `Pillow`、`aiohttp`、`aiofiles`（见 requirements.txt），缺失或头像/背景图下载失败时自动回退**文字运势**，不影响签到积分。可在配置页开启「预缓存背景图」加快出图；确认 `enable_fortune` 开关已打开。
</details>

## 六、更新日志

完整日志见 [CHANGELOG.md](./CHANGELOG.md)，近期版本：

| 版本 | 主要更新 |
|---|---|
| v2.19.0 | 融合今日运势插件（jrys）：签到附带运势海报，同日固定、节假日高爆率、失败回退文字 |
| v2.18.6 | 银行流水报告：新表 bank_transactions 存储存取/利息/管理员收益流水，每晚定时发送银行流水报告 |
| v2.18.5 | 修复新玩家（先玩过其他玩法）领不到首签送竿的问题 |
| v2.18.4 | 钓鱼播报群可定向配置（fishing_broadcast_groups） |
| v2.18.3 | 钓鱼播报多重路径兜底，彻底解决平台实例ID变动导致的静默失败 |
| v2.18.2 | 播报全链路日志，失败原因可排查 |
| v2.18.1 | 钓鱼爆率再上调（上钩70%、双鱼6%），长期挂机期望≈+4.5积分/次 |
| v2.18.0 | 新增银行系统：开户/存钱/取钱/每日利息/管理员额外收益/日结播报 |
| v2.17.0 | 每日自动收税 + 首次签到送鱼竿 |
| v2.15.8 | 钓鱼事件全群播报 |
| v2.15.5 | 至高传说鱼池加入满穗（10000积分稀有鱼） |
| v2.15.2 | 积分转账（10%手续费、每日限额、冷却） |
| v2.14.0 | 钓鱼系统上线（76种鱼+4条至高传说、图鉴、宝箱、幸运日） |
| v2.15.0 | 全部指令去掉「/积分」前缀，指令更简短 |
| v2.14.1 | 新增 /兑换礼品 |
| v1.0.0 | 首次发布：积分核心+转盘/答题/BOSS/乐透/卧底/WebUI |

## 七、安装

1. 下载 Release 中的 zip 包（或通过 AstrBot 插件市场搜索安装）；
2. 在 AstrBot WebUI → 插件管理 中导入安装；
3. 在插件配置页填写管理员QQ号等基础配置并重载插件。

## 八、数据备份

所有数据存储在 AstrBot 数据目录的 SQLite 数据库中，定期备份 `data/` 目录即可。

---

<div align="center">

如果这个插件对你有帮助，欢迎点个 Star ⭐

</div>
