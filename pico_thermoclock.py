# General imports
from machine import Pin, ADC, I2C, UART
import time
import uos
import random
from dht20 import DHT20
from neopixel import NeoPixel
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd
from pico_thermoclock_constants import *
import socket
import select 

# Network imports
import network
import socket
import struct

# Configuration
i2c1_sda = Pin(I2C_SDA_PIN)
i2c1_scl = Pin(I2C_SCL_PIN)
i2c1 = I2C(I2C_INTERFACE, sda=i2c1_sda, scl=i2c1_scl)
potentiometer = ADC(Pin(POTENTIOMETER_PIN))
led = Pin(LED_PIN, Pin.OUT)
dht20 = DHT20(DHT20_ADDRESS, i2c1)
lcdi2c = I2C(LCD_INTERFACE, sda=machine.Pin(I2C_SDA_PIN), scl=machine.Pin(I2C_SCL_PIN), freq=400000)
lcd = I2cLcd(lcdi2c, LCD_ADDRESS, LCD_ROWS, LCD_COLUMNS)
ring = NeoPixel(Pin(NEOPIXEL_PIN), NEOPIXEL_LCD_TOTAL)
uart = UART(0, baudrate=115200)
uart.init(115200, bits=8, parity=None, stop=1, tx=Pin(0), rx=Pin(1))
uos.dupterm(uart)

# What is the ideal temperature for you in 
IDEAL_TEMP = 20

# Create a temperature/LED dictionary for our scale
# Temperature is the key (left), LED index is the value (right)
LEDdict = {
  IDEAL_TEMP - 5: 0,
  IDEAL_TEMP - 4.5: 1,
  IDEAL_TEMP - 4: 2,
  IDEAL_TEMP - 3.5: 3,
  IDEAL_TEMP - 3: 4,
  IDEAL_TEMP - 2.5: 5,
  IDEAL_TEMP - 2: 6,
  IDEAL_TEMP - 1.5: 7,
  IDEAL_TEMP - 1: 8,
  IDEAL_TEMP - 0.5: 9,
  IDEAL_TEMP: 10, # Top-middle LED
  IDEAL_TEMP + 0.5: 11,
  IDEAL_TEMP + 1: 12,
  IDEAL_TEMP + 1.5: 13,
  IDEAL_TEMP + 2: 14,
  IDEAL_TEMP + 2.5: 15,
  IDEAL_TEMP + 3: 16,
  IDEAL_TEMP + 3.5: 17,
  IDEAL_TEMP + 4: 18,
  IDEAL_TEMP + 4.5: 19,
  IDEAL_TEMP + 5: 20
}

# Possible colours, from blue, to green, to red
LEDcolours = [
    (0,0,10),
    (0,1,9),
    (0,2,8),
    (0,3,7),
    (0,4,6),
    (0,5,5),
    (0,6,4),
    (0,7,3),
    (0,8,2),
    (0,9,1),
    (0,10,0), # Top-middle LED
    (1,9,0),
    (2,8,0),
    (3,7,0),
    (4,6,0),
    (5,5,0),
    (6,4,0),
    (7,3,0),
    (8,2,0),
    (9,1,0),
    (10,0,0)
]
    
# Grab data from the sensor dictionary
measurements = dht20.measurements
    
# Create temp and humidity variables
# From initial readings
lowtemp = round(measurements['t'],1)
hightemp = round(measurements['t'],1)

# For the current display
display = ""
firstLine = ""
lastLine = ""

def file_setup():
    global firstLine, lastLine
    # Create a header if there is not one already
    try:
        file = open("data.csv","r")
    except OSError:
        file = open("data.csv","a+")
        file.write("Date,Time,Temperature,Humidity\n")
    
    firstLine = file.readline()
    print("firstLine = " + firstLine)

    file.close()

    # Check if the file does not exist, or if the first line is something that we do not expect
    if (uos.stat('data.csv')[6] == 0 or firstLine != "Date,Time,Temperature,Humidity\n"):
        file = open("data.csv","w")
        file.write("Date,Time,Temperature,Humidity\n")
        file.close()

    # Get the date and time from the last line in the file.
    file = open("data.csv","a+")
    lastLine = file.readlines()[-1][:19]
    file.close()


# Connect to the internet
def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    i = 6
    while wlan.isconnected() == False:
        lcd.move_to(3, 0) 
        lcd.putstr("Connecting")
        lcd.move_to(i, 1) 
        lcd.putstr(".")
        i = i + 1
        time.sleep(1)
    lcd.clear()
    ip = wlan.ifconfig()[0]
    lcd.move_to(3, 0) 
    lcd.putstr("Connected!")
    lcd.move_to(1, 1) 
    lcd.putstr(ip)
    print(f'Connected on {ip}')
    time.sleep(3)
    lcd.clear()
    return ip
    
def start_web_server(connection):
    # Accept connections if available
    ready_to_read, _, _ = select.select([connection], [], [], 0)  # Non-blocking select
    if connection in ready_to_read:
        client, addr = connection.accept()
        print(f"Connection from {addr}")

        # Handle HTTP requests
        try:
            request = client.recv(1024).decode('utf-8')
            if 'GET /data.csv' in request:
                # Serve the CSV file
                response_headers = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/csv\r\n"
                    "Connection: close\r\n\r\n"
                )
                client.sendall(response_headers.encode())
                with open('data.csv', 'r') as f:
                    client.sendall(f.read().encode())
            elif 'GET /delete' in request:
                # Handle delete request
                try:
                    # Check if the file exists
                    if uos.stat('data.csv'):
                        uos.remove('data.csv')  # Delete the file
                        file_setup()  # Recreate it
                        response = (
                            "HTTP/1.1 200 OK\r\n"
                            "Content-Type: text/plain\r\n"
                            "Connection: close\r\n\r\n"
                            "File deleted and new file created."
                        )
                    else:
                        # File does not exist
                        response = (
                            "HTTP/1.1 404 Not Found\r\n"
                            "Content-Type: text/plain\r\n"
                            "Connection: close\r\n\r\n"
                            "File not found."
                        )
                except Exception as e:
                    # Handle any unexpected errors
                    response = (
                        "HTTP/1.1 500 Internal Server Error\r\n"
                        "Content-Type: text/plain\r\n"
                        "Connection: close\r\n\r\n"
                        f"An error occurred: {e}"
                    )
                finally:
                    client.sendall(response.encode())
            else:
                # Serve a basic webpage with links
                html = """
                <html>
                <body>
                    <h1>Raspberry Pi Temperature Data</h1>
                    <a href="/data.csv" download>Download Data.csv</a><br><br>
                    <a href="/delete" onclick="return confirmDelete()">Delete Data.csv</a>
                </body>
                </html>

                <script>
                    function confirmDelete() {
                        return confirm("Are you sure you want to delete Data.csv?");
                    }
                </script>
                """
                response_headers = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html\r\n"
                    "Connection: close\r\n\r\n"
                )
                client.sendall(response_headers.encode() + html.encode())
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client.close()

# Main setup for the web server
def setup_web_server():
    address = ('0.0.0.0', 80)  # Bind to all available interfaces on port 80
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    print("Web server running...")
    return connection

# Ensures that time.localtime() is correct
def set_time():
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo(HOST, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
    finally:
        s.close()
    val = struct.unpack("!I", msg[40:44])[0]
    t = val - NTP_DELTA    
    tm = time.gmtime(t)

    # Adjust for DST based on UK rules
    current_time = time.localtime(t)
    last_sunday_march = max(25, (31 - (current_time[6] - 6) % 7))
    last_sunday_october = max(25, (31 - (current_time[6] - 6) % 7))
    dst_starts = time.mktime((current_time[0], 3, last_sunday_march, 1, 0, 0, 0, 0, -1))
    dst_ends = time.mktime((current_time[0], 10, last_sunday_october, 2, 0, 0, 0, 0, -1))

    if t >= dst_starts and t < dst_ends:
        t += 3600  # Add 1 hour for DST
        machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3] + 1, tm[4], tm[5], 0))
        return

    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))

def light_controller():
    if (potentiometer.read_u16() < 32000):
        lcd.backlight_off()
    else:
        lcd.backlight_on()
        
def display_date():
    led.on()
    set_time()
    lcd.move_to(6, 0) 
    lcd.putstr("Date")
    lcd.move_to(4, 1)
    lcd.putstr(str(time.localtime()[2]) + "-" + str(time.localtime()[1]) + "-" + str(time.localtime()[0]))
    time.sleep(2)
    lcd.clear()
    led.off()
    
def write_data():
    global lastLine
    file=open("data.csv","a+")
    if (lastLine is not None and lastLine != "" and lastLine != "{}-{}-{}".format(yearstring, monthstring, daystring)
                  + "," + "{}:{}:{}".format(hourstring, minutestring, secondstring)):
        file.write("{}-{}-{}".format(yearstring, monthstring, daystring)
                  + "," + "{}:{}:{}".format(hourstring, minutestring, secondstring) + ","
                  + str(round(measurements['t'],2)) + "," + str(humidity) + "\n")
        file.flush()
        lastLine = "{}-{}-{}".format(yearstring, monthstring, daystring) + "," + "{}:{}:{}".format(hourstring, minutestring, secondstring)
        print("")
        print("-------------------")
        print("Information written")
        print("-------------------")
        print("")
    file.close()

# Initial setup for main code
file_setup()
ip = connect()
display_date()
connection = setup_web_server()

# For future additions
# connection = open_socket(ip)
print("firstLine = " + firstLine)
print("lastLine = " + lastLine)

# The code
while True:
    light_controller()
    start_web_server(connection)
    
    # Create a rounded variable for the temperature and humidity
    temperature = round(measurements['t'] * 2) / 2
    humidity = round(measurements['rh'], 1)
    
    if temperature < IDEAL_TEMP - 5:
        temperature = IDEAL_TEMP - 5
        print("*** Temperature very low ***")
    
    elif temperature > IDEAL_TEMP + 5:
        temperature = IDEAL_TEMP + 5
        print("*** Temperature very high ***")
    
    LEDindex = (LEDdict[temperature])

    hour = time.localtime()[3]
    minute = time.localtime()[4]
    second = time.localtime()[5]
    
    yearstring = str("{:04d}".format(time.localtime()[0]))
    monthstring = str("{:02d}".format(time.localtime()[1]))
    daystring = str("{:02d}".format(time.localtime()[2]))
    hourstring = str("{:02d}".format(hour))
    minutestring = str("{:02d}".format(minute))
    secondstring = str("{:02d}".format(second))
    
    if (0 <= second < 10 or 20 <= second < 30 or 40 <= second < 50):
        # Grab data from the sensor dictionary
        measurements = dht20.measurements
        
        # Create variable for current temp
        tempnow = round(measurements['t'],1)

        # Write initial low temp value to LCD
        if ((second == 0 or second == 20 or second == 40) and display != "temp"):
            display = "temp"
            lcd.clear()
            lcd.putstr("Current:")
            lcd.move_to(0, 1) # Move to second row
            lcd.putstr("L:       H:")
            lcd.move_to(3, 1)
            lcd.putstr(str(lowtemp))

            # Write initial high temp value to LCD
            lcd.move_to(12, 1) # 12th column, 2nd row
            lcd.putstr(str(hightemp))
        
            # Update current temp on display
            lcd.move_to(12, 0)
            lcd.putstr(str(tempnow))
    
        # If the lowest temp is HIGHER than current temp
        if tempnow < lowtemp:
            
             # Update the lowest recorded temp
            lowtemp = tempnow
        
        # If the highest temp is LOWER than current temp
        if tempnow > hightemp:
            
            # Update the highest recorded temp
            hightemp = tempnow
    
    else:
        if (second == 10 or second == 30 or second == 50):
            lcd.clear()
        display = "time"
        lcd.move_to(6, 0) 
        lcd.putstr("Time")
        lcd.move_to(4, 1)
        lcd.putstr(hourstring + ":" + minutestring + ":" + secondstring)
    
    # Print the temperature and index for debugging
    # print(f"Current time: {hourstring}:{minutestring}:{secondstring}")
    # print("Temperature:",round(measurements['t'],2))
    # print("Rounded temp:", temperature)
    # print(f"Humidity:    {humidity}%")
    # print("----------------")
            
    # Clear the ring
    ring.fill((0,0,0))
    ring.write()
    
    # Write the info to data.csv every half hour
    if (minute % 30 == 0 and second == 0):
        write_data()
    
    # Manage the logic for on the hour every hour
    if (minute == 0 and second == 0):
        
        # If it is midnight, reset the low and high temps
        if (hour == 0):
            lcd.putstr("Current:")
            lcd.move_to(0, 1)
            lcd.putstr("L:       H:")
            lowtemp = round(measurements['t'],1)
            hightemp = round(measurements['t'],1)
            
        # If it is midnight or midday, set the LED to spin
        if (hour % 12 == 0):
            for i in range(12):
                for i in range(12):
                    ring.fill((0,0,0))
                    ring.write()
                    ring[i] = LEDcolours[LEDindex]
                    ring.write()
                    time.sleep(0.05)
                    ring.fill((0,0,0))
                    ring.write()
        
        # Helpful for managing Daylight Savings
        if (hour == 3):
            machine.reset()

        # Otherwise, pulse the amount for the current hour            
        for i in range(hour % 12):
            ring.fill(LEDcolours[LEDindex])
            ring.write()
            time.sleep(0.3)
            ring.fill((0,0,0))
            ring.write()
            time.sleep(0.8)    
    
    # Light the LED dependent on temperature
    ring[(LEDindex - 4) % 12] = LEDcolours[LEDindex]
    ring.write()
    
    time.sleep(0.4)
