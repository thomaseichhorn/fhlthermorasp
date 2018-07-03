#!/usr/bin/env python3

import socket
from sys import argv, exit
from os.path import isfile
import signal

HOST = ""
PORT = 50007

finish = False
def signal_handler(signum, frame):
	global finish
	finish = True
#Handle stop process siginal
signal.signal(signal.SIGINT, signal_handler)

if len(argv) < 2:
	exit("Please input a file path.")
if not isfile(argv[1]):
	exit("Not a file: %s" % argv[1])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((HOST, PORT))
	print("Listening on port %i" % PORT)
	s.listen(10)
	while not finish:
		conn, addr = s.accept()
		print("Got connection from %s:%i" % addr)
		with conn:
			try:
				f = open(argv[1], "rb")
				data = f.read()
				f.close()
				conn.sendall(data)
			except IOError:
				conn.sendall("Error reading file.")
