#!/usr/bin/env python3

import subprocess as sproc
from os.path import isdir, join, exists
from os import makedirs, rename
import datetime
from time import sleep

CAM_WIDTH = 640
CAM_HEIGHT = 480
IMAGE_QUALITY = 70
INTERVAL = 10.0

def get_timestamp():
	return datetime.datetime.now().isoformat()
def make_shot():
	args = ["fswebcam",
		"-r", "%ix%i" % (CAM_WIDTH, CAM_HEIGHT),
		"--jpeg", "%i" % IMAGE_QUALITY,
		"-"]
	proc = sproc.Popen(args, stdout=sproc.PIPE, stderr=sproc.PIPE)
	data, errs = proc.communicate()
	#print(errs.decode())
	return data
def save_image(directory, image):
	cur_path = join(directory, "image.jpg")
	cur_path_tmp = join(directory, "image_tmp.jpg")
	hist_path = join(directory, "history")
	
	with open(cur_path_tmp, "wb") as f:
		f.write(image)
	rename(cur_path_tmp, cur_path)
	
	if not exists(hist_path):
		makedirs(hist_path)
	with open(join(hist_path, get_timestamp() + ".jpg"), "wb") as f:
		f.write(image)

if __name__ == "__main__":
	from sys import argv, exit
	
	if len(argv) < 2:
		exit("Please input a directory to save images to.")
	if not isdir(argv[1]):
		exit("Not a directory: %s" % argv[1])
	while True:
		data = make_shot()
		if len(data) == 0:
			print("%s Could not get image." % get_timestamp())
			sleep(2)
			continue
		save_image(argv[1], data)
		sleep(INTERVAL)
