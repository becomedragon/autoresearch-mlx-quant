"""自动参数优化 - 找到最优参数组合"""
import subprocess
import re
import json
import sys

results = []
best_score = -999

print("🤖 开始自动参数优化...")
print("="*70)

# 尝试不同的参数组合
sma_shorts = [5, 10, 15]
sma_longs = [50, 60, 70]
rsi_periods = [10, 14, 20]

total = len(sma_shorts) * len(sma_longs) * len(rsi_periods)
count = 0

for sma_short in sma_shorts:
    for sma_long in sma_longs:
        for rsi_period in rsi_periods:
            if sma_short >= sma_long:
                continue
            
            count += 1
            
            # 修改 backtest.py
            with open('backtest.py', 'r') as f:
                content = f.read()
            
            # 更精确的替换
            content = re.sub(r'SMA_SHORT = \d+', f'SMA_SHORT = {sma_short}', content)
            content = re.sub(r'SMA_LONG = \d+', f'SMA_LONG = {sma_long}', content)
            content = re.sub(r'RSI_PERIOD = \d+', f'RSI_PERIOD = {rsi_period}', content)
            
            with open('backtest.py', 'w') as f:
                f.write(content)
            
            # 运行回测
            try:
                result = subprocess.run(
                    ['python', 'backtest.py'], 
                    capture_output=True, 
                    text=True, 
                    timeout=60
                )
                
                output = result.stdout + result.stderr
                
                # 提取分数
                match = re.search(r'score:\s+([-\d.]+)', output)
                if match:
                    score = float(match.group(1))
                    
                    results.append({
                        'SMA_SHORT': sma_short,
                        'SMA_LONG': sma_long,
                        'RSI_PERIOD': rsi_period,
                        'score': score
                    })
                    
                    if score > best_score:
                        best_score = score
                        status = "⭐ 最优！"
                    else:
                        status = ""
                    
                    print(f"✓ [{count}] SMA({sma_short:2d},{sma_long:2d}) RSI{rsi_period:2d}: {score:10.6f} {status}")
                else:
                    print(f"✗ [{count}] SMA({sma_short:2d},{sma_long:2d}) RSI{rsi_period:2d}: 无法提取分数")
                    print(f"   输出: {output[-200:]}")
            except subprocess.TimeoutExpired:
                print(f"✗ [{count}] SMA({sma_short:2d},{sma_long:2d}) RSI{rsi_period:2d}: 超时")
            except Exception as e:
                print(f"✗ [{count}] SMA({sma_short:2d},{sma_long:2d}) RSI{rsi_period:2d}: {str(e)}")

print("\n" + "="*70)

if not results:
    print("❌ 没有成功运行的回测")
    sys.exit(1)

# 找到最优参数
best = max(results, key=lambda x: x['score'])
print(f"🏆 最优参数找到！")
print(f"   SMA_SHORT = {best['SMA_SHORT']}")
print(f"   SMA_LONG = {best['SMA_LONG']}")
print(f"   RSI_PERIOD = {best['RSI_PERIOD']}")
print(f"   最佳分数: {best['score']:.6f}")

# 显示前 5 名
print(f"\n🎯 前 5 个最佳策略：")
sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
for i, r in enumerate(sorted_results[:5], 1):
    print(f"   {i}. SMA({r['SMA_SHORT']},{r['SMA_LONG']}) RSI{r['RSI_PERIOD']}: {r['score']:.6f}")

print("="*70)

# 保存最优参数
with open('best_params.json', 'w') as f:
    json.dump(best, f, indent=2)

# 应用最优参数
with open('backtest.py', 'r') as f:
    content = f.read()

content = re.sub(r'SMA_SHORT = \d+', f"SMA_SHORT = {best['SMA_SHORT']}", content)
content = re.sub(r'SMA_LONG = \d+', f"SMA_LONG = {best['SMA_LONG']}", content)
content = re.sub(r'RSI_PERIOD = \d+', f"RSI_PERIOD = {best['RSI_PERIOD']}", content)

with open('backtest.py', 'w') as f:
    f.write(content)

print("\n✅ 最优参数已应用到 backtest.py")
print("   运行 'python backtest.py' 查看最优结果")
print("   最优参数已保存到 best_params.json")
