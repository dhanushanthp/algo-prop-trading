from modules.meta import util
from modules.common import files_util
from modules.common.Directions import Directions
import modules.meta.Currencies as curr
from modules.meta.Indicators import Indicators
from modules.meta.Strategies import Strategies
from modules.meta.Account import Account


class DelayedEntry:
    def __init__(self, indicators:Indicators, strategies:Strategies):
        self.indicators = indicators
        self.strategies = strategies
        self.account = Account()
        self.account_id = self.account.get_account_id()

    def symbol_price_recorder(self, strategy:Directions, symbols:list):
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
        if strategy != "UNKNOWN":
            current_date = util.get_current_time().strftime('%Y-%m-%d')
            file_path = f"PnLData/price_tracker/{self.account_id}_{current_date}.csv"
            if not files_util.check_file_exists(file_path=file_path):
                with open(file_path, mode="w") as file:
                    file.write("Symbol,Direction,Entry Price\n")
                
                for symbol in symbols:
                    # Find each symbol direction
                    symbol_direction = self.strategies.previous_day_close(symbol=symbol)
                    entry_price = self.indicators.prices.get_exchange_price(symbol=symbol)

                    if strategy == "BREAK":
                        trade_direction = symbol_direction.name
                    else:
                        trade_direction = "LONG" if symbol_direction.name == "SHORT" else "SHORT"
                    
                    with open(file_path, mode="a") as file:
                        file.write(f"{symbol},{trade_direction},{entry_price}\n")
        else:
            print("Strategy is UNKNOWN")

if __name__ == "__main__":
    from modules.meta.Prices import Prices
    from modules.meta.wrapper import Wrapper
    indicator = Indicators(wrapper=Wrapper(), prices=Prices())
    strategy = Strategies(indicators=indicator, wrapper=Wrapper())
    delayed_entry = DelayedEntry(indicators=indicator, strategies=strategy)
    dominant_direction = indicator.get_dominant_direction()
    delayed_entry.symbol_price_recorder(strategy=dominant_direction, symbols=curr.get_symbols(symbol_selection="PRIMARY"))