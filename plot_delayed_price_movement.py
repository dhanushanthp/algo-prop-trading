import matplotlib.pyplot as plt
import pandas as pd
from blessed import Terminal
import time
from modules.meta.Account import Account
from modules.meta import util

account = Account()

# Initialize terminal
term = Terminal()

# Function to update the plot
def update_plot(x, y, line, ax):
    line.set_xdata(x)
    line.set_ydata(y)
    ax.relim()
    ax.autoscale_view()
    plt.draw()
    plt.pause(0.01)

# Initialize plot
plt.ion()
fig, ax = plt.subplots()
line, = ax.plot([], [])
ax.axhline(y=0, color='black', linestyle='--')  # Add horizontal line at y=0

with term.cbreak(), term.hidden_cursor():
    current_date = util.get_current_time().strftime('%Y-%m-%d')
    file_path = f"PnLData/price_tracker/{account.get_account_id()}_{current_date}_hist.csv"
    
    while True:
        df = pd.read_csv(file_path, parse_dates=['Timestamp'])

        if 'Timestamp' not in df.columns or 'RR' not in df.columns:
            raise ValueError("CSV file must contain 'timestamp' and 'value' columns")

        x = df['Timestamp']
        y = df['RR']

        update_plot(x, y, line, ax)

        time.sleep(1)  # Adjust the sleep time as needed

        # Quiting
        if term.inkey(timeout=0.01) == 'q':
            break
