"""Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

from .strategy_bnh import StrategyBuyAndHold
from .strategy_sma_0 import StrategySma0
from .strategy_rsi import StrategyRsi
from .strategy_sma_ml import StrategySmaMl


class StrategyFactory:
    """Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

    STRATEGY_LIST = [StrategyBuyAndHold, StrategySma0, StrategyRsi, StrategySmaMl]
    LEGACY_CODE = {"0": "BNH", "1": "SMA", "2": "RSI", "3": "SML"}

    @staticmethod
    def normalize_code(code):
        """숫자 별칭과 대소문자를 전략 코드로 맞춘다"""
        if code is None:
            return ""
        text = str(code).strip()
        if text in StrategyFactory.LEGACY_CODE:
            return StrategyFactory.LEGACY_CODE[text]
        return text.upper()

    @staticmethod
    def create(code, params=None):
        """code에 해당하는 Strategy 객체를 생성하여 반환

        params: 전략 클래스 상수를 덮어쓸 선택 딕셔너리. 없으면 기본값.
        """
        normalized = StrategyFactory.normalize_code(code)
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == normalized:
                instance = strategy()
                instance.params = params
                return instance
        return None

    @staticmethod
    def get_name(code):
        """code에 해당하는 Strategy 이름을 반환"""
        normalized = StrategyFactory.normalize_code(code)
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == normalized:
                return strategy.NAME
        return None

    @staticmethod
    def get_all_strategy_info():
        """전체 Strategy 정보를 반환"""
        all_strategy = []
        for strategy in StrategyFactory.STRATEGY_LIST:
            all_strategy.append({"name": strategy.NAME, "code": strategy.CODE, "class": strategy})
        return all_strategy
