"""量化策略回测固定模块 - A股真实数据"""
import numpy as np
import pandas as pd
import tushare as ts
import time

# ⚠️ 替换成你的 Tushare Token！
TOKEN = "d5319aa70ec2b59f41e92dd2c7b62556fd61cf261c4f720cd13d5d32"  # 从 https://www.tushare.pro/ 获取

SYMBOLS = ["000001.SZ", "000858.SZ", "600000.SH"]  # 平安银行、五粮液、浦发银行
START_DATE = "20230101"
END_DATE = "20241231"
INITIAL_CAPITAL = 100000
COMMISSION = 0.001

class DataCache:
    _cache = {}
    
    @classmethod
    def get_data(cls, symbols, start_date, end_date):
        """从 Tushare 获取 A股真实数据"""
        key = (tuple(sorted(symbols)), start_date, end_date)
        if key not in cls._cache:
            data = {}
            print(f"📊 从 Tushare 下载 A股真实行情数据 {len(symbols)} 个...")
            
            pro = ts.pro_api(TOKEN)
            
            for symbol in symbols:
                try:
                    print(f"  ⏳ 正在下载 {symbol}...")
                    
                    # 获取日线数据
                    df = pro.daily(
                        ts_code=symbol,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if df is None or df.empty:
                        print(f"  ✗ {symbol}: 返回空数据")
                        return None
                    
                    # 按时间排序
                    df = df.sort_values('trade_date')
                    df['trade_date'] = pd.to_datetime(df['trade_date'])
                    df = df.set_index('trade_date')
                    
                    # 重命名列
                    df = df.rename(columns={
                        'open': 'Open',
                        'high': 'High',
                        'low': 'Low',
                        'close': 'Close',
                        'vol': 'Volume'
                    })
                    
                    data[symbol] = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                    print(f"  ✓ {symbol}: {len(df)} 根 K 线")
                    
                    time.sleep(0.5)  # API 速率限制
                    
                except Exception as e:
                    print(f"  ✗ {symbol}: 下载失败 - {str(e)}")
                    return None
            
            cls._cache[key] = data
        return cls._cache[key]

class StrategyEvaluator:
    @staticmethod
    def calculate_returns(pnl_history):
        pnl_array = np.array(pnl_history, dtype=np.float64)
        if len(pnl_array) < 2:
            return np.array([])
        returns = np.diff(pnl_array) / (pnl_array[:-1] + 1e-8)
        return returns
    
    @staticmethod
    def calculate_sharpe(returns, risk_free_rate=0.02):
        if len(returns) == 0:
            return -np.inf
        daily_excess = returns - risk_free_rate / 252
        if np.std(daily_excess) < 1e-8:
            return -np.inf
        sharpe = np.mean(daily_excess) / np.std(daily_excess) * np.sqrt(252)
        return float(sharpe)
    
    @staticmethod
    def calculate_max_drawdown(pnl_history):
        cumulative = np.array(pnl_history, dtype=np.float64)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (running_max + 1e-8)
        return float(np.min(drawdown))
    
    @staticmethod
    def calculate_win_rate(returns):
        if len(returns) == 0:
            return 0.0
        win_days = np.sum(returns > 0)
        return float(win_days / len(returns))

def evaluate_strategy_score(pnl_history):
    if len(pnl_history) < 2:
        return {
            'score': -999.0, 
            'sharpe': -999.0, 
            'max_drawdown': 0.0, 
            'win_rate': 0.0, 
            'final_pnl': 0.0, 
            'total_returns': 0.0
        }
    returns = StrategyEvaluator.calculate_returns(pnl_history)
    sharpe = StrategyEvaluator.calculate_sharpe(returns)
    max_dd = StrategyEvaluator.calculate_max_drawdown(pnl_history)
    win_rate = StrategyEvaluator.calculate_win_rate(returns)
    score = sharpe - 0.5 * abs(max_dd) + 0.1 * win_rate
    final_pnl = pnl_history[-1] - INITIAL_CAPITAL
    total_returns = final_pnl / INITIAL_CAPITAL if INITIAL_CAPITAL > 0 else 0
    return {
        'score': float(score), 
        'sharpe': float(sharpe if not np.isinf(sharpe) else -999), 
        'max_drawdown': float(max_dd), 
        'win_rate': float(win_rate), 
        'final_pnl': float(final_pnl), 
        'total_returns': float(total_returns)
    }
