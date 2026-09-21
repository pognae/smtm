"""최근 고점 대비 급락 후 반등을 매매하는 BNF 전략"""
import copy
import math
from datetime import datetime
from .strategy import Strategy
from .log_manager import LogManager
from .date_converter import DateConverter


class StrategyBnf(Strategy):
    """
    직전 lookback개 고점보다 drop_ratio 이상 내린 종가에 전량 매수한다.
    진입가 대비 rebound_ratio 반등하거나, 진입 때 저장한 고점을 회복하면 전량 매도한다.
    Buy and Hold(BNH)와 다르며, RSI와 펀딩은 보지 않는다.
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    COMMISSION_RATIO = 0.0005
    LOOKBACK = 240
    DROP_RATIO = 0.05
    REBOUND_RATIO = 0.02
    NAME = "BNF"
    CODE = "BNF"

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
        self.entry_price = None
        self.reference_high = None

    def initialize(self, budget, min_price=5000, add_spot_callback=None):
        """예산을 설정하고 초기화한다"""
        if self.is_intialized:
            return

        self.apply_params(
            {
                "lookback": "LOOKBACK",
                "drop_ratio": "DROP_RATIO",
                "rebound_ratio": "REBOUND_RATIO",
                "commission_ratio": "COMMISSION_RATIO",
            }
        )
        self.LOOKBACK = int(self.LOOKBACK)
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
        """미보유면 낙폭 매수, 보유면 반등 또는 고점 회복 매도만 본다"""
        self.position = None
        if len(self.data) <= self.LOOKBACK:
            return

        current = self.data[-1]
        close = float(current["closing_price"])
        prior = self.data[-(self.LOOKBACK + 1) : -1]
        peak = max(float(item["high_price"]) for item in prior)

        if self.asset_amount > 0 and self.entry_price:
            rebound = self.entry_price * (1 + self.REBOUND_RATIO)
            if close >= rebound or (
                self.reference_high is not None and close >= self.reference_high
            ):
                self.position = "sell"
                self.logger.debug(f"[BNF] SELL close {close}, entry {self.entry_price}")
            return

        if self.asset_amount > 0:
            return

        if close <= peak * (1 - self.DROP_RATIO):
            self.reference_high = peak
            self.position = "buy"
            self.logger.debug(f"[BNF] BUY close {close} <= {peak} drop")
        else:
            self.reference_high = None

    def update_result(self, result):
        """체결 결과로 잔고, 보유 수량, 진입가를 갱신한다"""
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
                    self.entry_price = price
                elif result["type"] == "sell":
                    self.asset_amount = round(self.asset_amount - amount, 6)
                    if self.asset_amount <= 0:
                        self.entry_price = None
                        self.reference_high = None

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
