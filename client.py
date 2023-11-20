import requests
import threading
server_url = 'http://192.168.20.15:5000'
headers = {'Content-Type': 'application/json'}

def trigger_order_entry(symbol, direction, distance):    
    data = {"symbol": symbol, "direction":direction, "distance":distance}
    requests.post(server_url, json=data, headers=headers)

def get_active_positions():
    response = requests.get(f"{server_url}/active_orders", headers=headers)
    return list(response.json())

def get_all_positions():
    response = requests.get(f"{server_url}/active_positions", headers=headers)
    return list(response.json())

def async_trigger_order_entry(symbol, direction, distance):
    thread = threading.Thread(target=trigger_order_entry, args=(symbol, direction, distance))
    thread.start()

def close_all_positions():
    requests.get(f"{server_url}/close_all_positions", headers=headers)

if __name__ == '__main__':
    async_trigger_order_entry("JP225.cash", "L")
    # async_trigger_order_entry("AUDUSD", "S")
    print(get_active_positions())
    print(get_all_positions())
    # close_all_positions()