import pandas as pd

data = pd.read_csv("FTMO_10K_DEMO.csv", names=["time", "equity"])

initial_equity = data.iloc[0]["equity"]

data["change"] = data["equity"] - initial_equity

import plotly.graph_objects as go
from datetime import datetime

# Sample data
dates = data["time"]
values = data["change"]

# Create a trace
trace = go.Scatter(x=dates, y=values, mode='lines+markers', name='Line Chart')

# Create layout
layout = go.Layout(title='Date vs. Integer Value Line Chart', xaxis=dict(title='Date'), yaxis=dict(title='Integer Value'))

# Create figure
fig = go.Figure(data=[trace], layout=layout)

# Show the figure
fig.show()