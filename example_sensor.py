#!/usr/bin/python3

from collections import namedtuple

ExampleResult = namedtuple("ExampleResult", ("sensor_name", "is_valid"))

class ExampleSensor(object):
	def __init__(self, number):
		self._number = number
		
	def read(self):
		return ExampleResult(self.get_sensor_name(), True)
	
	def get_sensor_type_name(self):
		return "Example"
		
	def get_sensor_name(self):
		return "Example_i" % (self._number,)

	def get_sensor_fields(self):
		#return ["temp", "hum", "pres"] #can meassure temperature, humidity and pressure
		return [] #this sensor can't actaully meassure anything
		
	def get_sensor_options(self):
		return (self._number)
		
	@staticmethod
	def detect_sensors():
		return [ExampleSensor(1)]
