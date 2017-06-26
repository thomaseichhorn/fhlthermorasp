#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import smbus
from collections import namedtuple

BME280Result = namedtuple("BME280Result", ("sensor_name", "is_valid", "temp", "hum", "pres"))

class BME280(object):
	def __init__(self, i2c_bus_number, i2c_address):
		self.i2c_address = i2c_address
		self.i2c_bus_number = i2c_bus_number
		self.i2c_bus = smbus.SMBus(self.i2c_bus_number)
		self.calibration_h = []
		self.calibration_p = []
		self.calibration_t = []
		self.t_fine = 0.0
		
		osrs_t = 1  # Temperature oversampling x 1
		osrs_p = 1  # Pressure oversampling x 1
		osrs_h = 1  # Humidity oversampling x 1
		mode = 3  # Normal mode
		t_sb = 5  # Tstandby 1000ms
		filter = 0  # Filter off
		spi3w_en = 0  # 3-wire SPI Disable

		ctrl_meas_reg = (osrs_t << 5) | (osrs_p << 2) | mode
		config_reg = (t_sb << 5) | (filter << 2) | spi3w_en
		ctrl_hum_reg = osrs_h

		self.write_byte_data(0xF2, ctrl_hum_reg)
		self.write_byte_data(0xF4, ctrl_meas_reg)
		self.write_byte_data(0xF5, config_reg)

		self.populate_calibration_data()
	
	def read_byte_data(self, cmd, bus=None, i2c_address=None):
		if bus is None:
			bus = self.i2c_bus
		if i2c_address is None:
			i2c_address = self.i2c_address
		return bus.read_byte_data(i2c_address, cmd)

	def write_byte_data(self, cmd, value, bus=None, i2c_address=None):
		if bus is None:
			bus = self.i2c_bus
		if i2c_address is None:
			i2c_address = self.i2c_address
		return bus.write_byte_data(i2c_address, cmd, value)
		
	def reset_calibration(self):
		self.calibration_h = []
		self.calibration_p = []
		self.calibration_t = []
		self.t_fine = 0.0
		
	def populate_calibration_data(self):
		raw_data = []

		for i in range(0x88, 0x88 + 24):
			raw_data.append(self.read_byte_data(i))
		raw_data.append(self.read_byte_data(0xA1))
		for i in range(0xE1, 0xE1 + 7):
			raw_data.append(self.read_byte_data(i))

		self.calibration_t.append((raw_data[1] << 8) | raw_data[0])
		self.calibration_t.append((raw_data[3] << 8) | raw_data[2])
		self.calibration_t.append((raw_data[5] << 8) | raw_data[4])
		self.calibration_p.append((raw_data[7] << 8) | raw_data[6])
		self.calibration_p.append((raw_data[9] << 8) | raw_data[8])
		self.calibration_p.append((raw_data[11] << 8) | raw_data[10])
		self.calibration_p.append((raw_data[13] << 8) | raw_data[12])
		self.calibration_p.append((raw_data[15] << 8) | raw_data[14])
		self.calibration_p.append((raw_data[17] << 8) | raw_data[16])
		self.calibration_p.append((raw_data[19] << 8) | raw_data[18])
		self.calibration_p.append((raw_data[21] << 8) | raw_data[20])
		self.calibration_p.append((raw_data[23] << 8) | raw_data[22])
		self.calibration_h.append(raw_data[24])
		self.calibration_h.append((raw_data[26] << 8) | raw_data[25])
		self.calibration_h.append(raw_data[27])
		self.calibration_h.append((raw_data[28] << 4) | (0x0F & raw_data[29]))
		self.calibration_h.append((raw_data[30] << 4) | ((raw_data[29] >> 4) & 0x0F))
		self.calibration_h.append(raw_data[31])

		for i in range(1, 2):
			if self.calibration_t[i] & 0x8000:
				self.calibration_t[i] = (-self.calibration_t[i] ^ 0xFFFF) + 1

		for i in range(1, 8):
			if self.calibration_p[i] & 0x8000:
				self.calibration_p[i] = (-self.calibration_p[i] ^ 0xFFFF) + 1

		for i in range(0, 6):
			if self.calibration_h[i] & 0x8000:
				self.calibration_h[i] = (-self.calibration_h[i] ^ 0xFFFF) + 1
				
	def compensate_pressure(self, adc_p):
		v1 = (self.t_fine / 2.0) - 64000.0
		v2 = (((v1 / 4.0) * (v1 / 4.0)) / 2048) * self.calibration_p[5]
		v2 += ((v1 * self.calibration_p[4]) * 2.0)
		v2 = (v2 / 4.0) + (self.calibration_p[3] * 65536.0)
		v1 = (((self.calibration_p[2] * (((v1 / 4.0) * (v1 / 4.0)) / 8192)) / 8) + ((self.calibration_p[1] * v1) / 2.0)) / 262144
		v1 = ((32768 + v1) * self.calibration_p[0]) / 32768

		if v1 == 0:
			return 0

		pressure = ((1048576 - adc_p) - (v2 / 4096)) * 3125
		if pressure < 0x80000000:
			pressure = (pressure * 2.0) / v1
		else:
			pressure = (pressure / v1) * 2

		v1 = (self.calibration_p[8] * (((pressure / 8.0) * (pressure / 8.0)) / 8192.0)) / 4096
		v2 = ((pressure / 4.0) * self.calibration_p[7]) / 8192.0
		pressure += ((v1 + v2 + self.calibration_p[6]) / 16.0)

		return pressure / 100
		
	def compensate_temperature(self, adc_t):
		v1 = (adc_t / 16384.0 - self.calibration_t[0] / 1024.0) * self.calibration_t[1]
		v2 = (adc_t / 131072.0 - self.calibration_t[0] / 8192.0) * (adc_t / 131072.0 - self.calibration_t[0] / 8192.0) * self.calibration_t[2]
		self.t_fine = v1 + v2
		temperature = self.t_fine / 5120.0
		return temperature

	def compensate_humidity(self, adc_h):
		var_h = self.t_fine - 76800.0
		if var_h == 0:
			return 0

		var_h = (adc_h - (self.calibration_h[3] * 64.0 + self.calibration_h[4] / 16384.0 * var_h)) * (
			self.calibration_h[1] / 65536.0 * (1.0 + self.calibration_h[5] / 67108864.0 * var_h * (
				1.0 + self.calibration_h[2] / 67108864.0 * var_h)))
		var_h *= (1.0 - self.calibration_h[0] * var_h / 524288.0)

		if var_h > 100.0:
			var_h = 100.0
		elif var_h < 0.0:
			var_h = 0.0

		return var_h
				
	def read_adc(self):
		data = []
		for i in range(0xF7, 0xF7 + 8):
			data.append(self.read_byte_data(i))
		pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
		temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
		hum_raw = (data[6] << 8) | data[7]

		return BME280Result(self.get_sensor_name(), True, temp_raw, hum_raw, pres_raw)
	
	def read_humidity(self, data=None):
		if data is None:
			data = self.read_adc()

		# We need a temperature reading to calculate humidity
		self.read_temperature(data)
		return self.compensate_humidity(data.hum)
		
	def read_pressure(self, data=None):
		if data is None:
			data = self.read_adc()

		# We need a temperature reading to calculate pressure
		self.read_temperature(data)
		return self.compensate_pressure(data.pres)

	def read_temperature(self, data=None):
		if data is None:
			data = self.read_adc()

		return self.compensate_temperature(data.temp)
		
	def read(self):
		data = self.read_adc()
		return BME280Result(self.get_sensor_name(), True,
			self.read_temperature(data),
			self.read_humidity(data),
			self.read_pressure(data))
		
	def get_sensor_type_name(self):
		return "BME280"
		
	def get_sensor_name(self):
		return "BME280_i2c-%i_0x%02x" % (self.i2c_bus_number, self.i2c_address)

	def get_sensor_fields(self):
		return ["temp", "hum", "pres"]
		
	def get_sensor_options(self):
		return (self.i2c_bus_number, self.i2c_address)
		
	@staticmethod
	def detect_sensors():
		try:
			sensors = [BME280(1, 0x76)] #Default bus is 1, default address is 0x76
		except (ValueError, ):
			sensors = []
		#TODO: Not just try the default address
		return sensors

if __name__ == '__main__':
	import argparse
	
	parser = argparse.ArgumentParser()

	parser.add_argument('--i2c-bus', default='1')
	parser.add_argument('--i2c-address', default='0x76')
	args = parser.parse_args()
	
	bme280 = BME280(int(args.i2c_bus), int(args.i2c_address, 0))

	res = bme280.read()

	print("is_valid:%r temperature:%.2f huminidty:%.2f pressure:%.2f" % (res.is_valid, res.temp, res.hum, res.pres))
