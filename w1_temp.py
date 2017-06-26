#!/usr/bin/env python3

from os.path import join, exists
import re
from collections import namedtuple

W1_DEVICES_DIR = "/sys/bus/w1/devices/"
SENSOR_PAT = re.compile("((?:[0-9a-f]{2} ){9}): crc=[0-9a-f]{2} (\w+)\n"
	"(?:[0-9a-f]{2} ){9}t=([0-9\-]+)")

	
W1Result = namedtuple("W1Result", ("sensor_name", "is_valid", "temp"))


class W1TempSensor(object):
	def __init__(self, name):
		if name[:3] == "W1_":
			name = name[3:]
		self._active_sensor = name
		
		sensor_file_path = join(W1_DEVICES_DIR, name, "w1_slave")
		if not exists(sensor_file_path):
			raise ValueError("No sensor connected with this ID.", name)

	def read(self):
		sensor_id = self._active_sensor
		sensor_dir = join(W1_DEVICES_DIR, sensor_id)
		
		data = ""
		sensor_file_path = join(sensor_dir, "w1_slave")
		if not exists(sensor_file_path):
			print("Sensor is unavailable: %s" % self.get_sensor_name())
			return False
		try:
			sensor_file = open(sensor_file_path)
		except FileNotFoundError:
			return False
		data = sensor_file.read()
		match = SENSOR_PAT.match(data)
		if not match:
			return False
		else:
			return W1Result(self.get_sensor_name(), match.group(2) == "YES", int(match.group(3)) / 1000)
			
	def get_sensor_type_name(self):
		return "W1Temp"

	def get_sensor_name(self):
		return "W1_%s" % self._active_sensor
		
	def get_sensor_fields(self):
		return ["temp"]
		
	def get_sensor_options(self):
		return (self._active_sensor,)
		
		
	@staticmethod
	def detect_sensors():
		master_dir = join(W1_DEVICES_DIR, "w1_bus_master1")

		sensors = list()
		try:
			with open(join(master_dir, "w1_master_slaves")) as slave_file:
				for line in slave_file:
					sensors.append(line[:-1])
		except FileNotFoundError:
			pass
		return [W1TempSensor(name) for name in sensors]

def get_sensors():
	return W1TempSensor.detect_sensors()

if __name__ == "__main__":
	sensor = W1TempSensor()
	result = sensor.read()
	print("valid:%r temperature:%i" % (result.is_valid, result.temp))
