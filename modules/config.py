import modules.currency_pairs as curr
import socket

if curr.company == "FTMO S.R.O.":
    account_risk_percentage = 1.0 # Value in %
elif curr.company == "AXSE Brokerage Ltd.":
    account_risk_percentage = 1.0 # Value in %
elif curr.company == "Black Bull Group Limited":
    account_risk_percentage = 1.0 # Value in %
else:
    account_risk_percentage = 1.0 # Value in %

position_split_of_account_risk = 10 # Number of positions can risk as per total account risk
server_timezone=2

buffer_ratio=0.25

local_ip = socket.gethostbyname(socket.gethostname()).replace(".", "_")