#!/usr/bin/env python3

from os.path import join, exists
import re
from collections import namedtuple
	
W1Result = namedtuple("W1Result", ("sensor_id", "temperature", "humidity", "is_valid"))

class W1Temp():
	W1_DEVICES_DIR = "/sys/bus/w1/devices/"
	SENSOR_PAT = re.compile("((?:[0-9a-f]{2} ){9}): crc=[0-9a-f]{2} (\w+)\n"
		"(?:[0-9a-f]{2} ){9}t=([0-9\-]+)")
	
	def __init__(self, active_sensor = None):
		self.find_sensors()
		if len(self._sensors) == 0:
			return
		if active_sensor == None:
			self.set_active_sensor(self._sensors[0])
		else:
			self.set_active_sensor(active_sensor)
	
	def find_sensors(self):
		master_dir = join(self.W1_DEVICES_DIR, "w1_bus_master1")

		self._sensors = []
		try:
			with open(join(master_dir, "w1_master_slaves")) as slave_file:
				for line in slave_file:
					self._sensors.append(line[:-1])
		except FileNotFoundError:
			pass
			
	def get_sensors(self):
		return list(self._sensors)
		
	def set_active_sensor(self, sensor_id):
		self._active_sensor = sensor_id
		
	def get_active_sensor(self):
		return self._active_sensor

	def measure(self, sensor_id):
		if not sensor_id in self._sensors:
			return False
		sensor_dir = join(self.W1_DEVICES_DIR, sensor_id)
		
		data = ""
		with open(join(sensor_dir, "w1_slave")) as sensor_file:
			data = sensor_file.read()
		match = self.SENSOR_PAT.match(data)
		if not match:
			return False
		else:
			return W1Result(sensor_id, int(match.group(3)) / 1000, None, match.group(2) == "YES")
			
	def read(self):
		return self.measure(self._active_sensor)
	def get_sensor_name(self):
		return "W1_%s" % self._active_sensor

def get_sensor_clas():
	return W1Temp

if __name__ == "__main__":
	sensor = W1Temp()
	result = sensor.read()
	print("valid:%r temperature:%i" % (result.is_valid, result.temperature))
