# fhlthermorasp

Scripts for environmental monitoring with a Raspberry Pi.  

Python:

bme280.py		-> Measure BME280 temperature, humidity and pressure sensors  
dht11.py		-> Measure DHT11 temperature and humidity sensors  
example_sensor.py	-> Example file
graph.py		-> Plot results
make_image.py		-> Use connected webcam for picture taking  
README.md		-> This file  
sensor_monitor.py	-> Run a continuous measurement  
sensor_monitor_gui.py	-> Run a continuous measurement with a GUI  
server.py		-> Report current measurement to a TCP client  
sht21.py		-> Measure SHT2x temperature and humidity sensors  
sht75.py		-> Measure SHT7x temperature and humidity sensors  
w1_temp.py		-> Measure DS18S20 temperature sensors  

C++:

monitor.cc		-> Run a continuous measurement, DHT11, DS18S20 and SHT1x


Typical operation with e.g. sht75:

python3 sensor_monitor.py --sht75 --dir=/opt/measurements/
python3 server.py /opt/measurements/readings.txt