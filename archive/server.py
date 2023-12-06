from flask import Flask, request,jsonify
import time
import trade_candles_server as tc
import mng_pos as mp
import MetaTrader5 as mt
import logging
mt.initialize()
import currency_pairs

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

app = Flask(__name__)
tc_ref = tc.AlgoTrader()
tc_ref.trading_timeframe = 15
tc_ref.stop_ratio = 1
tc_ref.target_ratio = 1

@app.route('/', methods=['POST'])
def index():
    data = request.get_json()
    if data:
        symbol = data["symbol"]
        direction = data["direction"]
        comment = data["comment"]
        
        for _ in range(3):
            mp.cancel_specific_pending_order(symbol=symbol)
            existing_positions = list(set([i.symbol for i in mt.positions_get()]))
            active_orders = list(set([i.symbol for i in mt.orders_get()]))
            combined_symbols = list(set(existing_positions + active_orders))
            
            if symbol not in combined_symbols:
                if direction == "L":
                    logger.info(f"long entry request: {symbol}")
                    tc_ref.long_real_entry(symbol=symbol, comment=comment)
                elif direction == "S":
                    logger.info(f"short entry request: {symbol}")
                    tc_ref.short_real_entry(symbol=symbol, comment=comment)
                
                time.sleep(1*60)
            else:
                break
        
        # Cancel the order after 3 tries. It still exist in active order
        mp.cancel_specific_pending_order(symbol=symbol)
            
    return "Success", 200

@app.route('/active_orders', methods=['GET'])
def get_active_orders():
    logger.info("request active orders")
    existing_positions = list(set([i.symbol for i in mt.positions_get()]))
    return jsonify(existing_positions)

@app.route('/active_positions', methods=['GET'])
def get_all_orders():
    logger.info("request all( position + active) orders")
    existing_positions = list(set([i.symbol for i in mt.positions_get()]))
    active_orders = list(set([i.symbol for i in mt.orders_get()]))
    all_symbols = list(set(existing_positions + active_orders))
    return jsonify(all_symbols)

@app.route('/close_all_positions', methods=['GET'])
def close_all_positions():
    logger.info("close all positions")
    mp.close_all_positions()
    return "Success", 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)