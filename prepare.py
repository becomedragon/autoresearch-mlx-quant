"""量化策略回测固定模块 - 使用缓存数据或模拟数据"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pickle
import os

SYMBOLS = ["000001", "000858", "600000"]
START_DATE = "20230101"
END_DATE = "20241231"
INITIAL_CAPITAL = 100000
COMMISSION = 0.001

class DataCache:
    _cache = {}
    
    @classmethod
    def get_data(cls, symbols, start_date, end_date):
        """优先使用缓存，否则生成模拟数据"""
        key = (tuple(sorted(symbols)), start_date, end_date)
        if key not in cls._cache:
            data = {}
            
            # 尝试读取缓存
            if os.path.exists('data_cache.pkl'):
                print(f"📊 从缓存读取 A股真实行情数据 {len(symbols)} 个...")
                try:
                    with open('data_cache.pkl', 'rb') as f:
                        cached = pickle.load(f)
                    for symbol in symbols:
                        if symbol in cached:
                            data[symbol] = cached[symbol]
                            print(f"  ✓ {symbol}: {len(cached[symbol])} 根 K 线")
                        else:
                            print(f"  ✗ {symbol}: 缓存中不存在")
                    
                    if len(data) == len(symbols):
                        cls._cache[key] = data
                        return cls._cache[key]
                except:
                    print(f"  ✗ 读取缓存失败，使用模拟数据")
            
            # 生成模拟数据
            print(f"📊 生成模拟行情数据 {len(symbols)} 个...")
            start = pd.to_datetime(start_date, format='%Y%m%d')
            end = pd.to_datetime(end_date, format='%Y%m%d')
            date_range = pd.date_range(start=start, end=end, freq='B')
            
            configs = {
                "000001": {"price": 15, "volatility": 0.012},
                "000858": {"price": 140, "volatility": 0.018},
                "600000": {"price": 14, "volatility": 0.015}
            }
            
            for symbol in symbols:
                try:
                    np.random.seed(hash(symbol) % 2**32)
                    config = configs.get(symbol, {"price": 100, "volatility": 0.015})
                    
                    n = len(date_range)
                    returns = np.random.normal(0.0005, config["volatility"]/np.sqrt(252), n)
                    prices = config["price"] * np.exp(np.cumsum(returns))
                    
                    df = pd.DataFrame({
                        'Open': prices * (1 + np.random.uniform(-0.01, 0.01, n)),
                        'High': prices * (1 + np.abs(np.random.uniform(0, 0.02, n))),
                        'Low': prices * (1 - np.abs(np.random.uniform(0, 0.02, n))),
                        'Close': prices,
                        'Volume': np.random.randint(1000000, 10000000, n)
                    }, index=date_range)
                    
                    data[symbol] = df.sort_index()
                    print(f"  ✓ {symbol}: {len(df)} 根 K 线")
                except Exception as e:
                    print(f"  ✗ {symbol}: {str(e)}")
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
