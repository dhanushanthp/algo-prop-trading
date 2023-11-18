import requests
import threading

def trigger_order_entry(symbol, direction):
    server_url = 'http://0.0.0.0:5000/'
    headers = {'Content-Type': 'application/json'}
    data = {"symbol": symbol, "direction":direction}
    requests.post(server_url, json=data, headers=headers)
    
def async_trigger_order_entry(symbol, direction):
    thread = threading.Thread(target=trigger_order_entry, args=(symbol, direction))
    thread.start()

if __name__ == '__main__':
    async_trigger_order_entry("AUDUSD", "L")
    async_trigger_order_entry("AUDUSD", "S")