#!/usr/bin/env python3

from sys import argv, exit, stderr
from os.path import isdir, join, exists
from os import rename
from time import sleep
import datetime
import importlib

INTERVAL = 10
RETRY_INTERVAL = 1
SENSORS = {"w1_temp": [], "dht11": [4]}

def get_timestamp():
	return datetime.datetime.now().isoformat(' ')
def save_format(directory, sensor_names, fields):
	hist_path = join(directory, "temp_history.txt")
	
	with open(hist_path, "a") as f:
		s_fields = []
		for sensor in sensor_names:
			for field in fields:
				s_fields.append("%s_%s" % (sensor, field))
		f.write("#date time " + " ".join(s_fields) + "\n")
		
def save_measurements(directory, *measurements):
	cur_path = join(directory, "temp.txt")
	cur_path_tmp = join(directory, "temp_tmp.txt")
	hist_path = join(directory, "temp_history.txt")
	
	me_string = ""
	for measurement in measurements:
		me_string += " "
		if measurement.temperature != None:
			me_string += "%.2f" % float(measurement.temperature)
		me_string += " "
		if measurement.humidity != None:
			me_string += "%.2f" % float(measurement.humidity)
	
	with open(cur_path_tmp, "w") as f:
		f.write(me_string + "\n")
	rename(cur_path_tmp, cur_path)
	with open(hist_path, "a") as f:
		f.write("%s%s\n" % (get_timestamp(), me_string))

if len(argv) < 2:
	exit("Please input a directory to save data to.")
if not isdir(argv[1]):
	exit("Not a directory: %s" % argv[1])
loaded_sensors = []
for sensor in sorted(list(SENSORS.keys())):
	sensor_module = importlib.import_module(sensor)
	loaded_sensors.append(sensor_module.get_sensor_clas()(*SENSORS[sensor]))
	
sensor_names = []
for sensor in loaded_sensors:
	sensor_names.append(sensor.get_sensor_name())
save_format(argv[1], sensor_names, ["temp", "hum"])
print("Loaded sensors: %s" % " ".join(sensor_names))
	
while True:
	measurements = []
	for sensor in loaded_sensors:
		while True:
			measurement = sensor.read()
			if not measurement:
				print("Failed to measure %s." % sensor.get_sensor_name(), file=stderr)
				break
			elif not measurement.is_valid:
				print("Got invalid measurement from %s." % sensor.get_sensor_name(), file=stderr)
				sleep(RETRY_INTERVAL)
			else:
				measurements.append(measurement)
				break
	if len(measurements) == 0:
		sleep(RETRY_INTERVAL)
		continue
	save_measurements(argv[1], *measurements)
	sleep(INTERVAL)
print(sensors)
print(mes)
