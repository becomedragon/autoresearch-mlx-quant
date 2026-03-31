class BacktestEngine:
    def __init__(self, strategy, initial_capital=10000):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.portfolio = []

    def execute(self, data):
        for date, price in data.items():
            action = self.strategy.signal_generator(price)
            if action == 'buy':
                shares = self.capital // price
                self.capital -= shares * price
                self.portfolio.append((date, shares, price))
            elif action == 'sell' and self.portfolio:
                shares = self.portfolio[-1][1]
                self.capital += shares * price
                self.portfolio.pop()

    def get_results(self):
        return {
            "final_capital": self.capital,
            "portfolio": self.portfolio
        }

# Example usage
if __name__ == "__main__":
    # Dummy data and strategy for testing
    class DummyStrategy:
        def signal_generator(self, price):
            return 'buy' if price < 100 else 'sell'

    data = {
        '2026-01-01': 95,
        '2026-01-02': 105,
        '2026-01-03': 90,
    }
    
    engine = BacktestEngine(DummyStrategy())
    engine.execute(data)
    results = engine.get_results()
    print(results)