from datetime import date, datetime, time
from typing import List, Optional, Tuple
import chinese_calendar
from enum import Enum

class MarketType(Enum):
    CN = "CN"  # A股
    HK = "HK"  # 港股 (暂未实现)
    US = "US"  # 美股 (暂未实现)

class CalendarService:
    """
    日历服务组件
    负责交易日识别和交易时段判断
    """
    
    def __init__(self):
        # A股交易时段配置 (默认)
        self.trading_sessions = [
            (time(9, 15), time(11, 30)),  # 上午 (含集合竞价)
            (time(13, 0), time(15, 5))    # 下午 (含收盘集合竞价)
        ]
        
        # 特殊休市日 (A股特有，非定假日但休市)
        # 例如：2024-02-09 (除夕)，虽然是工作日，但股市休市
        self.special_market_holidays = {
            date(2024, 2, 9), 
        }
        
    def is_trading_day(self, day: Optional[date] = None, market: MarketType = MarketType.CN) -> bool:
        """
        判断是否为交易日
        
        Args:
            day: 日期 (默认今天)
            market: 市场类型
            
        Returns:
            bool: 是否为交易日
            
        Raises:
            ValueError: 如果day参数类型错误
        """
        try:
            if day is None:
                day = date.today()
            elif isinstance(day, str):
                # 尝试解析字符串日期
                day = datetime.strptime(day, "%Y-%m-%d").date()
            elif isinstance(day, datetime):
                day = day.date()
            elif not isinstance(day, date):
                raise ValueError(f"Invalid date type: {type(day)}. Expected date, datetime or str.")
        except ValueError as e:
            # 重新抛出具体的错误
            raise e
        except Exception as e:
            # 捕获其他可能的错误
            raise ValueError(f"Error processing date: {e}")
            
        if market == MarketType.CN:
            # chinese_calendar.is_workday 判断是否工作日 (包含调休)
            # 但股市周末不开盘，即使是调休的工作日也不开盘 (通常情况)
            # 修正逻辑: 
            # 1. 必须是工作日 (is_workday)
            # 2. 不能是周末 (即使是调休工作日，A股通常也不开市，除非特殊安排，这里简化处理：周末一律不开)
            # 等等，chinese_calendar.is_workday 会把调休的周六日算作工作日。
            # A股规则：法定节假日休市，周末休市（即使调休上班）。
            # 所以逻辑应该是：不是节假日 (is_holiday) 且 不是周末
            
            # chinese_calendar.is_holiday() 返回 True 如果是假期 或者 周末
            # 但是调休上班的日子，is_holiday() 返回 False
            
            # 准确逻辑：
            # A股休市 = 法定节假日 OR 周末
            # chinese_calendar.is_holiday(day) 包含了法定节假日和周末，但排除了调休上班的周末
            # 所以如果 is_holiday() 为 True，肯定是休市
            # 如果 is_holiday() 为 False (工作日)，还需要判断是不是周末？
            # 不，调休上班的周末，A股也是休市的！
            # 例子：2025-10-11 是周六，调休上班。is_holiday -> False (是工作日)。但A股休市。
            
            # 最终逻辑：
            # 1. 如果是周末 (Saturday/Sunday)，A股一定休市 (不管是否调休)。
            # 2. 如果是法定节假日 (chinese_calendar.get_holiday_detail 返回非None)，A股休市。
            
            # 简单版：
            # A股交易日 = (非周末) AND (非节假日)
            
            is_weekend = day.weekday() >= 5
            try:
                is_holiday = chinese_calendar.is_holiday(day)
            except NotImplementedError:
                # 如果是未来年份且无节假日数据，回退到仅判断周末
                is_holiday = is_weekend
            except Exception:
                is_holiday = is_weekend
            
            if is_weekend:
                return False
                
            # 检查特殊休市日
            if day in self.special_market_holidays:
                return False
                
            # 如果是周一到周五，检查是否是节假日
            if is_holiday:
                return False
                
            return True
            
        else:
            # 其他市场暂不支持，默认返回工作日
            return day.weekday() < 5

    def is_business_hours(self, current_time: Optional[time] = None) -> bool:
        """
        判断当前时间是否在交易时段内
        
        Args:
            current_time: 时间 (默认当前时间)
            
        Returns:
            bool: 是否在交易时段
            
        Raises:
            ValueError: 如果时间参数类型错误
        """
        try:
            if current_time is None:
                current_time = datetime.now().time()
            elif isinstance(current_time, str):
                # 尝试解析字符串时间 (HH:MM 或 HH:MM:SS)
                try:
                    current_time = datetime.strptime(current_time, "%H:%M:%S").time()
                except:
                    current_time = datetime.strptime(current_time, "%H:%M").time()
            elif isinstance(current_time, datetime):
                current_time = current_time.time()
            elif not isinstance(current_time, time):
                raise ValueError(f"Invalid time type: {type(current_time)}. Expected time, datetime or str.")
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error processing time: {e}")
            
        for start, end in self.trading_sessions:
            if start <= current_time <= end:
                return True
                
        return False

    def get_next_trading_day(self, day: Optional[date] = None) -> date:
        """
        获取下一个交易日
        
        Args:
            day: 起始日期 (默认今天)
            
        Returns:
            date: 下一个交易日
            
        Raises:
            ValueError: 如果日期参数类型错误
        """
        try:
            if day is None:
                day = date.today()
            elif isinstance(day, str):
                day = datetime.strptime(day, "%Y-%m-%d").date()
            elif isinstance(day, datetime):
                day = day.date()
            elif not isinstance(day, date):
                raise ValueError(f"Invalid date type: {type(day)}. Expected date, datetime or str.")
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error processing date: {e}")
            
        next_day = day
        from datetime import timedelta
        
        while True:
            next_day = next_day + timedelta(days=1)
            if self.is_trading_day(next_day):
                return next_day

if __name__ == "__main__":
    # 简单测试
    service = CalendarService()
    today = date.today()
    print(f"Today ({today}) is trading day? {service.is_trading_day(today)}")
    
    now = datetime.now().time()
    print(f"Now ({now}) is business hours? {service.is_business_hours(now)}")
    
    # 测试调休逻辑 (假设 2024-02-04 是周日但调休上班，A股应休市)
    # test_date = date(2024, 2, 4)
    # print(f"2024-02-04 (Sun, Workday) is trading day? {service.is_trading_day(test_date)}")
