import objects.Currencies as curr
import socket

account_risk_percentage = 1.0 # Value in %
num_positions_at_risk = 5 # Number of positions can risk as per total account risk

buffer_ratio=0.0

server_timezone=2
local_ip = socket.gethostbyname(socket.gethostname()).replace(".", "_")
risk_of_a_position=account_risk_percentage/num_positions_at_risk