"""量化策略回测引擎 - AI Agent 在这个文件中修改策略"""
import numpy as np
import pandas as pd
import time
import sys
from prepare import DataCache, StrategyEvaluator, evaluate_strategy_score, SYMBOLS, START_DATE, END_DATE, INITIAL_CAPITAL, COMMISSION

# ============================================================================
# 策略参数段（Agent 可自由修改）
# ============================================================================

SMA_SHORT = 10
SMA_LONG = 50
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
ATR_PERIOD = 14
MAX_POSITION_SIZE = 0.3
STOP_LOSS_PERCENT = 0.05
TAKE_PROFIT_PERCENT = 0.15
USE_RSI = True
USE_SMA = True
USE_ATR_FILTER = False

def sma(prices, period):
    if len(prices) < period:
        return np.full(len(prices), prices[-1] if len(prices) > 0 else 0)
    result = np.zeros(len(prices))
    for i in range(len(prices)):
        if i < period - 1:
            result[i] = np.mean(prices[:i+1])
        else:
            result[i] = np.mean(prices[i-period+1:i+1])
    return result

def rsi(prices, period):
    if len(prices) < period + 1:
        return np.full(len(prices), 50)
    result = np.zeros(len(prices))
    result[:period] = 50
    for i in range(period, len(prices)):
        deltas = np.diff(prices[max(0, i-period):i+1])
        gains = np.sum(np.where(deltas > 0, deltas, 0))
        losses = np.sum(np.where(deltas < 0, -deltas, 0))
        if losses == 0:
            result[i] = 100 if gains > 0 else 50
        else:
            rs = gains / losses
            result[i] = 100 - (100 / (1 + rs))
    return result

def generate_signal(close, high, low, idx):
    min_lookback = max(SMA_LONG, RSI_PERIOD) + 1
    if idx < min_lookback:
        return 0
    signal = 0
    window = close[:idx+1]
    if USE_SMA and len(window) >= SMA_LONG:
        sma_s, sma_l = sma(window, SMA_SHORT)[-1], sma(window, SMA_LONG)[-1]
        if sma_s > sma_l * 1.01:
            signal = 1
        elif sma_s < sma_l * 0.99:
            signal = -1
    if USE_RSI and len(window) >= RSI_PERIOD:
        rsi_vals = rsi(window, RSI_PERIOD)[-1]
        if rsi_vals > RSI_OVERBOUGHT:
            signal = -1
        elif rsi_vals < RSI_OVERSOLD:
            signal = 1
    return signal

def run_backtest():
    print("\n" + "="*70)
    print("🚀 启动量化策略回测")
    print("="*70)
    
    data_dict = DataCache.get_data(SYMBOLS, START_DATE, END_DATE)
    if data_dict is None:
        print("❌ 数据获取失败")
        return None, 0
    
    print(f"\n📈 策略参数:")
    print(f"  SMA: ({SMA_SHORT}, {SMA_LONG})")
    print(f"  RSI: {RSI_PERIOD} (OB:{RSI_OVERBOUGHT}, OS:{RSI_OVERSOLD})")
    print(f"  头寸: {MAX_POSITION_SIZE*100:.0f}% | 止损: {STOP_LOSS_PERCENT*100:.1f}% | 止盈: {TAKE_PROFIT_PERCENT*100:.1f}%")
    
    cash = INITIAL_CAPITAL
    positions = {s: 0 for s in SYMBOLS}
    entry_prices = {s: 0.0 for s in SYMBOLS}
    portfolio_history = [INITIAL_CAPITAL]
    
    t_start = time.time()
    
    min_len = min(len(data_dict[s]) for s in SYMBOLS)
    min_lookback = max(SMA_LONG, RSI_PERIOD) + 1
    
    for day_idx in range(min_lookback, min_len):
        daily_portfolio_value = cash
        
        for symbol in SYMBOLS:
            ohlcv = data_dict[symbol]
            close_price = float(ohlcv['Close'].iloc[day_idx])
            
            signal = generate_signal(
                ohlcv['Close'].values[:day_idx+1],
                ohlcv['High'].values[:day_idx+1],
                ohlcv['Low'].values[:day_idx+1],
                day_idx
            )
            
            # 买入信号
            if signal == 1 and positions[symbol] == 0:
                max_investment = cash * MAX_POSITION_SIZE
                max_shares = int(max_investment / close_price)
                
                if max_shares > 0:
                    cost = max_shares * close_price * (1 + COMMISSION)
                    if cost <= cash:
                        positions[symbol] = max_shares
                        entry_prices[symbol] = close_price
                        cash -= cost
            
            # 卖出信号或止损/止盈
            elif positions[symbol] > 0:
                should_sell = False
                
                if signal == -1:
                    should_sell = True
                elif entry_prices[symbol] > 0:
                    pnl_pct = (close_price - entry_prices[symbol]) / entry_prices[symbol]
                    if pnl_pct <= -STOP_LOSS_PERCENT or pnl_pct >= TAKE_PROFIT_PERCENT:
                        should_sell = True
                
                if should_sell:
                    proceeds = positions[symbol] * close_price * (1 - COMMISSION)
                    cash += proceeds
                    positions[symbol] = 0
                    entry_prices[symbol] = 0.0
            
            # 累加头寸价值
            daily_portfolio_value += positions[symbol] * close_price
        
        portfolio_history.append(max(daily_portfolio_value, INITIAL_CAPITAL * 0.1))
    
    return portfolio_history, time.time() - t_start

if __name__ == "__main__":
    pnl_history, backtest_time = run_backtest()
    
    if pnl_history is None or len(pnl_history) < 2:
        print("\n❌ 回测失败")
        sys.exit(1)
    
    metrics = evaluate_strategy_score(pnl_history)
    
    print("\n" + "="*70)
    print("📊 回测结果")
    print("="*70)
    print(f"score:           {metrics['score']:.6f}")
    print(f"sharpe_ratio:    {metrics['sharpe']:.6f}")
    print(f"max_drawdown:    {metrics['max_drawdown']:.6f}")
    print(f"win_rate:        {metrics['win_rate']:.6f}")
    print(f"final_pnl:       ${metrics['final_pnl']:,.2f}")
    print(f"total_return:    {metrics['total_returns']*100:.2f}%")
    print(f"backtest_time:   {backtest_time:.2f}s")
    print("="*70 + "\n")
