#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2015 Martin Steppuhn, www.emsystech.de. All rights reserved.
#
# Redistribution and use in source and binary, must retain the above copyright notice, and the following disclaimer.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.
#
# History:
# 24.06.2015    Martin Steppuhn     Initial version

import RPi.GPIO as GPIO  # http://sourceforge.net/p/raspberry-gpio-python/wiki/Home/
import fcntl
import time
from collections import namedtuple

class I2C(object):
	"""Wrapper class for I2C with raspberry Pi

	Open the "internal" I2C Port with driver or emulate an I2C Bus on GPIO
	"""
	addr = 0
	dev = None
	gpio_scl = 0
	gpio_sda = 0
	delay = 0.001

	def open(self,addr=0, dev=1, scl=0, sda=0):
		"""Open I2C-Port

		addr: I2C-Device Address
		dev:  I2C-Port (Raspberry Pi) B,B+,Pi 2 = 1 the first Pi = 0
			  For I2C Emulation with GPIO, dev must be None
		scl:  GPIO-Pin for SCL
		sda:  GPIO-Pin for SDA
		"""
		self.addr = addr
		self.dev = dev
		self.gpio_scl = scl
		self.gpio_sda = sda

		if (self.dev == None):
			GPIO.setwarnings(False)
			GPIO.setmode(GPIO.BCM)
			GPIO.setup(self.gpio_scl, GPIO.IN)  # SCL=1
			GPIO.setup(self.gpio_sda, GPIO.IN)  # SDA=1
		else:
			self.dev_i2c = open(("/dev/i2c-%s" % self.dev), 'rb+', 0)
			fcntl.ioctl(self.dev_i2c, 0x0706, self.addr)  # I2C Address

	def close(self):
		if (self.dev == None):
			GPIO.setup(self.gpio_scl, GPIO.IN)  # SCL=1
			GPIO.setup(self.gpio_sda, GPIO.IN)  # SDA=1
		else:
			self.dev_i2c.close()

	def write(self, data):
		"""Write data to device

		:param data: one ore more bytes (int list)
		"""
		if (self.dev == None):
			self._i2c_gpio_start()
			ack = self._i2c_gpio_write_byte(self.addr << 1)
			for b in data:
				ack = self._i2c_gpio_write_byte(b)
			self._i2c_gpio_stop()
		else:
			d = bytes(data)
			self.dev_i2c.write(d)

	def read(self, size):
		"""Read Bytes from I2C Device

		:param size: Number of Bytes to read
		:return: List with bytes
		"""
		data = dict()
		if (self.dev == None):
			self._i2c_gpio_start()
			ack = self._i2c_gpio_write_byte((self.addr << 1) + 1)  # set READ-BIT
			# if not ack: print("I2C-ERROR: READ,NACK1")
			for i in range(size):
				ack = True if ((i + 1) < size) else False
				data[i] = self._i2c_gpio_read_byte(ack)
			self._i2c_gpio_stop()
		else:
			data = self.dev_i2c.read(size)
		return (data)

	##########################################################################
	##########################################################################
	#   GPIO Access
	##########################################################################
	##########################################################################

	def _i2c_gpio_start(self):
		"""Send Start"""
		GPIO.setup(self.gpio_scl, GPIO.IN)  # SCL=1
		GPIO.setup(self.gpio_sda, GPIO.IN)  # SDA=1
		time.sleep(2 * self.delay)
		GPIO.setup(self.gpio_sda, GPIO.OUT)  # SDA=0
		GPIO.output(self.gpio_sda, 0)
		time.sleep(2 * self.delay)
		GPIO.setup(self.gpio_scl, GPIO.OUT)  # SCL=0
		GPIO.output(self.gpio_scl, 0)

	def _i2c_gpio_stop(self):
		"""Send Stop"""
		GPIO.setup(self.gpio_sda, GPIO.OUT)  # SDA=0
		GPIO.output(self.gpio_sda, 0)
		time.sleep(2 * self.delay)
		GPIO.setup(self.gpio_scl, GPIO.IN)  # SCL=1
		time.sleep(2 * self.delay)
		GPIO.setup(self.gpio_sda, GPIO.IN)  # SDA=1
		time.sleep(2 * self.delay)

	def _i2c_gpio_write_byte(self, data):
		"""Write a single byte"""
		for i in range(8):  # stop
			if (data & 0x80):
				GPIO.setup(self.gpio_sda, GPIO.IN)  # SDA=1
			else:
				GPIO.setup(self.gpio_sda, GPIO.OUT)  # SDA=0
				GPIO.output(self.gpio_sda, 0)
			data = data << 1
			time.sleep(self.delay)
			GPIO.setup(self.gpio_scl, GPIO.IN)  # SCL=1
			time.sleep(self.delay)
			# Clockstretching ToDo
			GPIO.setup(self.gpio_scl, GPIO.OUT)  # SCL=0
			GPIO.output(self.gpio_scl, 0)
			time.sleep(self.delay)

		GPIO.setup(self.gpio_sda, GPIO.IN)  # SDA=1
		time.sleep(self.delay)
		GPIO.setup(self.gpio_scl, GPIO.IN)  # SCL=1
		time.sleep(self.delay)
		# Clockstretching ToDo
		ack = True if (GPIO.input(self.gpio_sda) == 0) else False
		GPIO.setup(self.gpio_scl, GPIO.OUT)  # SCL=0
		GPIO.output(self.gpio_scl, 0)
		time.sleep(self.delay)
		return (ack)  # SCL=0 SDA=1

	def _i2c_gpio_read_byte(self, ack):
		"""Read a single byte"""
		data = 0
		for i in range(8):  # stop
			time.sleep(self.delay)
			GPIO.setup(self.gpio_scl, GPIO.IN)  # SCL=1
			time.sleep(self.delay)
			# Clockstretching ToDo
			data = data << 1
			if (GPIO.input(self.gpio_sda)):
				data |= 1
			else:
				data &= ~1
			GPIO.setup(self.gpio_scl, GPIO.OUT)  # SCL=0
			GPIO.output(self.gpio_scl, 0)

		# ACK Bit ausgeben
		if (ack):
			GPIO.setup(self.gpio_sda, GPIO.OUT)  # SDA=0
			GPIO.output(self.gpio_sda, 0)
		else:
			GPIO.setup(self.gpio_sda, GPIO.IN)  # SDA=1

		time.sleep(self.delay)
		GPIO.setup(self.gpio_scl, GPIO.IN)  # SCL=1
		time.sleep(self.delay)
		# Clockstretching ToDo
		GPIO.setup(self.gpio_scl, GPIO.OUT)  # SCL=0
		GPIO.output(self.gpio_scl, 0)
		time.sleep(self.delay)
		GPIO.setup(self.gpio_sda, GPIO.IN)  # SDA=1  freigeben
		return (data)
		
SHT21Result = namedtuple("SHT21Result", ("sensor_name", "is_valid", "temp", "hum"))

class SHT21(object):
	def __init__(self, i2c_bus_number, i2c_address):
		self._bus_number = i2c_bus_number
		self._address = i2c_address
		self._i2c = I2C()     # I2C Wrapper Class
		self._eid = self.read_electronic_id()
		if self._eid is None:
			raise ValueError("No I2C sensor on these pins.", scl_pin, sda_pin)
		
	def read(self):
		self.open()
		t = self.read_temperature()
		hum = self.read_humidity()
		is_valid = True
		if t is None:
			is_valid = False
			t = 0
		if hum is None:
			is_valid = False
			hum = 0
		self._i2c.close()
		return SHT21Result(self.get_sensor_name(), is_valid, t, hum)
		
	def open(self):
		self._i2c.open(self._address, self._bus_number)
		self._i2c.write([0xFE])  # execute Softreset Command  (default T=14Bit RH=12)
		time.sleep(0.050)
		

	def read_temperature(self):
		""" Temperature measurement (no hold master), blocking for ~ 88ms !!! """
		self._i2c.write([0xF3])
		time.sleep(0.086)  # wait, typ=66ms, max=85ms @ 14Bit resolution
		data = self._i2c.read(3)
		if (self._check_crc(data, 2)):
			t = ((data[0] << 8) + data[1]) & 0xFFFC  # set status bits to zero
			t = -46.82 + ((t * 175.72) / 65536)  # T = 46.82 + (175.72 * ST/2^16 )
			return round(t, 1)
		else:
			return None

	def read_humidity(self):
		""" RH measurement (no hold master), blocking for ~ 32ms !!! """
		self._i2c.write([0xF5])  # Trigger RH measurement (no hold master)
		time.sleep(0.03)  # wait, typ=22ms, max=29ms @ 12Bit resolution
		data = self._i2c.read(3)
		if (self._check_crc(data, 2)):
			rh = ((data[0] << 8) + data[1]) & 0xFFFC  # zero the status bits
			rh = -6 + ((125 * rh) / 65536)
			if (rh > 100): rh = 100
			return round(rh, 1)
		else:
			return None
			
	def read_electronic_id(self):
		self.open()
		self._i2c.write([0xFA, 0x0F])
		data = self._i2c.read(8)
		snb = 0
		for i in range(0, 8, 2):
			if not self._check_crc([data[i], data[i+1]], 1):
				return None
			snb = (snb << 8) + data[i]
			
		self._i2c.write([0xFC, 0xC9])
		data = self._i2c.read(6)
		if not self._check_crc([data[0], data[1], data[2]], 2):
			return None
		if not self._check_crc([data[3], data[4], data[5]], 2):
			return None
		snc = (data[0] << 8) + data[1]
		sna = (data[3] << 8) + data[4]
			
		return (format(sna, "x").zfill(4)
			+ format(snb, "x").zfill(8)
			+ format(snc, "x").zfill(4))
		self.close()

	def close(self):
		"""Closes the i2c connection"""
		self.i2c.close()

	def _check_crc(self, data, length):
		"""Calculates checksum for n bytes of data and compares it with expected"""
		crc = 0
		for i in range(length):
			crc ^= (ord(chr(data[i])))
			for bit in range(8, 0, -1):
				if crc & 0x80:
					crc = (crc << 1) ^ 0x131  # CRC POLYNOMIAL
				else:
					crc = (crc << 1)
		return True if (crc == data[length]) else False
		
	def get_sensor_type_name(self):
		return "SHT21"
		
	def get_sensor_name(self):
		return "SHT21_%s" % (self._eid,)

	def get_sensor_fields(self):
		return ["temp", "hum"]
		
	def get_sensor_options(self):
		return (self._bus_number, self._address)
		
	@staticmethod
	def detect_sensors():
		try:
			sensors = [SHT21(1, 0x40)] #Default bus is 1, default address is 0x40
		except (ValueError, FileNotFoundError, OSError):
			sensors = []
		#TODO: Not just probe the default pins
		return sensors


if __name__ == "__main__":
	sht21 = SHT21(1, 0x40)
	res = sht21.read()
	print("is_valid:%r temperature:%i huminidty:%i" % (res.is_valid, res.temp, res.hum))
