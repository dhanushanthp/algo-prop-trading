from flask import Flask, request,jsonify
import time
import trade_candles as tc
import mng_pos as mp
import MetaTrader5 as mt

app = Flask(__name__)
tc_ref = tc.AlgoTrader()

@app.route('/', methods=['POST'])
def index():
    data = request.get_json()
    if data:
        symbol = data["symbol"]
        direction = data["direction"]
        
        while True:
            mp.cancel_specific_pending_order(symbol=symbol)
            existing_positions = list(set([i.symbol for i in mt.positions_get()]))
            active_orders = list(set([i.symbol for i in mt.orders_get()]))
            combined_symbols = list(set(existing_positions + active_orders))
            if symbol not in combined_symbols:
                if direction == "L":
                    tc_ref.long_real_entry(symbol=symbol)
                elif direction == "S":
                    tc_ref.short_real_entry(symbol=symbol)
                
                time.sleep(2*60)
            else:
                break
            
    return "Success", 200

@app.route('/active_orders', methods=['GET'])
def get_active_orders():
    existing_positions = list(set([i.symbol for i in mt.positions_get()]))
    return jsonify(existing_positions)

if __name__ == '__main__':
    app.run(debug=True, port=5000)