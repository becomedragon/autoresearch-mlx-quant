"""量化策略回测固定模块 - 使用真实市场逻辑的模拟数据"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

SYMBOLS = ["SPY", "QQQ", "AAPL"]
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
INITIAL_CAPITAL = 100000
COMMISSION = 0.001

class DataCache:
    _cache = {}
    
    @classmethod
    def generate_realistic_data(cls, symbol, start_date, end_date, base_price, volatility=0.015, drift=0.0005):
        """生成基于真实市场逻辑的模拟数据"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        date_range = pd.date_range(start=start, end=end, freq='B')
        
        # 使用与符号相关的种子，保证可重现
        np.random.seed(hash(symbol) % 2**32)
        
        # 生成几何布朗运动（GBM）- 真实股价模型
        n = len(date_range)
        dt = 1/252  # 每日时间步
        
        # 随机游走
        returns = np.random.normal(drift * dt, volatility * np.sqrt(dt), n)
        prices = base_price * np.exp(np.cumsum(returns))
        
        # 生成 OHLCV 数据
        opens = prices * (1 + np.random.uniform(-0.005, 0.005, n))
        highs = np.maximum(opens, prices) * (1 + np.abs(np.random.uniform(0, 0.01, n)))
        lows = np.minimum(opens, prices) * (1 - np.abs(np.random.uniform(0, 0.01, n)))
        closes = prices
        volumes = np.random.randint(1000000, 100000000, n)
        
        df = pd.DataFrame({
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes
        }, index=date_range)
        
        return df.sort_index()
    
    @classmethod
    def get_data(cls, symbols, start_date, end_date):
        """获取模拟数据"""
        key = (tuple(sorted(symbols)), start_date, end_date)
        if key not in cls._cache:
            data = {}
            print(f"📊 生成真实市场逻辑的模拟行情数据 {len(symbols)} 个品种...")
            
            # 基础价格和波动率设置（基于真实市场特征）
            configs = {
                "SPY": {"price": 380, "volatility": 0.012, "drift": 0.0006},
                "QQQ": {"price": 380, "volatility": 0.018, "drift": 0.0008},
                "AAPL": {"price": 180, "volatility": 0.020, "drift": 0.0010}
            }
            
            for symbol in symbols:
                try:
                    config = configs.get(symbol, {"price": 100, "volatility": 0.015, "drift": 0.0005})
                    df = cls.generate_realistic_data(
                        symbol, 
                        start_date, 
                        end_date,
                        base_price=config["price"],
                        volatility=config["volatility"],
                        drift=config["drift"]
                    )
                    data[symbol] = df
                    print(f"  ✓ {symbol}: {len(df)} 根 K 线 (基础价格: ${config['price']:.0f})")
                except Exception as e:
                    print(f"  ✗ {symbol}: 生成失败 - {str(e)}")
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
