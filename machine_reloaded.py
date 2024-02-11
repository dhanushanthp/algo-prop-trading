import MetaTrader5 as mt
import time
import argparse

import modules.indicators as ind
import modules.util as util
import objects.Currencies as curr
from objects.RiskManager import RiskManager
import modules.config as config
from modules.slack_msg import Slack
from objects.Prices import Prices
from objects.Orders import Orders
from objects.Account import Account

class MachineReloaded():
    def __init__(self, trading_timeframe:int):
        # MetaTrader initialization
        mt.initialize()

        # Default values
        self.target_ratio = 3.0  # Default 1:0.5 Ratio
        self.stop_ratio = 1.0
        self.immidiate_exit = False
        self.timer = 30
        self.retries = 0

        # External dependencies
        self.risk_manager = RiskManager(stop_ratio=self.stop_ratio, target_ratio=self.target_ratio)
        self.prices = Prices()
        self.orders = Orders(prices=self.prices, risk_manager=self.risk_manager)
        self.alert = Slack()
        self.account = Account()
        

        # Account information
        self.account_name = self.account.get_account_name()

        # Expected reward for the day
        self.fixed_initial_account_size = self.risk_manager.account_size

        # Default
        self.trading_timeframe = trading_timeframe

        # Take the profit as specific RR ratio
        self.partial_profit_rr = False
        self.partial_rr=self.risk_manager.account_risk_percentage
    
    def main(self):
        selected_symbols = ind.get_ordered_symbols()
        
        while True:
            print(f"\n------- {config.local_ip.replace('_', '.')} @ {util.get_current_time().strftime('%H:%M:%S')} in {self.trading_timeframe} TF & PartialProfit:{self.partial_profit_rr} with ({self.partial_rr} RR) ------------------")
            is_market_open, is_market_close = util.get_market_status()
            equity = self.account.get_equity()
            rr = (equity - self.fixed_initial_account_size)/self.risk_manager.risk_of_an_account
            pnl = (equity - self.risk_manager.account_size)
            print(f"{'Acc Trail Loss'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
            print(f"{'Acc at Risk'.ljust(20)}: {'{:,}'.format(round(((self.risk_manager.get_max_loss() - self.fixed_initial_account_size)/self.fixed_initial_account_size) * 100, 2))}%, ${self.risk_manager.get_max_loss()}")
            print(f"{'Next Trail at'.ljust(20)}: ${'{:,}'.format(round(self.risk_manager.get_max_loss() + self.risk_manager.risk_of_an_account))}")
            print(f"{'Risk:Reward'.ljust(20)}: {round(rr, 3)}")
            print(f"{'PnL'.ljust(20)}: ${round(pnl, 2)}")

            # Record PnL
            if pnl != 0:
                with open(f'{config.local_ip}_{util.get_current_time().strftime("%Y%m%d")}.csv', 'a') as file:
                    file.write(f"{util.get_current_time().strftime('%Y/%m/%d %H:%M:%S')},break,{self.retries},{round(rr, 3)},{round(pnl, 3)}\n")

            # Each position trail stop
            self.risk_manager.adjust_positions_trailing_stops(target_multiplier=self.target_ratio, trading_timeframe=self.trading_timeframe) 

            if self.partial_profit_rr:
                if rr > self.partial_rr:
                    self.immidiate_exit = True
                    self.orders.close_all_positions()

            if self.risk_manager.has_daily_maximum_risk_reached():
                self.immidiate_exit = True
                self.orders.close_all_positions()
                time.sleep(30) # Take some time for the account to digest the positions                
                self.alert.send_msg(f"{self.account_name}: Done for today!, Account RR: {round(rr, 2)}")

            if is_market_close:
                print("Market Close!")
                self.risk_manager = RiskManager() # Reset the risk for the day
                self.orders.close_all_positions()
                
                # Reset account size for next day
                self.fixed_initial_account_size = self.risk_manager.account_size
                self.immidiate_exit = False
            
            if is_market_open and (not is_market_close) and (not self.immidiate_exit):
                self.orders.cancel_all_pending_orders()
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))

                for symbol in selected_symbols:
                    if symbol in existing_positions:
                        continue

                    king_of_levels = ind.get_king_of_levels(symbol=symbol)

                    resistances = king_of_levels[0]
                    support = king_of_levels[1]

                    current_candle = mt.copy_rates_from_pos(symbol, util.match_timeframe(self.trading_timeframe), 0, 1)[-1]

                    for resistance_level in resistances:
                        if current_candle["open"] < resistance_level and current_candle["close"] > resistance_level:
                            print(f"{symbol.ljust(12)} Resistance: {resistance_level}")
                            self.orders.long_entry(symbol=symbol, break_level=resistance_level, trading_timeframe=self.trading_timeframe)
                            break
                    
                    for support_level in support:               
                        if current_candle["open"] > support_level and current_candle["close"] < support_level:
                            print(f"{symbol.ljust(12)} Support: {support_level}")
                            self.orders.short_entry(symbol=symbol, break_level=support_level, trading_timeframe=self.trading_timeframe)
                            break

            time.sleep(self.timer)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Example script with named arguments.')

    parser.add_argument('--partial_profit_rr', type=str, help='Partial Profit RR')
    parser.add_argument('--partial_rr', type=float, help='Partial Profit RR')
    parser.add_argument('--timeframe', type=str, help='Selected timeframe for trade')
    args = parser.parse_args()
    
    
    trading_timeframe = int(args.timeframe)
    win = MachineReloaded(trading_timeframe=trading_timeframe)

    win.partial_profit_rr = util.boolean(args.partial_profit_rr)
    win.partial_rr = args.partial_rr 

    win.main()

