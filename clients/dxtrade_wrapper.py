import requests
from clients.rest import Rest
import uuid
import pandas as pd

class DXTrade:
    def __init__(self) -> None:
        self.rest_service  = Rest()
        self.access_token = None
        self.access_token_header = None

    def login(self):
        payload = {
                    "username": "1210008442",
                    "domain": "default",
                    "password": "r9*2!@TR"
                }
        
        status_code, response = self.rest_service.post_request(url="login", payload=payload)
        if status_code == 200:
            self.access_token = response["sessionToken"]
            self.access_token_header =  {"Authorization": f"DXAPI {self.access_token}", 'Content-Type': 'application/json'}

    def ping(self):
        status_code, _ = self.rest_service.post_request(url="ping", payload=None, headers=self.access_token_header)
        if status_code != 200:
            raise Exception("Ping failed!")
    
    def get_candles(self, symbol, timeframe):
        payload = {
                "symbols": [
                    symbol
                ],
                "eventTypes": [
                    {
                    "type": "Candle",
                    "format": "COMPACT",
                    "candleType": "h"
                    }
                ]}
        status_code, response = self.rest_service.post_request(url="marketdata", payload=payload, headers=self.access_token_header)
        print(status_code, response)

    def get_exchange_price(self, symbol):
        # https://demo.dx.trade/developers/#/DXtrade-Push-API?id=market-data-subscription
        # https://demo.dx.trade/developers/#/DXtrade-Push-API?id=market-data
        payload = {
                "symbols": [
                    "GBPUSD"
                ],
                "eventTypes": [
                    {
                    "type": "Quote",
                    "format": "COMPACT",
                    "candleType":"h",
                    "fromTime":"",
                    "toTime":"",
                    "count":1
                    }
                ],
                "account": "default:1210008442"
                }

        status_code, response = self.rest_service.post_request(url="marketdata", payload=payload, headers=self.access_token_header)
        print(status_code, response)
    
    def new_order(self):
        payload = {
            "account": "default:1210008442",
            "orderCode": str(uuid.uuid4()),
            "type": "MARKET",
            "instrument": "EURGBP",
            "quantity": 2000,
            "side": "BUY",
            "positionEffect":"OPEN",
            "tif": "GTC"
            }

        status_code, response = self.rest_service.post_request(url=f"accounts/default:1210008442/orders", payload=payload, headers=self.access_token_header)
        print(status_code, response)

    def get_positions(self):
        response = self.rest_service.get_request(url=f"accounts/default:1210008442/positions", headers=self.access_token_header)
        print(pd.DataFrame(response["positions"]))

    def get_active_orders(self):
        response = self.rest_service.get_request(url=f"accounts/default:1210008442/orders", headers=self.access_token_header)
        print(pd.DataFrame(response["orders"]))

    def get_account(self):
        response = self.rest_service.get_request(url=f"accounts/default:1210008442/portfolio", headers=self.access_token_header)
        print(response)
    
    def get_dollar_value(self, from_currency, to_currency):
        response = self.rest_service.get_request(url=f"conversionRates?fromCurrency={from_currency}&toCurrency={to_currency}", headers=self.access_token_header)
        print(response)
    
    def cancel_single_order(self, order_code):
        response = self.rest_service.get_request(url=f"accounts/default:1210008442/orders/{order_code}", headers=self.access_token_header)
        print(response)


if __name__ == "__main__":
    obj = DXTrade()
    obj.login()
    print(obj.access_token)
    obj.ping()
    # obj.new_order()
    # obj.get_positions()
    # obj.get_active_orders()
    # obj.get_account()
    # obj.get_dollar_value("GBP", "USD")
    obj.get_exchange_price("GBPUSD")
    
    # obj.get_candles("GBPUSD", 60)
    
    


"""
PYTHONPATH="/Users/dhanu/Library/CloudStorage/OneDrive-Personal/Financial Freedom/Phoenix:$PYTHONPATH"
export PYTHONPATH

"""