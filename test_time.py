from datetime import datetime, timedelta
import pytz

# Define the desired timezone (GMT+3)
gmt3 = pytz.timezone('Etc/GMT-2') 

# Create a datetime object for a specific date and time in GMT+3
gmt3_time = datetime.now(gmt3) + timedelta(minutes=2)

# Print the datetime object
print(gmt3_time)