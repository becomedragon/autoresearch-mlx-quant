"""量化策略回测引擎 - AI Agent 在这个文件中修改策略"""
import numpy as np
import pandas as pd
import time
import sys
from prepare import DataCache, StrategyEvaluator, evaluate_strategy_score, SYMBOLS, START_DATE, END_DATE, INITIAL_CAPITAL, COMMISSION

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
USE_REVERSAL = False
USE_VOLUME_FILTER = False

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

def atr(high, low, close, period):
    if len(high) < period:
        return np.full(len(high), np.mean(high - low))
    tr = np.zeros(len(high))
    tr[0] = high[0] - low[0]
    for i in range(1, len(high)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    result = np.zeros(len(high))
    result[:period] = np.mean(tr[:period])
    for i in range(period, len(high)):
        result[i] = np.mean(tr[max(0, i-period+1):i+1])
    return result

def generate_signal(close, high, low, idx):
    min_lookback = max(SMA_LONG, RSI_PERIOD, ATR_PERIOD) + 1
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
    if USE_ATR_FILTER and len(window) >= ATR_PERIOD:
        atr_vals = atr(high[:idx+1], low[:idx+1], close[:idx+1], ATR_PERIOD)[-1]
        if atr_vals < close[idx] * 0.005:
            signal = 0
    return signal

def run_backtest():
    print("\n" + "="*70)
    print("🚀 启动量化策略回测")
    print("="*70)
    data_dict = DataCache.get_data(SYMBOLS, START_DATE, END_DATE)
    if data_dict is None:
        print("❌ 数据获取失败")
        return None, 0
    print(f"\n📈 策略参数:\n  SMA: ({SMA_SHORT}, {SMA_LONG})\n  RSI: {RSI_PERIOD} (OB:{RSI_OVERBOUGHT}, OS:{RSI_OVERSOLD})\n  头寸: {MAX_POSITION_SIZE*100:.0f}% | 止损: {STOP_LOSS_PERCENT*100:.1f}% | 止盈: {TAKE_PROFIT_PERCENT*100:.1f}%")
    portfolio_value, positions, entry_prices = [INITIAL_CAPITAL], {s: 0 for s in SYMBOLS}, {s: 0.0 for s in SYMBOLS}
    t_start = time.time()
    min_len = min(len(data_dict[s]) for s in SYMBOLS)
    min_lookback = max(SMA_LONG, RSI_PERIOD, ATR_PERIOD) + 1
    for day_idx in range(min_lookback, min_len):
        current_pnl = 0
        for symbol in SYMBOLS:
            ohlcv = data_dict[symbol]
            close_price = ohlcv['Close'].iloc[day_idx]
            signal = generate_signal(ohlcv['Close'].values[:day_idx+1], ohlcv['High'].values[:day_idx+1], ohlcv['Low'].values[:day_idx+1], day_idx)
            max_shares = int(portfolio_value[-1] * MAX_POSITION_SIZE / close_price)
            if signal == 1 and positions[symbol] == 0 and max_shares > 0:
                positions[symbol], entry_prices[symbol] = max_shares, close_price
                portfolio_value[-1] -= positions[symbol] * close_price * (1 + COMMISSION)
            elif signal == -1 and positions[symbol] > 0:
                portfolio_value[-1] += positions[symbol] * close_price * (1 - COMMISSION)
                positions[symbol] = 0
            if positions[symbol] > 0 and entry_prices[symbol] > 0:
                pnl_pct = (close_price - entry_prices[symbol]) / entry_prices[symbol]
                if pnl_pct < -STOP_LOSS_PERCENT or pnl_pct > TAKE_PROFIT_PERCENT:
                    portfolio_value[-1] += positions[symbol] * close_price * (1 - COMMISSION)
                    positions[symbol] = 0
            current_pnl += positions[symbol] * close_price
        portfolio_value.append(max(portfolio_value[-1] + current_pnl, INITIAL_CAPITAL * 0.5))
    return portfolio_value, time.time() - t_start

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
