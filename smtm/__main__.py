"""smtm 모듈의 시작
mode:
    0: simulator with interative mode
    1: execute single simulation
    2: controller for real trading
    3: telegram chatbot controller
    4: mass simulation with config file
    5: make config file for mass simulation

Example)
python -m smtm --mode 0
python -m smtm --mode 1
python -m smtm --mode 1 --budget 500 --from_dash_to 201220.170000-201221 --term 1 --strategy BNH --currency BTC
python -m smtm --mode 2 --budget 50000 --term 60 --strategy BNH --currency ETH
python -m smtm --mode 2 --budget 50000 --term 60 --strategy BNH --currency ETH --demo 1
python -m smtm --mode 3
python -m smtm --mode 3 --demo 1
python -m smtm --mode 4 --config /data/sma0_simulation.json
python -m smtm --mode 5 --budget 50000 --title SMA_2H_week --strategy SMA --currency ETH --from_dash_to 210804.000000-210811.000000 --offset 120 --file generated_config.json
"""
import argparse
from argparse import RawTextHelpFormatter
import json
import sys
from .simulator import Simulator
from .controller import Controller
from .telegram_controller import TelegramController
from .mass_simulator import MassSimulator
from .log_manager import LogManager
from .__init__ import __version__

if __name__ == "__main__":
    DEFAULT_MODE = 6
    parser = argparse.ArgumentParser(
        description="""자동 거래 시스템 smtm

mode:
    0: simulator with interative mode
    1: execute single simulation
    2: controller for real trading
    3: telegram chatbot controller
    4: mass simulation with config file
    5: make config file for mass simulation

Example)
python -m smtm --mode 0
python -m smtm --mode 1 --budget 50000 --from_dash_to 201220.170000-201221 --term 0.1 --strategy BNH --currency BTC
python -m smtm --mode 2 --budget 50000 --term 60 --strategy BNH --currency ETH
python -m smtm --mode 3
python -m smtm --mode 3 --demo 1 --token <telegram chat-bot token> --chatid <chat id>
python -m smtm --mode 4 --config /data/sma0_simulation.json
python -m smtm --mode 5 --budget 50000 --title SMA_6H_week --strategy SMA --currency ETH --from_dash_to 210804.000000-210811.000000 --offset 360 --file generated_config.json
""",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument("--budget", help="budget", type=int, default=10000)
    parser.add_argument("--term", help="trading tick interval (seconds)", type=float, default="60")
    parser.add_argument("--strategy", help="BNH: buy and hold, SMA: sma, RSI: rsi", default="BNH")
    parser.add_argument("--trader", help="trader 0: Upbit, 1: Bithumb", default="0")
    parser.add_argument("--currency", help="trading currency e.g.BTC", default="BTC")
    parser.add_argument("--config", help="mass simulation config file", default="")
    parser.add_argument(
        "--process",
        help="process number for mass simulation. default -1 use cpu number",
        type=int,
        default=-1,
    )
    parser.add_argument("--title", help="mass simulation title", default="SMA_2H_week")
    parser.add_argument("--file", help="generated config file name", default=None)
    parser.add_argument("--offset", help="mass simulation period offset", type=int, default=120)
    parser.add_argument("--log", help="log file name", default=None)
    parser.add_argument("--demo", help="use demo trader", type=int, default=0)
    parser.add_argument("--slippage", help="simulation slippage ratio. 0.001 = 0.1%%", type=float, default=0)
    parser.add_argument(
        "--max_loss",
        help="stop when cumulative return <= -max_loss percent. 0 disables",
        type=float,
        default=0,
    )
    parser.add_argument(
        "--strategy_params",
        help='strategy parameter JSON e.g. {"short": 5, "mid": 20, "long": 30}',
        default=None,
    )
    parser.add_argument("--token", help="telegram chat-bot token", default=None)
    parser.add_argument("--chatid", help="telegram chat id", default=None)
    parser.add_argument(
        "--mode",
        help="0: interactive simulator, 1: single simulation, 2: real trading",
        type=int,
        default=DEFAULT_MODE,
    )
    parser.add_argument(
        "--from_dash_to",
        help="simulation period ex) 201220.170000-201220.180000",
        default="201220.170000-201220.180000",
    )
    parser.add_argument("--version", action="version", version=f'smtm version: {__version__}')
    args = parser.parse_args()
    strategy_params = None
    if args.strategy_params:
        try:
            strategy_params = json.loads(args.strategy_params)
        except json.JSONDecodeError:
            print("invalid --strategy_params JSON")
            sys.exit(1)
        if not isinstance(strategy_params, dict):
            print("--strategy_params must be a JSON object")
            sys.exit(1)

    if args.log is not None:
        LogManager.change_log_file(args.log)

    if args.mode < 2:
        simulator = Simulator(
            budget=args.budget,
            interval=args.term,
            strategy=args.strategy,
            currency=args.currency,
            from_dash_to=args.from_dash_to,
            strategy_params=strategy_params,
            slippage=args.slippage,
            max_loss=args.max_loss,
        )

    if args.mode == DEFAULT_MODE:
        parser.print_help()
        sys.exit(0)

    if args.mode == 0:
        simulator.main()
    elif args.mode == 1:
        simulator.run_single()
    elif args.mode == 2:
        controller = Controller(
            budget=args.budget,
            interval=args.term,
            strategy=args.strategy,
            currency=args.currency,
            is_bithumb=args.trader == "1",
            is_demo=args.demo == 1,
            strategy_params=strategy_params,
            max_loss=args.max_loss,
        )
        controller.main()
    elif args.mode == 3:
        tcb = TelegramController(token=args.token, chatid=args.chatid, max_loss=args.max_loss)
        if tcb.TOKEN == "telegram_token" and args.token is None:
            print("Please check your telegram chat-bot token")
            sys.exit(0)

        tcb.main(demo=args.demo == 1)
    elif args.mode == 4:
        if args.config == "":
            parser.print_help()
            sys.exit(0)

        mass = MassSimulator()
        mass.run(args.config, args.process)
    elif args.mode == 5:
        result = MassSimulator.make_config_json(
            title=args.title,
            budget=args.budget,
            strategy_code=args.strategy,
            currency=args.currency,
            from_dash_to=args.from_dash_to,
            offset_min=args.offset,
            filepath=args.file,
        )
        print(f"{result} is generated")
