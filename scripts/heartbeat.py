import psutil
from objects.slack_msg import Slack
alert = Slack()
import archived.indicators as ind

def is_process_running(process_name):
    for process in psutil.process_iter(['pid', 'name', "cmdline"]):
        if process.info['cmdline'] is not None and len(process.info['cmdline']) > 1:
            if process.info['cmdline'][1] == process_name:
                return True
    return False

if __name__ == "__main__":
    process_name = "trade_candles_r_s_combined.py"

    if is_process_running(process_name):
        # account_name = ind.get_account_name()
        # alert.send_msg(f"{account_name}: App is running fine!")
        pass
    else:
        account_name = ind.get_account_name()
        alert.send_msg(f"{account_name}: App is not running!")