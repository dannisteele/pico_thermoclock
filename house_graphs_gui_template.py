from tkinter import BOTH, NORMAL, TOP, LEFT, DISABLED, X, BOTTOM, ttk, messagebox, filedialog, Tk
from pandas import read_sql, to_datetime, read_csv
from matplotlib.pyplot import subplots, Normalize
from matplotlib.dates import date2num, MonthLocator, DateFormatter
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sqlalchemy import create_engine
from datetime import datetime
from numpy import array, concatenate, amin, amax, reshape
from sys import exit
from os import path

import configparser
import os

def get_config_path():
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        return os.path.join(sys._MEIPASS, "config.ini")
    else:
        # Running as a normal script
        return "config.ini"

CONFIG_FILE = get_config_path()

def get_database_credentials():
    config = configparser.ConfigParser()

    # Check if config file exists
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        return (
            config["DATABASE"]["mysql_username"],
            config["DATABASE"]["mysql_password"],
            config["DATABASE"]["mysql_server"],
            config["DATABASE"]["database_name"],
        )

    # Ask user for credentials if not stored
    from tkinter.simpledialog import askstring
    from tkinter import Tk
    
    root = Tk()
    root.withdraw()  # Hide the root window

    mysql_username = askstring("Database Setup", "Enter MySQL Username:", initialvalue="root")
    mysql_password = askstring("Database Setup", "Enter MySQL Password:", initialvalue="admin")
    mysql_server = askstring("Database Setup", "Enter MySQL Server:", initialvalue="localhost")
    database_name = askstring("Database Setup", "Enter Database Name:", initialvalue="Something")

    # Save credentials to config file
    config["DATABASE"] = {
        "mysql_username": mysql_username,
        "mysql_password": mysql_password,
        "mysql_server": mysql_server,
        "database_name": database_name,
    }

    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)

    return mysql_username, mysql_password, mysql_server, database_name

# Function to fetch data and plot
def plot_data(year, root, frame, save_button):
    try:
        # Expand window to full screen
        root.state('zoomed')
        
        # Get stored credentials
        mysql_username, mysql_password, mysql_server, database_name = get_database_credentials()

        # Database connection
        db_connection = create_engine(f'mysql+mysqlconnector://{mysql_username}:{mysql_password}@{mysql_server}/{database_name}')

        # Query data
        daily_avg = read_sql('SELECT * FROM daily_avg', con=db_connection)
        daily_min_max = read_sql('SELECT * FROM daily_min_max', con=db_connection)

        # Ensure required columns exist
        required_columns_avg = {'Date', 'AvgTemperature', 'AvgHumidity'}
        required_columns_min_max = {'Date', 'MinTemperature', 'MaxTemperature'}
        if not required_columns_avg.issubset(daily_avg.columns) or not required_columns_min_max.issubset(daily_min_max.columns):
            raise KeyError("Required columns are missing in the database query results.")

        # Convert 'Date' to datetime
        daily_avg['Date'] = to_datetime(daily_avg['Date'])
        daily_min_max['Date'] = to_datetime(daily_min_max['Date'])

        # Filter data by year
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)

        avg_filtered = daily_avg[(daily_avg['Date'] >= start_date) & (daily_avg['Date'] <= end_date)]
        min_max_filtered = daily_min_max[(daily_min_max['Date'] >= start_date) & (daily_min_max['Date'] <= end_date)]

        if avg_filtered.empty or min_max_filtered.empty:
            raise ValueError(f"No data available for the year {year}.")

        # Plot data
        fig, axs = subplots(3, 1, figsize=(10, 10))
        fig.suptitle(f"House Data for {year}", fontsize=16)

        # Plot daily average temperature with gradient
        dates = date2num(avg_filtered['Date'])
        temperatures = avg_filtered['AvgTemperature'].values
        norm_temp = Normalize(temperatures.min(), temperatures.max())
        points_temp = array([dates, temperatures]).T.reshape(-1, 1, 2)
        segments_temp = concatenate([points_temp[:-1], points_temp[1:]], axis=1)
        cmap_temp = LinearSegmentedColormap.from_list("temp_gradient", ["blue", "lightgreen", "red"])
        lc_temp = LineCollection(segments_temp, cmap=cmap_temp, norm=norm_temp)
        lc_temp.set_array(temperatures)
        lc_temp.set_linewidth(2)
        axs[0].add_collection(lc_temp)
        axs[0].set_xlim(datetime(year, 1, 1), datetime(year, 12, 31))
        axs[0].set_ylim(temperatures.min() - 2, temperatures.max() + 2)
        axs[0].set_title(f"Daily Average Temperature for {year}")
        axs[0].xaxis.set_major_locator(MonthLocator())
        axs[0].xaxis.set_major_formatter(DateFormatter('%b'))
        axs[0].grid(True)

        # Plot daily average humidity with gradient
        humidities = avg_filtered['AvgHumidity'].values
        norm_hum = Normalize(humidities.min(), humidities.max())
        points_hum = array([dates, humidities]).T.reshape(-1, 1, 2)
        segments_hum = concatenate([points_hum[:-1], points_hum[1:]], axis=1)
        cmap_hum = LinearSegmentedColormap.from_list("hum_gradient", ["cyan", "blue"])
        lc_hum = LineCollection(segments_hum, cmap=cmap_hum, norm=norm_hum)
        lc_hum.set_array(humidities)
        lc_hum.set_linewidth(2)
        axs[1].add_collection(lc_hum)
        axs[1].set_xlim(datetime(year, 1, 1), datetime(year, 12, 31))
        axs[1].set_ylim(humidities.min() - 5, humidities.max() + 5)
        axs[1].set_title(f"Daily Average Humidity for {year}")
        axs[1].xaxis.set_major_locator(MonthLocator())
        axs[1].xaxis.set_major_formatter(DateFormatter('%b'))
        axs[1].grid(True)

        # Plot min and max temperatures
        axs[2].plot(min_max_filtered['Date'], min_max_filtered['MinTemperature'], label='Min Temp', color='blue')
        axs[2].plot(min_max_filtered['Date'], min_max_filtered['MaxTemperature'], label='Max Temp', color='red')
        axs[2].set_xlim(datetime(year, 1, 1), datetime(year, 12, 31))
        axs[2].set_title(f"Daily Min and Max Temperatures for {year}")
        axs[2].xaxis.set_major_locator(MonthLocator())
        axs[2].xaxis.set_major_formatter(DateFormatter('%b'))
        axs[2].grid(True)
        axs[2].legend()

        # Add spacing between subplots
        fig.tight_layout(pad=1.0)

        # Clear previous plots and display the new one
        for widget in frame.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=BOTH, expand=True)
        canvas.draw()

        # Enable the save button
        def save_as():
            default_filename = f"House_Data_for_{year}.png" 
            file_path = filedialog.asksaveasfilename(defaultextension=".png", 
                                                     filetypes=[("PNG files", "*.png"), ("All files", "*.*")], 
                                                     initialfile=default_filename)
            if file_path:
                fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Save Successful", f"Graph saved as {file_path}")

        save_button.config(command=save_as, state=NORMAL)

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        
def import_data(root):
    try:
        # Open file dialog to select CSV
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return

        if not path.exists(file_path):
            raise FileNotFoundError(f"The file '{file_path}' does not exist.")

        mysql_username, mysql_password, mysql_server, database_name = get_database_credentials()
        db_connection = create_engine(f'mysql+mysqlconnector://{mysql_username}:{mysql_password}@{mysql_server}/{database_name}')

        data = read_csv(file_path)

        # Rename columns if necessary to match the table schema
        data.rename(columns={
            'Date': 'Date',
            'Time': 'Time',
            'Temperature': 'Temp', 
            'Humidity': 'Humidity'
        }, inplace=True)

        # Insert data into the table using pandas
        try:
            data.to_sql(database_name, con=db_connection, if_exists='append', index=False, method='multi')
            messagebox.showinfo("Success", f"Data from {file_path} imported successfully into '{database_name}'!")
        except Exception as pandas_error:
            messagebox.showerror("Error", f"Failed to import data into '{database_name}': {pandas_error}")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")



# GUI setup
def main():
    root = Tk()
    root.title("Temperature and Humidity Data Viewer")
    root.geometry("550x70")  # Initial small size
    
    # Bring window to the front
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))
    root.focus_force()
    
    # Get stored credentials
    mysql_username, mysql_password, mysql_server, database_name = get_database_credentials()
    
    # Ensure the process exits when the window is closed
    root.protocol("WM_DELETE_WINDOW", lambda: (root.destroy(), exit()))

    # Input section
    input_frame = ttk.Frame(root, padding="10")
    input_frame.pack(side=TOP, fill=X)

    ttk.Label(input_frame, text="Enter Year:").pack(side=LEFT, padx=(0, 5))
    year_entry = ttk.Entry(input_frame, width=10)
    year_entry.pack(side=LEFT)

    def handle_enter(event):
        on_plot_button_click(year_entry, root, plot_frame, save_button)

    year_entry.bind("<Return>", handle_enter)

    plot_button = ttk.Button(input_frame, text="Plot Data", command=lambda: on_plot_button_click(year_entry, root, plot_frame, save_button))
    plot_button.pack(side=LEFT, padx=(5, 0))

    save_button = ttk.Button(input_frame, text="Save as PNG", state=DISABLED)
    save_button.pack(side=LEFT, padx=(5, 0))
    
    import_button = ttk.Button(input_frame, text="Import CSV", command=lambda: import_data(root))
    import_button.pack(side=LEFT, padx=(5, 0))

    style = ttk.Style()
    style.configure("TButton", foreground="black", background="lightgray")  # Ensure text and background contrast

    # Plot section
    plot_frame = ttk.Frame(root, padding="10")
    plot_frame.pack(side=BOTTOM, fill=BOTH, expand=True)

    year_entry.focus_set()  # Set focus to the year entry on startup

    root.mainloop()

def on_plot_button_click(year_entry, root, plot_frame, save_button):
    try:
        year = int(year_entry.get())
        if year < 1900 or year > datetime.now().year:
            raise ValueError("Please enter a valid year.")
        plot_data(year, root, plot_frame, save_button)
    except ValueError as ve:
        messagebox.showwarning("Invalid Input", str(ve))

if __name__ == "__main__":
    main()
