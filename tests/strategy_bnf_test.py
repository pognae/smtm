import unittest
from smtm import StrategyBnf


def _candle(price, high=None, low=None, when="2020-12-20T00:00:00"):
    return {
        "market": "BTC",
        "date_time": when,
        "opening_price": price,
        "high_price": price if high is None else high,
        "low_price": price if low is None else low,
        "closing_price": price,
        "acc_price": 0,
        "acc_volume": 0,
    }


class StrategyBnfTests(unittest.TestCase):
    def _ready(self, lookback=3, drop_ratio=0.05, rebound_ratio=0.02, budget=1000000, min_price=5000):
        strategy = StrategyBnf()
        strategy.is_simulation = True
        strategy.initialize(budget, min_price)
        strategy.LOOKBACK = lookback
        strategy.DROP_RATIO = drop_ratio
        strategy.REBOUND_RATIO = rebound_ratio
        return strategy

    def _buy(self, strategy):
        request = strategy.get_request()[-1]
        strategy.update_result(
            {
                "type": "buy",
                "request": {"id": request["id"]},
                "price": request["price"],
                "amount": request["amount"],
                "msg": "success",
                "state": "done",
            }
        )
        return request

    def test_initialize_applies_params_without_changing_class_defaults(self):
        strategy = StrategyBnf()
        strategy.params = {"lookback": 30, "drop_ratio": 0.1, "rebound_ratio": 0.03}
        strategy.initialize(50000, 100)
        self.assertEqual(strategy.LOOKBACK, 30)
        self.assertEqual(strategy.DROP_RATIO, 0.1)
        self.assertEqual(strategy.REBOUND_RATIO, 0.03)
        self.assertEqual(StrategyBnf.LOOKBACK, 240)
        self.assertEqual(StrategyBnf.DROP_RATIO, 0.05)
        self.assertEqual(StrategyBnf.CODE, "BNF")
        self.assertNotEqual(strategy.CODE, "BNH")

    def test_warmup_does_not_order(self):
        strategy = self._ready()
        strategy.update_trading_info(_candle(100))
        strategy.update_trading_info(_candle(100))
        request = strategy.get_request()
        self.assertEqual(request[0]["amount"], 0)
        self.assertEqual(strategy.position, None)

    def test_drop_from_high_buys_and_stores_reference_high(self):
        strategy = self._ready()
        for _ in range(3):
            strategy.update_trading_info(_candle(100, high=100, low=99))
        strategy.update_trading_info(_candle(94, high=95, low=93))
        request = strategy.get_request()
        self.assertEqual(request[-1]["type"], "buy")
        self.assertEqual(request[-1]["price"], 94)
        self.assertGreater(request[-1]["amount"], 0)
        self.assertEqual(strategy.reference_high, 100)

    def test_rebound_from_entry_sells(self):
        strategy = self._ready()
        for _ in range(3):
            strategy.update_trading_info(_candle(100, high=100, low=99))
        strategy.update_trading_info(_candle(94, high=95, low=93))
        bought = self._buy(strategy)
        self.assertEqual(strategy.entry_price, 94)
        strategy.update_trading_info(_candle(96, high=96, low=94))
        request = strategy.get_request()
        self.assertEqual(request[-1]["type"], "sell")
        self.assertEqual(request[-1]["price"], 96)
        self.assertEqual(request[-1]["amount"], bought["amount"])

    def test_recovery_of_reference_high_sells_without_small_rebound(self):
        strategy = self._ready(rebound_ratio=0.5)
        for _ in range(3):
            strategy.update_trading_info(_candle(100, high=100, low=99))
        strategy.update_trading_info(_candle(94, high=95, low=93))
        self._buy(strategy)
        strategy.update_trading_info(_candle(100, high=101, low=99))
        request = strategy.get_request()
        self.assertEqual(request[-1]["type"], "sell")
        self.assertEqual(request[-1]["price"], 100)

    def test_min_price_blocks_order(self):
        strategy = self._ready(budget=1000, min_price=5000)
        for _ in range(3):
            strategy.update_trading_info(_candle(100, high=100, low=99))
        strategy.update_trading_info(_candle(94, high=95, low=93))
        request = strategy.get_request()
        self.assertEqual(request[0]["amount"], 0)
        strategy.is_simulation = False
        self.assertEqual(strategy.get_request(), None)
