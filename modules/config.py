import modules.currency_pairs as curr

if curr.company == "FTMO S.R.O.":
    account_risk_percentage = 0.25 # Value in %
elif curr.company == "AXSE Brokerage Ltd.":
    account_risk_percentage = 0.25 # Value in %
elif curr.company == "Black Bull Group Limited":
    account_risk_percentage = 0.25 # Value in %
else:
    account_risk_percentage = 1.0 # Value in %

position_split_of_account_risk = 4 # Number of positions can risk as per total account risk
server_timezone=2