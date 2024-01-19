from flask import Flask, jsonify
import MetaTrader5 as mt5
import json
import logging
app = Flask(__name__)

# Disable Flask logs
app.logger.disabled = True
log = logging.getLogger('werkzeug')
log.disabled = True

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

@app.route('/get_positions', methods=['GET'])
def get_data():
    existing_positions = mt5.positions_get()
    data_dict = {}
    for position in existing_positions:
        data_dict[position.symbol] = (position.type, position.time)

    return jsonify(data_dict)

if __name__ == '__main__':
    # curl http://10.1.0.6:8080/get_positions
    app.run(host="0.0.0.0", port="8080")
