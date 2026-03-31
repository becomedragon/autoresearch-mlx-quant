class DataCache:
    def __init__(self):
        self.data = {}

    def get_data(self, symbol, start_date, end_date):
        # Fetch data logic goes here
        pass

class StrategyEvaluator:
    def __init__(self, data_cache):
        self.data_cache = data_cache

    def evaluate(self, symbol, start_date, end_date, initial_capital, commission):
        # Strategy evaluation logic goes here
        pass

def evaluate_strategy_score(symbols, start_date, end_date, initial_capital, commission):
    data_cache = DataCache()
    evaluator = StrategyEvaluator(data_cache)
    scores = {}

    for symbol in symbols:
        score = evaluator.evaluate(symbol, start_date, end_date, initial_capital, commission)
        scores[symbol] = score

    return scores