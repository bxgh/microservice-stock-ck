    async def fetch_tick_data_rigorous(
        self,
        stock_code: str,
        trade_date: str
    ) -> List[Dict[str, Any]]:
        """
        严谨完整性优先策略 (Rigorous Integrity-First Strategy)
        
        逻辑流程:
        1. [Baseline Fetch]: 执行标准顺序回溯，获取大部分数据。
        2. [Gap Analysis]: 分析数据覆盖范围。如果已含 09:25-15:00，直接返回。
        3. [Targeted Probe]: 如果缺失早盘 (min > 09:25)，启动智能矩阵搜索填补缺口。
        4. [Consensus]: 合并所有数据，去重排序。
        """
        logger.debug(f"开始严谨完整性采集: {stock_code} ({trade_date})")
        
        collected_frames = []
        
        # Step 1: Baseline Fetch (获取基础数据)
        # 用法：只请求常规的 0 和 1000 偏移量，快速拿到午盘数据
        # 即使被截断，也能拿到 10:06-15:00
        baseline_data = await self.fetch_tick_data_sequential(stock_code, trade_date)
        if baseline_data:
            collected_frames.append(baseline_data)
            
        # Step 2: Gap Analysis (缺口分析)
        current_data = []
        for frame in collected_frames:
            current_data.extend(frame)
            
        if not current_data:
            # 如果连基础数据都没有，尝试用矩阵“盲搜”一次作为最后努力
            logger.debug(f"{stock_code}: 基础数据为空，尝试盲搜早盘...")
            matrix_data = await self.fetch_tick_data_smart(stock_code, trade_date)
            if matrix_data:
                collected_frames.append(matrix_data)
                current_data.extend(matrix_data)
            else:
                return []
        
        # 提取时间特征
        times = [x.get('time', '') for x in current_data]
        min_t, max_t = min(times), max(times)
        
        # 判定完整性
        has_morning = (min_t <= "09:25")
        has_afternoon = (max_t >= "15:00")  # 或接近 15:00
        
        if has_morning and has_afternoon:
            logger.debug(f"{stock_code}: 基础数据已完整 ({min_t}-{max_t})，无需补采")
            # 直接复用 current_data 进行排序去重即可
        else:
            # Step 3: Targeted Probe (靶向填补)
            if not has_morning:
                logger.info(f"🔍 {stock_code}: 缺失早盘 ({min_t} > 09:25)，启动深潜探测...")
                # 调用智能矩阵搜索，它专门负责挖掘 3500-6000 偏移量的深层数据
                deep_data = await self.fetch_tick_data_smart(stock_code, trade_date)
                if deep_data:
                    collected_frames.append(deep_data)
                    logger.info(f"🧩 {stock_code}: 深潜探测归来，补全早盘数据")
            
            # 如果缺午盘（非常少见，除非停牌），理论上 sequential 已经覆盖了。
            
        # Step 4: Consensus (共识合并)
        # 将所有 collected_frames 合并、去重、排序
        all_items = []
        for frame in collected_frames:
            all_items.extend(frame)
            
        seen = set()
        final_data = []
        for item in all_items:
            # key: time, price, vol, buyorsell
            key = (
                item.get('time'), 
                item.get('price'), 
                item.get('vol', item.get('volume')), 
                item.get('buyorsell', 2)
            )
            if key not in seen:
                seen.add(key)
                final_data.append(item)
                
        # 按时间排序
        final_data.sort(key=lambda x: x.get('time', ''))
        
        return final_data
