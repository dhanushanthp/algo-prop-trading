import requests
import threading
server_url = 'http://192.168.20.15:5000'
headers = {'Content-Type': 'application/json'}

def trigger_order_entry(symbol, direction):    
    
    data = {"symbol": symbol, "direction":direction}
    requests.post(server_url, json=data, headers=headers)

def get_active_positions():
    response = requests.get(f"{server_url}/active_orders", headers=headers)
    return list(response.json())

def async_trigger_order_entry(symbol, direction):
    thread = threading.Thread(target=trigger_order_entry, args=(symbol, direction))
    thread.start()

if __name__ == '__main__':
    # async_trigger_order_entry("AUDUSD", "L")
    # async_trigger_order_entry("AUDUSD", "S")
    print(get_active_positions())