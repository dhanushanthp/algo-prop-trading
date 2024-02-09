import modules.currency_pairs as curr
import socket

account_risk_percentage = 1.0 # Value in %
risk_of_a_position=0.2

position_split_of_account_risk = 10 # Number of positions can risk as per total account risk
server_timezone=2

buffer_ratio=0.25

local_ip = socket.gethostbyname(socket.gethostname()).replace(".", "_")