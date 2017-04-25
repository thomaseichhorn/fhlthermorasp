#!/usr/bin/env python3

from sys import argv, exit, stderr
from os.path import isdir, join, exists
from os import rename
from time import sleep
import datetime
import importlib

INTERVAL = 10
RETRY_INTERVAL = 10
SENSORS = {"w1_temp": [], "dht11": [17], "dht11": [18], "dht11": [27]}

def get_timestamp():
	return datetime.datetime.now().isoformat(' ')

def save_format(directory, sensor_fields):
	hist_path = join(directory, "temp_history.txt")
	
	with open(hist_path, "a") as f:
		s_fields = []
		for name, field in sensor_fields:
			s_fields.append("%s_%s" % (name, field))
		f.write("#date time %s\n" % (" ".join(s_fields),))
		
def save_measurements(directory, sensor_fields, *measurements):
	cur_path = join(directory, "temp.txt")
	cur_path_tmp = join(directory, "temp_tmp.txt")
	hist_path = join(directory, "temp_history.txt")
	
	measure_dict = dict()
	measure_str = ""
	for measurement in measurements:
		measure_dict[measurement.sensor_name] = measurement
	print(measure_dict)
	for name, fields in sensor_fields:
		for field in fields:
			measure_str += " %.2f" % (getattr(measure_dict[name], field),)
	
	with open(cur_path_tmp, "w") as f:
		f.write(measure_str + "\n")
	rename(cur_path_tmp, cur_path)
	with open(hist_path, "a") as f:
		f.write("%s%s\n" % (get_timestamp(), measure_str))

if len(argv) < 2:
	exit("Please input a directory to save data to.")
if not isdir(argv[1]):
	exit("Not a directory: %s" % argv[1])
loaded_sensors = []
for sensor in sorted(list(SENSORS.keys())):
	sensor_module = importlib.import_module(sensor)
	loaded_sensors.extend(sensor_module.get_sensors(*SENSORS[sensor]))
	
sensor_fields = []
for sensor in loaded_sensors:
	fields = sensor.get_sensor_fields()
	sname = sensor.get_sensor_name()
	for field in fields:
		sensor_fields.append((sname, field))
save_format(argv[1], sensor_fields)
print("Loaded sensors: %s" % " ".join([name for name, fields in sensor_fields]))
	
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
	save_measurements(argv[1], sensor_fields, *measurements)
	sleep(INTERVAL)
print(sensors)
print(mes)
