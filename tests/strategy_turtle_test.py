import unittest
from smtm import StrategyTurtle


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


class StrategyTurtleTests(unittest.TestCase):
    def _ready(self, entry_n=3, exit_m=2, budget=1000000, min_price=5000):
        strategy = StrategyTurtle()
        strategy.is_simulation = True
        strategy.initialize(
            budget,
            min_price,
        )
        strategy.ENTRY_N = entry_n
        strategy.EXIT_M = exit_m
        return strategy

    def test_initialize_keeps_class_defaults_and_applies_params(self):
        strategy = StrategyTurtle()
        strategy.params = {"entry_n": 20, "exit_m": 10}
        strategy.initialize(50000, 100)
        self.assertEqual(strategy.ENTRY_N, 20)
        self.assertEqual(strategy.EXIT_M, 10)
        self.assertEqual(strategy.min_price, 100)
        self.assertEqual(StrategyTurtle.ENTRY_N, 240)
        self.assertEqual(StrategyTurtle.EXIT_M, 120)
        strategy.initialize(1, 1)
        self.assertEqual(strategy.budget, 50000)

    def test_warmup_does_not_order(self):
        strategy = self._ready()
        strategy.update_trading_info(_candle(10))
        strategy.update_trading_info(_candle(10))
        request = strategy.get_request()
        self.assertEqual(request[0]["amount"], 0)
        self.assertEqual(strategy.position, None)

    def test_breakout_buys_full_balance(self):
        strategy = self._ready()
        for _ in range(3):
            strategy.update_trading_info(_candle(10, high=10, low=9))
        strategy.update_trading_info(_candle(11, high=12, low=10))
        request = strategy.get_request()
        self.assertEqual(request[-1]["type"], "buy")
        self.assertEqual(request[-1]["price"], 11)
        self.assertGreater(request[-1]["amount"], 0)

    def test_holding_does_not_buy_again_until_exit(self):
        strategy = self._ready()
        for _ in range(3):
            strategy.update_trading_info(_candle(10, high=10, low=9))
        strategy.update_trading_info(_candle(11, high=12, low=11))
        buy = strategy.get_request()[-1]
        strategy.update_result(
            {
                "type": "buy",
                "request": {"id": buy["id"]},
                "price": 11,
                "amount": buy["amount"],
                "msg": "success",
                "state": "done",
            }
        )
        strategy.update_trading_info(_candle(13, high=14, low=12))
        request = strategy.get_request()
        self.assertEqual(request[0]["amount"], 0)
        self.assertEqual(strategy.position, None)

    def test_close_below_prior_low_sells_holding(self):
        strategy = self._ready()
        for _ in range(3):
            strategy.update_trading_info(_candle(10, high=10, low=9))
        strategy.update_trading_info(_candle(11, high=12, low=11))
        buy = strategy.get_request()[-1]
        strategy.update_result(
            {
                "type": "buy",
                "request": {"id": buy["id"]},
                "price": 11,
                "amount": buy["amount"],
                "msg": "success",
                "state": "done",
            }
        )
        strategy.update_trading_info(_candle(11, high=12, low=11))
        self.assertEqual(strategy.position, None)
        strategy.update_trading_info(_candle(7, high=8, low=7))
        request = strategy.get_request()
        self.assertEqual(request[-1]["type"], "sell")
        self.assertEqual(request[-1]["price"], 7)
        self.assertEqual(request[-1]["amount"], buy["amount"])

    def test_min_price_blocks_order(self):
        strategy = self._ready(budget=1000, min_price=5000)
        for _ in range(3):
            strategy.update_trading_info(_candle(10, high=10, low=9))
        strategy.update_trading_info(_candle(11, high=12, low=10))
        request = strategy.get_request()
        self.assertEqual(request[0]["amount"], 0)

        strategy.is_simulation = False
        self.assertEqual(strategy.get_request(), None)
