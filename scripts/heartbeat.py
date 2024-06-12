import psutil
from modules.common.slack_msg import Slack
alert = Slack()
from modules.meta import util
import subprocess
import os

def is_process_running(process_name):
    for process in psutil.process_iter(['pid', 'name', "cmdline"]):
        if process.info['cmdline'] is not None and len(process.info['cmdline']) > 1:
            if process.info['cmdline'][1] == process_name:
                return True
    return False

if __name__ == "__main__":
    process_name = "smart_trader.py"

    if is_process_running(process_name):
        # account_name = ind.get_account_name()
        # alert.send_msg(f"{account_name}: App is running fine!")
        pass
    else:
        account_name = util.get_account_name()
        alert.send_msg(f"{account_name}: App is not running!")
        username = os.getenv('USERNAME')
        batch_file_path = f"C:\\Users\\{username}\\OneDrive\\Financial Freedom\\Phoenix\\FRX_15M_4CDL_BREAK.bat"
        subprocess.run(['start', 'cmd', '/k', batch_file_path], shell=True)