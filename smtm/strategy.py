"""데이터를 기반으로 매매 결정을 생성하는 Strategy 추상클래스"""
from abc import ABCMeta, abstractmethod


class Strategy(metaclass=ABCMeta):
    """
    데이터를 받아서 매매 판단을 하고 결과를 받아서 다음 판단에 반영하는 전략 클래스
    """

    CODE = "---"
    NAME = "---"

    def apply_params(self, key_to_attr):
        """params에 있는 값만 인스턴스 속성으로 덮어쓴다. 없으면 클래스 기본값을 유지한다."""
        params = getattr(self, "params", None) or {}
        for key, attr in key_to_attr.items():
            if key in params and params[key] is not None:
                setattr(self, attr, params[key])

    def sync_from_account(self, balance, asset_amount=0):
        """거래소 계좌 조회로 전략의 현금과 코인 수량을 맞춘다"""
        self.balance = balance
        if hasattr(self, "asset_amount"):
            self.asset_amount = asset_amount

    @abstractmethod
    def initialize(self, budget, min_price=100, add_spot_callback=None):
        """예산을 설정하고 초기화한다

        budget: 예산
        min_price: 최소 거래 금액, 거래소의 최소 거래 금액
        add_spot_callback(date_time, value): 그래프에 그려질 spot을 추가하는 콜백 함수
        """

    @abstractmethod
    def get_request(self):
        """전략에 따라 거래 요청 정보를 생성한다

        Returns: 배열에 한 개 이상의 요청 정보를 전달
        [{
            "id": 요청 정보 id "1607862457.560075"
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "date_time": 요청 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간
        }]
        """

    @abstractmethod
    def update_trading_info(self, info):
        """새로운 거래 정보를 업데이트

        info:
        {
            "market": 거래 시장 종류 BTC
            "date_time": 정보의 기준 시간
            "opening_price": 시작 거래 가격
            "high_price": 최고 거래 가격
            "low_price": 최저 거래 가격
            "closing_price": 마지막 거래 가격
            "acc_price": 단위 시간내 누적 거래 금액
            "acc_volume": 단위 시간내 누적 거래 양
        }
        """

    @abstractmethod
    def update_result(self, result):
        """요청한 거래의 결과를 업데이트
        request: 거래 요청 정보
        result:
        {
            "request": 요청 정보
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "state": 거래 상태 requested, done
            "msg": 거래 결과 메세지
            "date_time": 거래 체결 시간, 시뮬레이션 모드에서는 데이터 시간 +2초
        }
        """
