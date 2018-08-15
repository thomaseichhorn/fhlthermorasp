# fhlthermorasp

Scripts for environmental monitoring with a Raspberry Pi.

# Supported sensors

- DS18S20 temperature sensor
- DHT11 temperature and humidity sensor
- SHT2x temperature and humidity sensor
- SHT7x temperature and humidity sensor
- BME280 temperature, humidity and pressure sensor
- BME680 temperature, humidity, pressure and air quality sensor

# Single measurements with python

Usage:

- `python3 w1_temp.py` for DS18S20
- `python3 dht11.py` for DHT11
- `python3 sht21.py` for SHT2x
- `python3 sht75.py` for SHT7x
- `python3 bme280.py` for BME280
- `python3 bme680.py` for BME680

Other tools/files:

- `example_sensor.py` is an example file
- `python3 graph.py` does some simple analysis (ROOT required)
- `sh initi2c.sh` can be used to reset the i2c bus after an error
- `python3 make_image.py` can be used for picture taking with a connected web cam
- `README.md` is this file

# Continuous measurements with python

Usage:

- `python3 sensor_monitor.py --<sensors> --dir <directory>` for continuous read-out, results are saved to <directory>
- `python3 sensor_monitor_gui.py` contains a GUI
- `python3 server.py <file>` reports the current measurement status to a TCP client


# C++ implementation

Still under development

- You can compile `monitor.cc` for a continuous measurement of some sensors
