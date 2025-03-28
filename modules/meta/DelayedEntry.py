from modules.meta import util
from modules.common import files_util
from modules.common.Directions import Directions
import modules.meta.Currencies as curr
from modules.meta.Indicators import Indicators
from modules.meta.Strategies import Strategies
from modules.meta.Account import Account
import pandas as pd
from modules.meta.RiskManager import RiskManager


class DelayedEntry:
    def __init__(self, indicators:Indicators, strategies:Strategies, risk_manager:RiskManager):
        self.indicators = indicators
        self.strategies = strategies
        self.account = Account()
        self.risk_manager = risk_manager
        self.account_id = self.account.get_account_id()

    def symbol_price_recorder(self, symbols:list):
        """
        Records the price of symbols based on the given strategy.
        Args:
            strategy (Directions): The trading strategy direction (e.g., "BREAK", "LONG", "SHORT", etc.).
            symbols (list): A list of symbols to record prices for.
        Writes:
            A CSV file in the format "PnLData/price_tracker/{account_id}_{current_date}.csv" with the following columns:
            - Symbol: The symbol being recorded.
            - Direction: The trade direction based on the strategy.
            - Entry Price: The entry price of the symbol.
        If the strategy is "UNKNOWN", it prints a message indicating that the strategy is unknown.
        """
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/price_tracker/{self.account_id}_{current_date}.csv"
        if not files_util.check_file_exists(file_path=file_path):
            strategy = self.indicators.get_dominant_direction()
            if strategy != "UNKNOWN":
                with open(file_path, mode="w") as file:
                    file.write("symbol,direction,entry_price,volume\n")
                
                # Validate all the symbols entries in the file
                counter = 0
                for symbol in symbols:
                    symbol_direction = self.strategies.previous_day_close(symbol=symbol)
                    counter += 1
                
                # Just to make sure that we covered all the symbols
                if counter == len(symbols):
                    for symbol in symbols:
                        # Find each symbol direction
                        symbol_direction = self.strategies.previous_day_close(symbol=symbol)
                        entry_price = self.indicators.prices.get_exchange_price(symbol=symbol)
                        shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=15, buffer_ratio=0)
                        _, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_long_stop)
                        
                        if symbol_direction:
                            if strategy == "BREAK":
                                trade_direction = symbol_direction.name
                            else:
                                trade_direction = "LONG" if symbol_direction.name == "SHORT" else "SHORT"
                            
                            with open(file_path, mode="a") as file:
                                file.write(f"{symbol},{trade_direction},{entry_price},{lots}\n")
            else:
                print("Strategy is UNKNOWN")

    def directional_pnl(self, entry, current, direction):
        """
        Calculate the profit and loss (PnL) based on the entry price, current price, and trade direction.

        Args:
            entry (float): The entry price of the trade.
            current (float): The current price of the trade.
            direction (int): The direction of the trade. 
                        0 for long (buy) position, 1 for short (sell) position.

        Returns:
            float: The calculated PnL. Positive value indicates profit, negative value indicates loss.
        """
        if direction == "LONG":
            return current - entry
        elif direction == "SHORT":
            return entry - current

    def price_by_direction(self, symbol, direction):
        # if direction == "LONG":
        #     # For long position, the stop is hit by the bid, Because the stop is a sell. 
        #     price, _ = self.indicators.prices.get_bid_ask(symbol=symbol)
        # elif direction == "SHORT":
        #     # For long position, the stop is hit by the ask, Because the stop is a buy.
        #     _, price = self.indicators.prices.get_bid_ask(symbol=symbol)

        price = self.indicators.prices.get_exchange_price(symbol=symbol)
        return price

    def delayed_rr(self):
        """
        Calculate the risk-reward ratio (RR) for the current date based on the account's price tracker data.
        This method performs the following steps:
        1. Retrieves the current date.
        2. Constructs the file path for the price tracker CSV file based on the account ID and current date.
        3. Checks if the CSV file exists.
        4. If the file exists, reads the data from the CSV file.
        5. Updates the current price for each symbol in the data.
        6. Calculates the change in price for each entry.
        7. Calculates the profit and loss (PnL) for each position.
        8. Sums up the total PnL.
        9. Calculates the risk-reward ratio (RR) by dividing the total PnL by the account's risk.
        Returns:
            float: The calculated risk-reward ratio (RR) rounded to two decimal places.
        """
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/price_tracker/{self.account_id}_{current_date}.csv"
        if files_util.check_file_exists(file_path=file_path):
            data = pd.read_csv(file_path)
            data["current_price"] = data.apply(lambda x: self.price_by_direction(symbol=x["symbol"], direction=x["direction"]) , axis=1)
            data["change"] =  data.apply(lambda x: self.directional_pnl(entry=x["entry_price"], current=x["current_price"], direction=x["direction"]) , axis=1)
            data["pnl"] = data.apply(lambda x: self.risk_manager.get_pnl_of_position(symbol=x["symbol"], lots=x["volume"], points_in_stop=x["change"]), axis=1)
            commission = self.risk_manager.risk_of_an_account * 0.05 # 5% of the account
            total_pnl = round(data["pnl"].sum() - commission, 2)
            rr = round((total_pnl/self.risk_manager.risk_of_an_account), 2)
            self.record_pnl_logs(rr=rr)
            return rr
        
        return 0.0

    def is_max_ranged(self):
        """
        Checks if the range of the 'RR' column in the historical price tracker file exceeds 1.
        This method constructs a file path based on the current date and the account ID, 
        and checks if the file exists. If the file exists, it reads the file into a pandas 
        DataFrame, calculates the minimum and maximum values of the 'RR' column, and 
        determines if the difference between the maximum and minimum values is greater than 1.
        Returns:
            bool: True if the range of the 'RR' column exceeds 1, False otherwise.
        """
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/price_tracker_history/{self.account_id}_{current_date}_hist.csv"
        if files_util.check_file_exists(file_path=file_path):
            data = pd.read_csv(file_path)
            min_index = data.iloc[data["RR"].idxmin()]
            max_index = data.iloc[data["RR"].idxmax()]
            latest_index = data.iloc[-1]
            print(f"{'Ranged RR Changed'.ljust(20)}: {round(max_index['RR'] - min_index['RR'], 2)}, Latest: {round(max_index['RR'] - latest_index['RR'], 2)}")

            # Only when the RR is below -0.5
            if latest_index["RR"] < -0.5:
                # The RR between min and max should be greater than 1, Saying that It should have moved 1R below from the high.
                if (max_index["RR"] - min_index["RR"] > 1.0):
                    # The timestamp which has the minimum should be the latest
                    if min_index["Timestamp"] >  max_index["Timestamp"]:
                        print(f"{'RR Max'.ljust(20)}: {max_index['RR']}")
                        print(f"{'RR Min'.ljust(20)}: {min_index['RR']}")
                        return True
                # The RR between max and latest should be greater than 1, Saying that It should have moved 1R below from the high.
                if (max_index["RR"] - latest_index["RR"] > 1.0):
                    # The timestamp which has the minimum should be the latest
                    if latest_index["Timestamp"] >  max_index["Timestamp"]:
                        print(f"{'RR Max'.ljust(20)}: {max_index['RR']}")
                        print(f"{'RR Latest'.ljust(20)}: {latest_index['RR']}")
                        return True
            
        return False

    def record_pnl_logs(self, rr):
        """
        Records profit and loss (PnL) logs along with risk-reward (RR) ratio to a CSV file.
        This method creates a new CSV file for each day if it does not already exist, 
        and appends the PnL and RR data with a timestamp to the file.
        Args:
            pnl (float): The profit and loss value to be recorded.
            rr (float): The risk-reward ratio to be recorded.
        Returns:
            None
        """
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/price_tracker_history/{self.account_id}_{current_date}_hist.csv"

        if not files_util.check_file_exists(file_path=file_path):
            with open(file_path, mode="w") as file:
                file.write("Timestamp,RR\n")

        with open(file_path, mode="a") as file:
            file.write(f"{util.get_current_time().strftime('%Y-%m-%d %H:%M:%S')},{round(rr, 2)}\n")
    

if __name__ == "__main__":
    from modules.meta.Prices import Prices
    from modules.meta.wrapper import Wrapper
    indicator = Indicators(wrapper=Wrapper(), prices=Prices())
    strategy = Strategies(indicators=indicator, wrapper=Wrapper())
    delayed_entry = DelayedEntry(indicators=indicator, strategies=strategy)
    dominant_direction = indicator.get_dominant_direction()
    delayed_entry.symbol_price_recorder(strategy=dominant_direction, symbols=curr.get_symbols(symbol_selection="PRIMARY"))