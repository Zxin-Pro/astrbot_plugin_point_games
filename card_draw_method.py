
    # ============================================================
    #  功能25：抽卡大作战（十连抽卡，期望为负）
    # ============================================================
    @filter.command("十连")
    async def card_draw(self, event: AstrMessageEvent):
        """/十连 —— 抽10张卡，总分越高奖励越高"""
        ok_gate, msg_gate = await self._check_group_gate(event, "十连")
        if not ok_gate:
            yield event.plain_result(msg_gate)
            return
        
        user_id = event.get_sender_id()
        
        async def fn(session):
            # 检查冷却
            remaining = await self._enforce_cooldown(session, user_id)
            if remaining > 0:
                raise _BizError(f"操作太频繁啦，请 {remaining} 秒后再试喵~")
            
            # 检查余额
            bal = await self._total_balance(session, user_id)
            if bal < self.DRAW_COST:
                raise _BizError(f"❌ 积分不足！需要{self.DRAW_COST}积分，当前余额：{bal}积分")
            
            # 抽10张卡
            cards = []
            total = 0
            legendary_count = 0
            
            for i in range(self.DRAW_COUNT):
                # 卡牌概率：普通60%、稀有25%、史诗10%、传说5%
                rand = random.random()
                if rand < 0.60:
                    # 普通卡 1-60分
                    card = random.randint(self.CARD_MIN, 60)
                elif rand < 0.85:
                    # 稀有卡 61-80分
                    card = random.randint(61, 80)
                elif rand < 0.95:
                    # 史诗卡 81-90分
                    card = random.randint(81, 90)
                else:
                    # 传说卡 91-100分
                    card = random.randint(91, self.CARD_MAX)
                    legendary_count += 1
                
                cards.append(card)
                total += card
            
            # 计算奖励
            reward = int(total * self.DRAW_BASE_RATE)
            bonus_msg = ""
            
            if total >= 900:
                reward = int(reward * self.DRAW_BONUS_900)
                bonus_msg = "🌟 总分超过900！奖励三倍！"
            elif total >= 800:
                reward = int(reward * self.DRAW_BONUS_800)
                bonus_msg = "🌟 总分超过800！奖励翻倍！"
            
            net = reward - self.DRAW_COST
            
            # 记账
            await self._add_points(
                session, user_id, net, "十连",
                earned=reward, spent=self.DRAW_COST,
            )
            
            new_bal = await self._balance(session, user_id)
            
            # 检查消费达标提醒
            should_remind = await self._check_spend_reward(session, user_id, event.get_group_id())
            
            # 组装卡片显示
            card_str = " ".join(f"[{c:2d}]" for c in cards)
            
            # 组装消息
            lines = [
                f"🃏 【十连抽卡】",
                card_str,
                f"总分：{total}",
            ]
            
            if bonus_msg:
                lines.append(bonus_msg)
            
            lines.append(f"奖励：{reward}积分（净赚{net}）")
            
            # 传说卡单独显示
            if legendary_count > 0:
                lines.append(f"🎉 获得{legendary_count}张传说卡！")
            
            lines.append(f"当前余额：{new_bal}积分")
            
            msg = "\n".join(lines)
            
            return True, msg, should_remind
        
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

