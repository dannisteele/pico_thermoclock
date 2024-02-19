# Pico Thermoclock
This code assumes the user has a Raspberry Pi Pico W, althoguh other wifi-enabled microcontrollers may also work.

Some modifications are necessary:
- SSID hostname and password need replacing.
- it assumes a potentiometer dht20 is in use, and connected to pin 28 of the Pico.
- A 12 LED ring is in use and connected to pin 2
- Other changes should be obvious, but I will add them over time.
- The ideal temperature should be set within the constants.

# What does it do?
The Thermoclock measures the temperature and humidity of the area where it is placed.
If it is the ideal temperature, then the light will be green and at the top of the ring. 
As it gets colder, the light will move left and get bluer.
As it gets hotter, the light right move right and get redder. 
Every 30 minutes, it will log the date, time, temperature and humidity to data.csv on the Pico. This can be commented out if not needed, or can be used for databases to keep track of house readings. 
On the hour, every hour, it will pulse all of the lights. The frequency of this depends on the time. At 5pm, it will pulse 5 times, at 9am is will pulse 9 times, etc.
At midnight and midday, the lights will spiral around the ring 12 times, just for something a little different.
Every 10 seconds, the attached LCD screen alternates between showing the time, and showing the current temperature as well as the highest and lowest it has been through the day. 
Every midnight, the highest and lowest temperatures reset.
