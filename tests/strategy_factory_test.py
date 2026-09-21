import unittest
from smtm import StrategyFactory, StrategyBuyAndHold, StrategySma0, StrategyRsi, StrategySmaMl
from unittest.mock import *


class StrategyFactoryTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_create_return_None_when_called_with_invalid_code(self):
        strategy = StrategyFactory.create("")
        self.assertEqual(strategy, None)

    def test_create_return_correct_strategy(self):
        self.assertTrue(isinstance(StrategyFactory.create("BNH"), StrategyBuyAndHold))
        self.assertTrue(isinstance(StrategyFactory.create("SMA"), StrategySma0))
        self.assertTrue(isinstance(StrategyFactory.create("RSI"), StrategyRsi))
        self.assertTrue(isinstance(StrategyFactory.create("SML"), StrategySmaMl))

    def test_create_return_legacy_code(self):
        self.assertTrue(isinstance(StrategyFactory.create(0), StrategyBuyAndHold))
        self.assertTrue(isinstance(StrategyFactory.create("1"), StrategySma0))
        self.assertTrue(isinstance(StrategyFactory.create("2"), StrategyRsi))
        self.assertTrue(isinstance(StrategyFactory.create(3), StrategySmaMl))
        self.assertEqual(StrategyFactory.get_name("0"), StrategyBuyAndHold.NAME)
        self.assertEqual(StrategyFactory.get_name(1), StrategySma0.NAME)

    def test_create_keeps_strategy_params_until_initialize(self):
        strategy = StrategyFactory.create("SMA", params={"short": 5, "mid": 15, "long": 20})
        self.assertEqual(strategy.SHORT, StrategySma0.SHORT)
        strategy.initialize(10000)
        self.assertEqual(strategy.SHORT, 5)
        self.assertEqual(strategy.MID, 15)
        self.assertEqual(strategy.LONG, 20)
        self.assertEqual(StrategySma0.SHORT, 10)

    def test_get_name_return_None_when_called_with_invalid_code(self):
        strategy = StrategyFactory.get_name("")
        self.assertEqual(strategy, None)

    def test_get_name_return_correct_strategy(self):
        self.assertTrue(StrategyFactory.get_name("BNH"), StrategyBuyAndHold.NAME)
        self.assertTrue(StrategyFactory.get_name("SMA"), StrategySma0.NAME)
        self.assertTrue(StrategyFactory.get_name("RSI"), StrategyRsi.NAME)
        self.assertTrue(StrategyFactory.get_name("SML"), StrategySmaMl.NAME)

    def test_get_all_strategy_info_return_correct_info(self):
        all = StrategyFactory.get_all_strategy_info()
        self.assertTrue(all[0]["name"], StrategyBuyAndHold.NAME)
        self.assertTrue(all[0]["code"], StrategyBuyAndHold.CODE)
        self.assertTrue(all[0]["class"], StrategyBuyAndHold)
        self.assertTrue(all[1]["name"], StrategySma0.NAME)
        self.assertTrue(all[1]["code"], StrategySma0.CODE)
        self.assertTrue(all[1]["class"], StrategySma0)
        self.assertTrue(all[2]["name"], StrategyRsi.NAME)
        self.assertTrue(all[2]["code"], StrategyRsi.CODE)
        self.assertTrue(all[2]["class"], StrategyRsi)
        self.assertTrue(all[3]["name"], StrategySmaMl.NAME)
        self.assertTrue(all[3]["code"], StrategySmaMl.CODE)
        self.assertTrue(all[3]["class"], StrategySmaMl)
