#!/usr/bin/python3

from collections import namedtuple
import serial
#ser = serial.Serial ( '/dev/ttyUSB0', 9600 )

DustResult = namedtuple ( "DustResult", ( "sensor_name", "is_valid", "smalldust", "largedust" ) )

class DustSensor ( object ) :
	def __init__ ( self, number ) :
		self._number = number
		
	def read ( self ) :
		while True :
			data = ser.readline ( )
			if data :
				[small_str, large_str] = data.split ( b',' )
				smalldst = float ( small_str )
				largedst = float ( large_str )
				if smalldst < 0.5 :
					smalldst = float ( 0.00001 )
				if largedst < 0.5 :
					largedst = float ( 0.00001 )
				return DustResult ( self.get_sensor_name ( ), True, smalldst, largedst )
	
	def get_sensor_type_name ( self ) :
		return "DustSensor"
		
	def get_sensor_name ( self ) :
		return ( "DustSensor_%i" % self._number )

	def get_sensor_fields ( self ) :
		return ["smalldust", "largedust"]

	def get_sensor_options ( self ) :
		return ( self._number )
		
	@staticmethod
	def detect_sensors ( ) :
		return [DustSensor ( 1 )]

if __name__ == "__main__":
	sensor = DustSensor ( 1 )
	result = sensor.read ( )
	print ( "valid:%r smalldust:%i largedust:%i" % ( result.is_valid, result.smalldust, result.largedust ) )
