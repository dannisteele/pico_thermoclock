# General imports
from machine import Pin, ADC, I2C, UART
import time
import uos
from dht20 import DHT20
from neopixel import NeoPixel
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

# Network imports
import network
import socket
import struct

# Constants
NTP_DELTA = 2208988800
HOST = "pool.ntp.org"
SSID = 'HOSTNAME'
PASSWORD = 'PASSWORD'
LED_PIN = "LED"
POTENTIOMETER_PIN = 28
I2C_SDA_PIN = 14
I2C_SCL_PIN = 15
NEOPIXEL_PIN = 2

# Configuration
i2c1_sda = Pin(I2C_SDA_PIN)
i2c1_scl = Pin(I2C_SCL_PIN)
i2c1 = I2C(1, sda=i2c1_sda, scl=i2c1_scl)
potentiometer = ADC(Pin(POTENTIOMETER_PIN))
led = Pin("LED", Pin.OUT)
dht20 = DHT20(0x38, i2c1)
lcdi2c = I2C(1, sda=machine.Pin(I2C_SDA_PIN), scl=machine.Pin(I2C_SCL_PIN), freq=400000)
lcd = I2cLcd(lcdi2c, 0x27, 2, 16)
ring = NeoPixel(Pin(NEOPIXEL_PIN), 12)
IDEAL_TEMP = 20
uart = UART(0, baudrate=115200)
uart.init(115200, bits=8, parity=None, stop=1, tx=Pin(0), rx=Pin(1))
uos.dupterm(uart)

# Create a temperature/LED dictionary for our scale
# Temperature is the key (left), LED index is the value (right)
LEDdict = {
  IDEAL_TEMP - 3: 0,
  IDEAL_TEMP - 2.5: 1,
  IDEAL_TEMP - 2: 2,
  IDEAL_TEMP - 1.5: 3,
  IDEAL_TEMP - 1: 4,
  IDEAL_TEMP - 0.5: 5,
  IDEAL_TEMP: 6, # Top-middle LED (index 6 / LED #7) for ideal temp in °C
  IDEAL_TEMP + 0.5: 7,
  IDEAL_TEMP + 1: 8,
  IDEAL_TEMP + 1.5: 9,
  IDEAL_TEMP + 2: 10,
  IDEAL_TEMP + 2.5: 11,
}

LEDcolours = [
    (0,0,10),
    (0,2,8),
    (0,4,6),
    (0,6,4),
    (0,8,6),
    (0,9,1),
    (0,10,0),
    (1,9,0),
    (4,6,0),
    (6,4,0),
    (8,2,0),
    (10,0,0)]
    
# Grab data from the sensor dictionary
measurements = dht20.measurements
    
# Create temp and humidity variables
# From initial readings
lowtemp = round(measurements['t'],1)
hightemp = round(measurements['t'],1)

# Set up the file - create a header if there is not one already
try:
    file=open("data.csv","r")
except OSError:
    file=open("data.csv","a+")
    file.write("Date,Time,Temperature,Humidity\n")
    
firstline = file.readline()
file.close()
if (uos.stat('data.csv')[6] == 0 or firstline != "Date,Time,Temperature,Humidity\n"):
    file=open("data.csv","w")
    file.write("Date,Time,Temperature,Humidity\n")
    file.close()
file=open("data.csv","a+")
lastLine = file.readlines()[-1][:19]
file.close()

def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    i = 5
    while wlan.isconnected() == False:
        lcd.move_to(3, 0) 
        lcd.putstr("Connecting")
        lcd.move_to(i, 1)
        lcd.putstr('.')
        i = i + 1
        time.sleep(1)
        
    lcd.clear()
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    return ip
    
def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    return connection

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
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
    
def webpage(temperature, humidity, file):
    #Template HTML
    html = f"""
            <!DOCTYPE html>
            <html>
            <form action="./downloadfile">
            <a href="./data.csv" download><input type="submit" value="Download Data" /></a>
            </form>
            <form action="./deletefile">
            <input type="submit" value="Delete file" />
            </form>
            <p>Temperature is {temperature}</p>
            <p>Humidity is {humidity}</p>
            </body>
            </html>
            """
    return html

def serve(connection):
    #Start a web server
    client = connection.accept()[0]
    request = client.recv(1024)
    request = str(request)
    try:
        request = request.split()[1]
    except IndexError:
        pass
    if request == '/downloadfile?':
        downloadfile()
    elif request =='/deletefile?':
        deletefile()
    html = webpage(temperature, humidity, "./data.csv")
    client.send(html)
    client.close()

connect()
led.on()
set_time()
lcd.move_to(6, 0) 
lcd.putstr("Date")
lcd.move_to(4, 1)
lcd.putstr(str(time.localtime()[2]) + "-" + str(time.localtime()[1]) + "-" + str(time.localtime()[0]))
time.sleep(2)
lcd.clear()
led.off()

# Create a rounded variable for the temperature and humidity
temperature = round(measurements['t'] * 2) / 2
humidity = round(measurements['rh'], 1)
tempnow = round(measurements['t'],1)

# The code
while True:
    if (potentiometer.read_u16() < 32000):
        lcd.backlight_off()
    else:
        lcd.backlight_on()
    
    measurements = dht20.measurements
    
    # Create a rounded variable for the temperature and humidity
    temperature = round(measurements['t'] * 2) / 2
    humidity = round(measurements['rh'], 1)
    tempnow = round(measurements['t'],1)
    
    if temperature < IDEAL_TEMP - 3:
        temperature = IDEAL_TEMP - 3
        print("*** Temperature very low ***")
    
    elif temperature > IDEAL_TEMP + 2.5:
        temperature = IDEAL_TEMP + 2.5
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
        if (second == 0 or second == 20 or second == 40):
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
        lcd.move_to(6, 0) 
        lcd.putstr("Time")
        lcd.move_to(4, 1)
        lcd.putstr(hourstring + ":" + minutestring + ":" + secondstring)
    
    # Print the temperature and index
    print(f"Current time: {hourstring}:{minutestring}:{secondstring}")
    print("Temperature:",round(measurements['t'],2))
    print("Rounded temp:", temperature)
    print(f"Humidity:    {humidity}%")
    print("----------------")
            
    # Clear the ring
    ring.fill((0,0,0))
    ring.write()
    

    
    if (minute % 30 == 0
        and second == 0):
        file=open("data.csv","a+")
        if (lastLine != "{}-{}-{}".format(yearstring, monthstring, daystring)
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
        
    if (minute == 0 and second == 0):
        if (hour == 0):
            lcd.putstr("Current:")
            lcd.move_to(0, 1)
            lcd.putstr("L:       H:")
            lowtemp = round(measurements['t'],1)
            hightemp = round(measurements['t'],1)
            
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
                    
        for i in range(hour % 12):
            ring.fill(LEDcolours[LEDindex])
            ring.write()
            time.sleep(0.3)
            ring.fill((0,0,0))
            ring.write()
            time.sleep(0.8)    
    
    ring[LEDindex] = LEDcolours[LEDindex] # Light the index LED
    ring.write() # Write the LED data
    
    time.sleep(0.4)

