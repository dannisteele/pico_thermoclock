import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sqlalchemy import create_engine

# Create the database connection
db_connection = create_engine('mysql+mysqlconnector://root:admin@localhost/House')

# Query the data from the views
daily_avg_temp_and_humidity = pd.read_sql('SELECT * FROM daily_avg', con=db_connection)
daily_min_and_max_temp_and_humidity = pd.read_sql('SELECT * FROM daily_min_max', con=db_connection)

# Plot daily average temperature
plt.figure(figsize=(18,10))
plt.plot(daily_avg_temp_and_humidity['Date'], daily_avg_temp_and_humidity['AvgTemperature'], color='tab:red', label='Avg Temperature')

plt.xlabel('Date')
plt.xticks(rotation=45)
plt.ylabel('Avg Temperature (°C)')
plt.title('Daily Average Temperature')
plt.legend()
plt.grid(True)
plt.show()

# Plot daily average humidity
plt.figure(figsize=(18,10))
plt.plot(daily_avg_temp_and_humidity['Date'], daily_avg_temp_and_humidity['AvgHumidity'], color='tab:blue', label='Avg Humidity')

plt.xlabel('Date')
plt.xticks(rotation=45)
plt.ylabel('Avg Humidity (%)')
plt.title('Daily Average Humidity')
plt.legend()
plt.grid(True)
plt.show()

# Plot min and max temperature
plt.figure(figsize=(18,10))
plt.plot(daily_min_and_max_temp_and_humidity['Date'], daily_min_and_max_temp_and_humidity['MinTemperature'], color='tab:blue', label='Min Temperature')
plt.plot(daily_min_and_max_temp_and_humidity['Date'], daily_min_and_max_temp_and_humidity['MaxTemperature'], color='tab:red', label='Max Temperature')

plt.xlabel('Date')
plt.xticks(rotation=45)
plt.ylabel('Temperature (°C)')
plt.title('Daily Min and Max Temperature')
plt.legend()
plt.grid(True)
plt.show()
