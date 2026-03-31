"""量化策略回测固定模块 - 获取真实市场数据"""
import numpy as np
import pandas as pd
import pandas_datareader as pdr
from datetime import datetime, timedelta
import time

SYMBOLS = ["SPY", "QQQ", "AAPL"]
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
INITIAL_CAPITAL = 100000
COMMISSION = 0.001

class DataCache:
    _cache = {}
    
    @classmethod
    def get_data(cls, symbols, start_date, end_date):
        """获取真实市场数据 - 使用 pandas_datareader"""
        key = (tuple(sorted(symbols)), start_date, end_date)
        if key not in cls._cache:
            data = {}
            print(f"📊 下载真实行情数据 {len(symbols)} 个品种...")
            for symbol in symbols:
                try:
                    print(f"  ⏳ 正在下载 {symbol}...")
                    # 使用 pandas_datareader 从 Yahoo Finance 获取数据
                    df = pdr.get_data_yahoo(symbol, start=start_date, end=end_date)
                    
                    # 确保列名正确
                    if 'Adj Close' in df.columns:
                        df['Close'] = df['Adj Close']
                    
                    data[symbol] = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                    print(f"  ✓ {symbol}: {len(df)} 根 K 线")
                    time.sleep(1)  # 避免被限流
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
        return {'score': -999.0, 'sharpe': -999.0, 'max_drawdown': 0.0, 'win_rate': 0.0, 'final_pnl': 0.0, 'total_returns': 0.0}
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
