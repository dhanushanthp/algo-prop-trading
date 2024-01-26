import modules.currency_pairs as curr
import socket

if curr.company == "FTMO S.R.O.":
    account_risk_percentage = 1.0 # Value in %
elif curr.company == "AXSE Brokerage Ltd.":
    account_risk_percentage = 0.20 # Value in %
elif curr.company == "Black Bull Group Limited":
    account_risk_percentage = 0.20 # Value in %
else:
    account_risk_percentage = 1.0 # Value in %

position_split_of_account_risk = 2 # Number of positions can risk as per total account risk
server_timezone=2

local_ip = socket.gethostbyname(socket.gethostname()).replace(".", "_")