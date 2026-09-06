"""
帮助图片生成器 - 积分游戏插件
"""
from PIL import Image, ImageDraw, ImageFont
import textwrap

def generate_help_image(output_path: str = "/var/minis/attachments/help.png"):
    """生成帮助图片"""
    # 画布尺寸
    width = 1200
    height = 3000
    bg_color = (245, 247, 250)  # 浅灰蓝背景
    
    # 创建画布
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # 加载字体（使用思源黑体）
    try:
        title_font = ImageFont.truetype("/var/minis/workspace/astrbot_plugin_point_games/font/SourceHanSansCN-Regular.otf", 56)
        heading_font = ImageFont.truetype("/var/minis/workspace/astrbot_plugin_point_games/font/SourceHanSansCN-Regular.otf", 38)
        text_font = ImageFont.truetype("/var/minis/workspace/astrbot_plugin_point_games/font/SourceHanSansCN-Regular.otf", 26)
    except:
        # 降级到默认字体
        title_font = ImageFont.load_default()
        heading_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    y = 40
    
    # 标题
    draw.text((width//2, y), "🎮 积分游戏插件", font=title_font, fill=(50, 50, 50), anchor="mm")
    y += 80
    draw.text((width//2, y), "v4.22.0 - 完整指令手册", font=heading_font, fill=(100, 100, 100), anchor="mm")
    y += 80
    
    # 分类内容
    categories = [
        ("📊 基础查询", [
            "/积分 - 查看自己的积分余额",
            "/查询 - 查看详细数据",
            "/查积分 @玩家 - 查询他人积分",
            "/排行 - 全服总资产排行榜",
        ]),
        ("🎮 娱乐玩法", [
            "/掷骰 @群友 - 比大小（胜者+10）",
            "/转盘 [积分] - 幸运转盘（最高5倍）",
            "/水果机 [积分] - 老虎机玩法",
            "/刮刮乐 [张数] - 即时开奖",
            "/猜数字 [积分] [大/小/数字] - 猜数字",
            "/抽卡 - 消耗10积分抽卡",
            "/十连 - 消耗100积分十连抽",
            "/图鉴 - 查看已收集卡牌",
            "/速算 - 速算挑战（每天10次）",
            "/闯关 - 答题闯关",
        ]),
        ("🎲 竞技互动", [
            "/攻击 - 消耗5积分打BOSS",
            "/BOSS状态 - 查看BOSS血量",
            "/BOSS排行 - 今日伤害前十",
            "/买彩票 [积分] - 每日20:00开奖",
            "/彩票奖池 - 查看当前奖池",
            "/卧底开始 [人数] - 谁是卧底",
            "/加入卧底 - 报名游戏",
            "/投票 @某人 - 投票阶段",
        ]),
        ("💣 炸弹游戏", [
            "/炸弹开始 - 数字炸弹（1-100）",
            "/猜 [数字] - 猜数字",
            "/炸弹结束 - 强制结束（管理员）",
        ]),
        ("🎣 钓鱼系统", [
            "/买鱼竿 - 200积分购买（最多10根）",
            "/买鱼饵 [数量] - 10积分/个",
            "/挂机钓鱼 [编号] - 鱼竿挂机",
            "/收鱼 - 收取挂机钓到的鱼",
            "/卖鱼 - 一键卖出所有鱼",
            "/鱼图鉴 - 查看收集进度（77种）",
            "/鱼竿列表 - 查看鱼竿状态",
            "/修鱼竿 [编号] - 50积分修理",
            "/钓鱼排行 - 卖鱼收入前十",
            "/钓鱼统计 - 查看钓鱼数据",
        ]),
        ("💰 经济系统", [
            "/转账 @群友 [积分] - 转账（10%手续费）",
            "/开户 - 开通银行账户",
            "/存钱 [积分] - 存入银行",
            "/取钱 [积分] - 从银行取出",
            "/我的银行 - 查看银行余额",
            "/贷款 [积分] - 申请贷款（5%利息/天）",
            "/还款 - 还清当前贷款",
            "/我的贷款 - 查看贷款详情",
            "/兑换礼品 - 花费10000积分兑换",
        ]),
        ("🎁 福利系统", [
            "签到/jrzj/今日座驾 - 每日签到",
            "群活跃奖励 - 每日前三名（自动）",
            "每日红包 - 随机时间发放（自动）",
            "/发红包 [总积分] [份数] - 自己发红包",
            "每日收税 - 凌晨0点收税（自动）",
        ]),
    ]
    
    # 绘制每个分类
    for category_name, items in categories:
        # 分类标题背景
        draw.rectangle([(40, y), (width-40, y+50)], fill=(100, 150, 250), outline=(70, 120, 220), width=2)
        draw.text((60, y+25), category_name, font=heading_font, fill=(255, 255, 255), anchor="lm")
        y += 60
        
        # 分类内容
        for item in items:
            draw.text((80, y), f"• {item}", font=text_font, fill=(60, 60, 60), anchor="lm")
            y += 40
        
        y += 20  # 分类间距
    
    # 底部提示
    y += 20
    draw.rectangle([(40, y), (width-40, y+120)], fill=(255, 250, 230), outline=(220, 200, 150), width=2)
    y += 20
    draw.text((width//2, y), "💡 快速开始", font=heading_font, fill=(200, 100, 50), anchor="mm")
    y += 50
    draw.text((width//2, y), "发送「签到」领取每日积分 → 发送「/积分」查看余额 → 选择喜欢的玩法开始游戏！", 
              font=text_font, fill=(100, 100, 100), anchor="mm")
    
    # 裁剪到实际高度
    img = img.crop((0, 0, width, y+80))
    
    # 保存
    img.save(output_path, 'PNG', quality=95)
    return output_path

if __name__ == "__main__":
    path = generate_help_image()
    print(f"✓ 帮助图片已生成：{path}")
