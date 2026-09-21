"""돈치안 채널 돌파로 현물만 매수하는 터틀 롱 전략"""
import copy
import math
from datetime import datetime
from .strategy import Strategy
from .log_manager import LogManager
from .date_converter import DateConverter


class StrategyTurtle(Strategy):
    """
    종가가 직전 entry_n개 고점을 넘으면 전량 매수하고,
    직전 exit_m개 저점을 깨면 보유 수량을 전량 매도한다.
    공매도, 불타기, ATR 베팅은 하지 않는다.
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    COMMISSION_RATIO = 0.0005
    ENTRY_N = 240
    EXIT_M = 120
    NAME = "Turtle Long"
    CODE = "TUR"

    def __init__(self):
        self.is_intialized = False
        self.is_simulation = False
        self.data = []
        self.result = []
        self.add_spot_callback = None
        self.budget = 0
        self.balance = 0
        self.asset_amount = 0
        self.min_price = 0
        self.logger = LogManager.get_logger(__class__.__name__)
        self.waiting_requests = {}
        self.position = None

    def initialize(self, budget, min_price=5000, add_spot_callback=None):
        """예산을 설정하고 초기화한다"""
        if self.is_intialized:
            return

        self.apply_params(
            {
                "entry_n": "ENTRY_N",
                "exit_m": "EXIT_M",
                "commission_ratio": "COMMISSION_RATIO",
            }
        )
        self.ENTRY_N = int(self.ENTRY_N)
        self.EXIT_M = int(self.EXIT_M)
        self.is_intialized = True
        self.budget = budget
        self.balance = budget
        self.min_price = min_price
        self.add_spot_callback = add_spot_callback

    def get_request(self):
        """현재 포지션에 따라 거래 요청을 만든다. 신호가 없으면 시뮬레이션은 수량 0 매수를 반환한다."""
        if self.is_intialized is not True:
            return None

        try:
            last_data = self.data[-1]
            now = datetime.now().strftime(self.ISO_DATEFORMAT)
            if self.is_simulation:
                last_dt = datetime.strptime(self.data[-1]["date_time"], self.ISO_DATEFORMAT)
                now = last_dt.isoformat()

            if last_data is None or self.position is None:
                return self._empty_request(now)

            if self.position == "buy":
                request = self._create_buy(last_data["closing_price"])
            elif self.position == "sell":
                request = self._create_sell(last_data["closing_price"], self.asset_amount)
            else:
                request = None

            if request is None:
                return self._empty_request(now)

            request["date_time"] = now
            final_requests = []
            for request_id in self.waiting_requests:
                final_requests.append(
                    {
                        "id": request_id,
                        "type": "cancel",
                        "price": 0,
                        "amount": 0,
                        "date_time": now,
                    }
                )
            final_requests.append(request)
            return final_requests
        except (ValueError, KeyError) as msg:
            self.logger.error(f"invalid data {msg}")
        except IndexError:
            self.logger.error("empty data")
        except AttributeError as msg:
            self.logger.error(msg)

    def update_trading_info(self, info):
        """새 캔들을 반영하고 매수·매도 여부를 갱신한다"""
        if self.is_intialized is not True or info is None:
            return
        self.data.append(copy.deepcopy(info))
        self._update_position()

    def _update_position(self):
        """보유 중이면 저점 이탈만, 미보유면 고점 돌파만 본다"""
        self.position = None
        current = self.data[-1]
        close = float(current["closing_price"])

        if self.asset_amount > 0 and len(self.data) > self.EXIT_M:
            prior = self.data[-(self.EXIT_M + 1) : -1]
            trough = min(float(item["low_price"]) for item in prior)
            if close < trough:
                self.position = "sell"
                self.logger.debug(f"[TUR] SELL close {close} < {trough}")
            return

        if self.asset_amount <= 0 and len(self.data) > self.ENTRY_N:
            prior = self.data[-(self.ENTRY_N + 1) : -1]
            peak = max(float(item["high_price"]) for item in prior)
            if close > peak:
                self.position = "buy"
                self.logger.debug(f"[TUR] BUY close {close} > {peak}")

    def update_result(self, result):
        """체결 결과로 잔고와 보유 수량을 갱신한다"""
        if self.is_intialized is not True:
            return

        try:
            request = result["request"]
            if result["state"] == "requested":
                self.waiting_requests[request["id"]] = result
                return

            if result["state"] == "done" and request["id"] in self.waiting_requests:
                del self.waiting_requests[request["id"]]

            price = float(result["price"])
            amount = float(result["amount"])
            total = price * amount
            fee = total * self.COMMISSION_RATIO
            if result["type"] == "buy":
                self.balance -= round(total + fee)
            else:
                self.balance += round(total - fee)

            if result["msg"] == "success":
                if result["type"] == "buy":
                    self.asset_amount = round(self.asset_amount + amount, 6)
                elif result["type"] == "sell":
                    self.asset_amount = round(self.asset_amount - amount, 6)

            self.result.append(copy.deepcopy(result))
        except (AttributeError, TypeError, KeyError) as msg:
            self.logger.error(msg)

    def _empty_request(self, now):
        if self.is_simulation:
            return [
                {
                    "id": DateConverter.timestamp_id(),
                    "type": "buy",
                    "price": 0,
                    "amount": 0,
                    "date_time": now,
                }
            ]
        return None

    def _create_buy(self, price):
        req_price = float(price)
        if req_price <= 0:
            return None
        req_amount = self.balance / (req_price * (1 + self.COMMISSION_RATIO))
        req_amount = math.floor(req_amount * 10000) / 10000
        final_value = req_amount * req_price
        if req_amount <= 0 or self.min_price > final_value:
            self.logger.info(f"target_value is too small {final_value}")
            return None
        return {
            "id": DateConverter.timestamp_id(),
            "type": "buy",
            "price": req_price,
            "amount": req_amount,
        }

    def _create_sell(self, price, amount):
        req_amount = min(float(amount), self.asset_amount)
        req_amount = math.floor(req_amount * 10000) / 10000
        req_price = float(price)
        total_value = req_price * req_amount
        if req_amount <= 0 or total_value < self.min_price:
            self.logger.info(f"asset is too small {req_amount}, {total_value}")
            return None
        return {
            "id": DateConverter.timestamp_id(),
            "type": "sell",
            "price": req_price,
            "amount": req_amount,
        }
