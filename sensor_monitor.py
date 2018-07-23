#!/usr/bin/env python3

import os
from os.path import join
import json
from collections import defaultdict

from w1_temp import W1TempSensor
from sht21 import SHT21
from dht11 import DHT11
from bme280 import BME280
from sht75 import SHT75
from bme680 import BME680

class SensorMonitor(object):
	KNOWN_SENSORS = {
		"W1Temp": [W1TempSensor],
		"SHT21": [SHT21],
		"DHT11": [DHT11],
		"BME280": [BME280],
		"SHT75": [SHT75],
		"BME680": [BME280]
	}
	
	def __init__(self, sensors = list(), readings_path = None,
			readings_log_path = None,
			mrtg_path = "/var/www/scripts/sensoroutput",
			options_path = None,
			alarm_number = None):
		self._loaded_sensors = list()
		self._readings_path = join(os.getcwd(), "readings.txt")
		self._readings_log_path = join(os.getcwd(), "readings_log.txt")
		self._mrtg_path = mrtg_path
		self._log_fields = list()
		self._should_abort = False
		self._alarms = dict()
		self._alarm_number = 1
		self._alarm_states = defaultdict(int)
		self._alarm_causes = defaultdict(list)
		self.options_from_file = dict()
		
		if not options_path is None:
			self.options_from_file, sensors_ = self.set_options_from_file(options_path)
			for sensor in sensors_:
				self.add_sensor(sensor)
		if not readings_path is None:
			self._readings_path = readings_path
		if not readings_log_path is None:
			self._readings_log_path = readings_log_path
		if not alarm_number is None:
			self._alarm_number = alarm_number
		
		for sensor in self.load_sensors(sensors):
			self.add_sensor(sensor)
				
	def load_sensors(self, sensors):
		loaded_sensors = list()
		for sensor_name, sensor_opts in sensors:
			sensor_class = self.KNOWN_SENSORS[sensor_name][0]
			if sensor_opts is None:
				loaded_sensors.extend(sensor_class.detect_sensors())
			else:
				loaded_sensors.append(sensor_class(*sensor_opts))
		return loaded_sensors
					
	def add_sensor(self, sensor):
		name = sensor.get_sensor_name()
		if name in [s.get_sensor_name() for s in self._loaded_sensors]:
			print("Warning: Already added sensor %s." % (name,))
			return
		
		self._loaded_sensors.append(sensor)
		for field in sensor.get_sensor_fields():
			self._log_fields.append("%s_%s" % (name, field))
			
	def remove_sensor(self, sensor):
		self._loaded_sensors.remove(sensor)
		name = sensor.get_sensor_name()
		for field in sensor.get_sensor_fields():
			self._log_fields.remove("%s_%s" % (name, field))
			
	def save_log_fields(self):
		log_file = open(self._readings_log_path, "a")
		line = self.get_log_fields()
		log_file.write("#%s\n" % (line,))
		log_file.close()
		return line
		
	def set_readings_path(self, readings_path):
		self._readings_path = readings_path
		
	def get_readings_path(self):
		return self._readings_path
		
	def set_readings_log_path(self, readings_log_path):
		self._readings_log_path = readings_log_path
		
	def get_readings_log_path(self):
		return self._readings_log_path
		
	def get_log_fields(self):
		return "date time %s" % (" ".join(self._log_fields),)
		
	def get_readings(self, check_alarm = True):
		readings = dict()
		self._should_abort = False
		for sensor in self._loaded_sensors:
			fields = sensor.get_sensor_fields()
			reading = sensor.read()
			#if reading.sensor_name in readings:
			#	error
			reading_dict = None
			if reading and reading.is_valid:
				reading_dict = dict()
				for field in fields:
					#if field in reading_dict:
					#	error
					reading_dict[field] = getattr(reading, field)
			readings[reading.sensor_name] = reading_dict
			if self._should_abort:
				break
			
		if check_alarm:
			self._check_alarm_for_readings(readings)
			
		self._should_abort = False
		return readings
		
	def abort(self):
		self._should_abort = True
		
	def _generate_readings_line(self, datetime, readings):
		log_dict = dict()
		for sensor_name, reading in readings.items():
			if reading is None:
				continue
			for field_name, value in reading.items():
				log_field = "%s_%s" % (sensor_name, field_name)
				log_dict[log_field] = value
				
		reading_line = datetime.isoformat(" ")
		for field in self._log_fields:
			reading_line += " "
			if field in log_dict and log_dict[field] != False and not log_dict[field] is None:
				reading_line += "%.2f" % (log_dict[field],)
		
		return reading_line
		
	def save_readings(self, datetime, readings):
		reading_line = self._generate_readings_line(datetime, readings)
				
		log_file = open(self._readings_log_path, "a")
		log_file.write(reading_line + "\n")
		log_file.close()
		
		cur_file = open(self._readings_path, "w")
		cur_file.write("#{}\n".format(self.get_log_fields()))
		cur_file.write(reading_line)
		cur_file.close()
		
		#if self._mrtg_path != False:
		#	i = 1
		#	for sensor_name, reading in readings.items():
		#		if reading is None:
		#			continue
		#		mrtg_file = open(join(self._mrtg_path, "%i.txt" % (i,)), "w")
		#		values = ["%0.2f" % (val,) for val in reading.values()]
		#		mrtg_file.write(" ".join(values))
		#		i += 1
		
		return reading_line
		
	def get_sensor_options(self):
		sensor_options = list()
		for sensor in self._loaded_sensors:
			ty = sensor.get_sensor_type_name()
			opt = sensor.get_sensor_options()
			sensor_options.append((ty, opt))
		return sensor_options
		
	def get_options(self):
		options = dict()
		options["sensors"] = self.get_sensor_options()
		options["readings_path"] = self.get_readings_path()
		options["readings_log_path"] = self.get_readings_log_path()
		options["alarms"] = self._alarms.copy()
		options["alarm_number"] = self._alarm_number
		return options
		
	def set_options_from_file(self, path, add_sensors = False):
		size = os.path.getsize(path)
		if size == 0:
			raise EOFError("Empty json file.")
		
		fp = open(path, "r")
		options = json.load(fp)
		fp.close()
		if "sensors" in options:
			sensors = self.load_sensors(options["sensors"])
		if add_sensors:
			for sensor in sensors:
				self.add_sensor(sensor)
		if "readings_path" in options:
			self._readings_path = options["readings_path"]
		if "readings_log_path" in options:
			self._readings_log_path = options["readings_log_path"]
		if "alarms" in options:
			for field, limits in options["alarms"].items():
				self.set_alarm_limits(field, int(limits[0]), int(limits[1]))
		if "alarm_number" in options:
			self._alarm_number = int(options["alarm_number"])
		return (options, sensors)
		
	def set_alarm_limits(self, field_name, limit1, limit2):
		low = min(limit1, limit2)
		high = max(limit1, limit2)
		self._alarms[field_name] = (low, high)
		
	def get_alarm_limits(self, field_name):
		if not field_name in self._alarms:
			return (None, None)
		else:
			return self._alarms[field_name]
		
	def unset_alarm_for(self, field_name):
		if field_name in self._alarms:
			del self._alarms[field_name]
		
	def set_alarm_number(self, alarm_number):
		self._alarm_number = alarm_number
		
	def get_alarm_number(self):
		return self._alarm_number
			
	def _check_alarm_for_count(self, field, count):
		return count >= self._alarm_number
			
	def _check_alarm_for_readings(self, readings):
		alarm = False
		states_per_reading = defaultdict(int)
		cause_per_reading = defaultdict(list)
		
		for sensor_name, reading in readings.items():
			if reading is None:
				continue
			for field in (self._alarms.keys() & reading.keys()):
				limits = self._alarms[field]
				value = reading[field]
				if not limits[0] <= value <= limits[1]:
					states_per_reading[field] += 1
					cause_per_reading[field].append(value)
		
		for field, count in states_per_reading.items():
			if count > 0:
				self._alarm_states[field] += 1
				self._alarm_causes[field].extend(cause_per_reading[field])
			else:
				self._alarm_states[field] = 0
				self._alarm_causes[field].clear()
			if self._check_alarm_for_count(field, count):
				self._ring_alarm(field, cause_per_reading[field])
				alarm = True
		
		for field in (self._alarm_states.keys() - states_per_reading.keys()):
			self._alarm_states[field] = 0
			self._alarm_causes[field].clear()
			
		for field, count in self._alarm_states.items():
			if not alarm and self._check_alarm_for_count(field, count):
				self._ring_alarm(field, self._alarm_causes[field])
				alarm = True
				self._alarm_states[field] = 0
				self._alarm_causes[field].clear()
		
		return alarm
	
	def _ring_alarm(self, field_name, over_limit_values):
		print("Alarm for %s with values: %s" % (field_name, "; ".join(map(str, over_limit_values))))
		
if __name__ == "__main__":
	from argparse import ArgumentParser
	import datetime
	import time
	import sys
	
	parser = ArgumentParser(description="Monitor various sensors over time.")
	parser.add_argument("--dir", type=str, help="A directory to save logs to. Default: Save to CWD.")
	parser.add_argument("--config", "-c", type=str, help="A JSON config file to read configuration (enabled sensors etc.) from.")
	parser.add_argument("--save-config", type=str, help="If set, will save the current configuration to the supplied path and exit.")
	parser.add_argument("--interval", "-i", type=int, default=10, help="Interval to wait between measurements in seconds. Default: 10")
	parser.add_argument("--alarm-temp", type=float, nargs=2, help="If set, alarm will be rang if temperature is not within these two values for alarm_num times.")
	parser.add_argument("--alarm-hum", type=float, nargs=2, help="If set, alarm will be rang if humidity is not within these two values for alarm_num times.")
	parser.add_argument("--alarm-pres", type=float, nargs=2, help="If set, alarm will be rang if pressure is not within these two values for alarm-num times.")
	parser.add_argument("--num-alarm", type=int, help="The number of times a measurement can be (successive) outside of the limits given by the --alarm-* options. Default: 1")
	parser.add_argument("--w1", action="store_true", help="Enable W1 sensors and try to auto-detect them.")
	parser.add_argument("--dht11", action="store_true", help="Enable DHT11 sensors and try to auto-detect them.")
	parser.add_argument("--sht21", action="store_true", help="Enable SHT21 sensors and try to auto-detect them.")
	parser.add_argument("--bme280", action="store_true", help="Enable BME280 sensors and try to auto-detect them.")
	parser.add_argument("--sht75", action="store_true", help="Enable SHT75 sensors and try to auto-detect them.")
	parser.add_argument("--bme680", action="store_true", help="Enable BME680 sensors and try to auto-detect them.")
	args = parser.parse_args()
	
	sensors = list()
	if args.w1:
		sensors.append(("W1Temp", None))
	if args.dht11:
		sensors.append(("DHT11", None))
	if args.sht21:
		sensors.append(("SHT21", None))
	if args.bme280:
		sensors.append(("BME280", None))
	if args.sht75:
		sensors.append(("SHT75", None))
	if args.bme680:
		sensors.append(("BME680", None))
		
	if not args.dir is None:
		readings_path = join(args.dir, "readings.txt")
		readings_log_path = join(args.dir, "readings_log.txt")
	else:
		readings_path = None
		readings_log_path = None
	
	if not args.config is None:
		monitor = SensorMonitor(sensors, readings_path,
			readings_log_path, options_path=args.config,
			alarm_number = args.num_alarm)
	else:
		monitor = SensorMonitor(sensors, readings_path,
			readings_log_path, alarm_number = args.num_alarm)
	if not args.alarm_temp is None:
		monitor.set_alarm_limits("temp", args.alarm_temp[0], args.alarm_temp[1])
	if not args.alarm_hum is None:
		monitor.set_alarm_limits("hum", args.alarm_temp[0], args.alarm_temp[1])
	if not args.alarm_pres is None:
		monitor.set_alarm_limits("pres", args.alarm_temp[0], args.alarm_temp[1])
		
	if not args.save_config is None:
		options = monitor.get_options()
		options["interval"] = args.interval
		fp = open(args.save_config, "w")
		json.dump(options, fp, indent=4)
		fp.close()
		sys.exit()
	
	print(monitor.save_log_fields())
	while True:
		readings = monitor.get_readings()
		line = monitor.save_readings(datetime.datetime.now(), readings)
		print(line)
		time.sleep(args.interval)
