#!/usr/bin/env python3

import bme680
from os.path import join, exists
from collections import namedtuple

BME680Result = namedtuple("BME680Result", ("sensor_name", "is_valid", "temp", "hum", "pres"))


class BME680(object):
	def __init__(self, i2c_bus_number, i2c_address):
		self.i2c_address = i2c_address
		self.i2c_bus_number = i2c_bus_number
		self.i2c_bus = smbus.SMBus(self.i2c_bus_number)

		self.sensor = bme680.BME680()
		self.sensor.set_humidity_oversample(bme680.OS_2X)
		self.sensor.set_pressure_oversample(bme680.OS_4X)
		self.sensor.set_temperature_oversample(bme680.OS_8X)
		self.sensor.set_filter(bme680.FILTER_SIZE_3)
		self.sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

	def read(self):
		if sensor.get_sensor_data():
			return BME280Result(self.get_sensor_name(), True, self.sensor.data.temperature, self.sensor.data.humidity, self.sensor.data.pressure)
		
	def get_sensor_type_name(self):
		return "BME680"
		
	def get_sensor_name(self):
		return "BME680_i2c-%i_0x%02x" % (self.i2c_bus_number, self.i2c_address)

	def get_sensor_fields(self):
		return ["temp", "hum", "pres"]
		
	def get_sensor_options(self):
		return (self.i2c_bus_number, self.i2c_address)

	@staticmethod
	def detect_sensors():
		try:
			sensors = [BME680(1, 0x77)] #Default bus is 1, default address is 0x77
		except (ValueError, ):
			sensors = []
		#TODO: Not just try the default address
		return sensors

if __name__ == "__main__":
	sensor = BME680()
	result = sensor.read()
	print("is_valid:%r temperature:%.2f huminidty:%.2f pressure:%.2f" % (result.is_valid, result.temp, result.hum, result.pres))
