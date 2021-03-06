import time
import RPi
import RPi.GPIO as GPIO
from collections import namedtuple

NUM_BCM_PINS = 28 #including BCM0

DHT11Result = namedtuple("DHT11Result", ("sensor_name", "is_valid", "temp", "hum"))

class DHT11(object):
	'DHT11 sensor reader class for Raspberry'

	def __init__(self, pin):
		if pin >= NUM_BCM_PINS:
			raise ValueError("No pin with this BCM number.", pin)
		#Need reliable way to check if there is a DHT11 on this pin
		self.__pin = pin
		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BCM)
		GPIO.cleanup()

	def read(self):
		GPIO.setmode(GPIO.BCM)
		RPi.GPIO.setup(self.__pin, RPi.GPIO.OUT)

		# send initial high
		self.__send_and_sleep(RPi.GPIO.HIGH, 0.05)

		# pull down to low
		self.__send_and_sleep(RPi.GPIO.LOW, 0.02)

		# change to input using pull up
		RPi.GPIO.setup(self.__pin, RPi.GPIO.IN, RPi.GPIO.PUD_UP)

		# collect data into an array
		data = self.__collect_input()

		# parse lengths of all data pull up periods
		pull_up_lengths = self.__parse_data_pull_up_lengths(data)

		# if bit count mismatch, return error (4 byte data + 1 byte checksum)
		if len(pull_up_lengths) != 40:
			#return DHT11Result(DHT11Result.ERR_MISSING_DATA, self.get_sensor_name(), 0, 0)
			return DHT11Result(self.get_sensor_name(), False, 0, 0)

		# calculate bits from lengths of the pull up periods
		bits = self.__calculate_bits(pull_up_lengths)

		# we have the bits, calculate bytes
		the_bytes = self.__bits_to_bytes(bits)

		# calculate checksum and check
		checksum = self.__calculate_checksum(the_bytes)
		if the_bytes[4] != checksum:
			#return DHT11Result(DHT11Result.ERR_CRC, self.get_sensor_name(), 0, 0)
			return DHT11Result(self.get_sensor_name(), False, 0, 0)

		# ok, we have valid data, return it
		return DHT11Result(self.get_sensor_name(), True, the_bytes[2], the_bytes[0])

	def __send_and_sleep(self, output, sleep):
		RPi.GPIO.output(self.__pin, output)
		time.sleep(sleep)

	def __collect_input(self):
		# collect the data while unchanged found
		unchanged_count = 0

		# this is used to determine where is the end of the data
		max_unchanged_count = 100

		last = -1
		data = []
		while True:
			current = RPi.GPIO.input(self.__pin)
			data.append(current)
			if last != current:
				unchanged_count = 0
				last = current
			else:
				unchanged_count += 1
				if unchanged_count > max_unchanged_count:
					break

		return data

	def __parse_data_pull_up_lengths(self, data):
		STATE_INIT_PULL_DOWN = 1
		STATE_INIT_PULL_UP = 2
		STATE_DATA_FIRST_PULL_DOWN = 3
		STATE_DATA_PULL_UP = 4
		STATE_DATA_PULL_DOWN = 5

		state = STATE_INIT_PULL_DOWN

		lengths = [] # will contain the lengths of data pull up periods
		current_length = 0 # will contain the length of the previous period

		for i in range(len(data)):

			current = data[i]
			current_length += 1

			if state == STATE_INIT_PULL_DOWN:
				if current == RPi.GPIO.LOW:
					# ok, we got the initial pull down
					state = STATE_INIT_PULL_UP
			elif state == STATE_INIT_PULL_UP:
				if current == RPi.GPIO.HIGH:
					# ok, we got the initial pull up
					state = STATE_DATA_FIRST_PULL_DOWN
			elif state == STATE_DATA_FIRST_PULL_DOWN:
				if current == RPi.GPIO.LOW:
					# we have the initial pull down, the next will be the data pull up
					state = STATE_DATA_PULL_UP
			elif state == STATE_DATA_PULL_UP:
				if current == RPi.GPIO.HIGH:
					# data pulled up, the length of this pull up will determine whether it is 0 or 1
					current_length = 0
					state = STATE_DATA_PULL_DOWN
			elif state == STATE_DATA_PULL_DOWN:
				if current == RPi.GPIO.LOW:
					# pulled down, we store the length of the previous pull up period
					lengths.append(current_length)
					state = STATE_DATA_PULL_UP

		return lengths

	def __calculate_bits(self, pull_up_lengths):
		# find shortest and longest period
		shortest_pull_up = 1000
		longest_pull_up = 0

		for i in range(0, len(pull_up_lengths)):
			length = pull_up_lengths[i]
			if length < shortest_pull_up:
				shortest_pull_up = length
			if length > longest_pull_up:
				longest_pull_up = length

		# use the halfway to determine whether the period it is long or short
		halfway = shortest_pull_up + (longest_pull_up - shortest_pull_up) / 2
		bits = []

		for i in range(0, len(pull_up_lengths)):
			bit = False
			if pull_up_lengths[i] > halfway:
				bit = True
			bits.append(bit)

		return bits

	def __bits_to_bytes(self, bits):
		the_bytes = []
		byte = 0

		for i in range(0, len(bits)):
			byte = byte << 1
			if (bits[i]):
				byte = byte | 1
			else:
				byte = byte | 0
			if ((i + 1) % 8 == 0):
				the_bytes.append(byte)
				byte = 0

		return the_bytes

	def __calculate_checksum(self, the_bytes):
		return the_bytes[0] + the_bytes[1] + the_bytes[2] + the_bytes[3] & 255
		
	def get_sensor_type_name(self):
		return "DHT11"
		
	def get_sensor_name(self):
		return "DHT11_PIN%i" % self.__pin
		
	def get_sensor_fields(self):
		return ["temp", "hum"]
		
	def get_sensor_options(self):
		return (self.__pin,)
		
	@staticmethod
	def detect_sensors():
		sensors = list()
		for i in range(NUM_BCM_PINS):
			sensor = DHT11(i)
			res = sensor.read()
			if res.is_valid:
				sensors.append(sensor)
		return sensors

def get_sensors(*pins):
	return [DHT11(pin) for pin in pins]

if __name__ == "__main__":
	sensor = DHT11.detect_sensors()[0]
	result = sensor.read()
	print("valid:%r temperature:%i huminidty:%i" % (result.is_valid, result.temp, result.hum))
