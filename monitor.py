#!/usr/bin/env python3

from sys import argv, exit, stderr
from os.path import isdir, join, exists
from os import rename
from time import sleep
import datetime
import importlib
from argparse import ArgumentParser

INTERVAL = 10
RETRY_INTERVAL = 10
#SENSORS = {"w1_temp": [], "dht11": [17, 18, 27]}
SENSORS = {"w1_temp": [], "sht21": [3, 2]}

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
	
	measurements_by_sensor = dict()
	measure_str = ""
	for measurement in measurements:
		measurements_by_sensor[measurement.sensor_name] = measurement
	for name, field in sensor_fields:
		if not name in measurements_by_sensor:
			print("No measurement by %s (%s)" % (name, field))
			measure_str += " "
		else:
			measure_str += "%.2f " % (getattr(measurements_by_sensor[name], field),)
	
	print(measure_str)
	with open(cur_path_tmp, "w") as f:
		f.write(measure_str + "\n")
	rename(cur_path_tmp, cur_path)
	with open(hist_path, "a") as f:
		f.write("%s%s\n" % (get_timestamp(), measure_str))
		
parser = ArgumentParser(description="Monitor various sensors over time.")
parser.add_argument("directory", type=str, help="A directory to save logs to.")
args = parser.parse_args()

if not isdir(args.directory):
	exit("Not a directory: %s" % args.directory)
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
save_format(args.directory, sensor_fields)
print("Loaded sensors: %s" % " ".join(["%s_%s" % (name, field) for name, field in sensor_fields]))
	
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
				#sleep(RETRY_INTERVAL)
			else:
				measurements.append(measurement)
				break
	if len(measurements) == 0:
		sleep(RETRY_INTERVAL)
		continue
	save_measurements(args.directory, sensor_fields, *measurements)
	sleep(INTERVAL)

