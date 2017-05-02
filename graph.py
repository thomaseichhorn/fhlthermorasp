#!/usr/bin/env python3

ROOT_PATH = "/usr/lib/root"
NO_VALUE = -120 #value to use when the real value is not available

import sys
sys.path.append(ROOT_PATH)
from ROOT import gROOT, gStyle, TCanvas, TGraph, TGraphErrors, TImage, TH2F, TLegend

from array import array
from collections import defaultdict
from datetime import datetime
import numpy as np
from scipy.signal import savgol_filter

DATAFIELDS = {"": ("Graph", "", "Mean"),
	"temp": ("Temperature", "Temperature in C", "Mean temperature"),
	"hum": ("Humidity", "Humidity in %", "Mean humidity")}

#create an array of length  len and type type filled with value val
def array_val_len(val, len, type = "d"):
	a = array(type)
	a.fromlist([val]*len)
	return a
	
#convert a list to an array of type type
def list_to_array(l, type = "d"):
	a = array(type)
	a.fromlist(l)
	return a

def parse_hist(filename):
	data = defaultdict(lambda: array("d"))
	keys = list()
	f = open(filename)
	for line in f:
		line = line.strip()
		if line[0] == "#":
			keys = line[1:].split(" ")
		else:
			line = line.split(" ")
			for index, key in enumerate(keys):
				if key == "date" or key == "time":
					continue
				if index < len(line):
					try:
						value = float(line[index])
					except ValueError:
						value = NO_VALUE
				else:
					value = NO_VALUE
				data[key].append(value)
					
			#parse timestamps
			if "date" in keys and "time" in keys:	
				date_idx = keys.index("date")
				time_idx = keys.index("time")
				date_str = "%sT%s" % (line[date_idx], line[time_idx])
				try:
					ts = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f").timestamp()
				except ValueError:
					ts = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").timestamp()
				data["timestamp"].append(ts)
	return data
	
def find_stray_samples(x, min_diff, max_len = 10):
	t = np.where(abs(np.diff(x)) > min_diff)[0] + 1
	t_near = np.diff(t) <= max_len
	
	#remove points that do not have a partner within max_len
	t2 = np.array([], dtype=int)
	i = 0
	while i < len(t_near):
		if t_near[i]:
			t2 = np.append(t2, [t[i], t[i+1]])
			i += 2
		else:
			i += 1
	
	#make slices from point pairs
	t2 = t2.reshape(len(t2) // 2, 2)
	slices = list()
	for ival in t2:
		slices.append(np.s_[ival[0]:ival[1]])
	return slices
	
def replace_stray_samples(x, min_diff):
	#replace missing values
	for i, value in enumerate(x):
		if value == NO_VALUE:
			x[i] = x[i-1]	
	
	slices = find_stray_samples(x, min_diff)
	for s in slices:
		x[s] = array_val_len(x[s.start-1], s.stop - s.start)
	
	return x
	
def find_constant_intervals(x, min_len, max_diff):
	intervals = list()
	for start_pos, sample in enumerate(x[:-1]):
		for j, sample2 in enumerate(x[start_pos + 1:]):
			if abs(sample2 - sample) > max_diff:
				break
		end_pos = start_pos + j + 1
		if end_pos - start_pos < min_len:
			continue
		intervals.append((start_pos, end_pos))
	if len(intervals) <= 1:
		return intervals
	
	#filter out overlapping intervals. Keep the largest
	intervals_clear = intervals.copy()
	last_ival = intervals[0]
	for ival in intervals[1:]:
		if ival[0] < last_ival[1]:
			if ival[1] - ival[0] < last_ival[1] - last_ival[0]:
				intervals_clear.remove(ival)
			else:
				intervals_clear.remove(last_ival)
				last_ival = ival
		else:
			last_ival = ival
	if len(intervals_clear) <= 1:
		return intervals_clear
	return intervals_clear
	
	
	#merge touching intervals
	intervals = intervals_clear.copy()
	last_ival = intervals[0]
	for ival in intervals[1:]:
		if ival[0] == last_ival[1]:
			new_ival = (last_ival[0], ival[1])
			intervals_clear[intervals_clear.index(last_ival)] = new_ival
			intervals_clear.remove(ival)
			last_ival = new_ival
		else:
			last_ival = ival
	return intervals_clear
	
def smooth(y, box_pts):
    box = np.ones(box_pts) / box_pts
    y_smooth = np.convolve(y, box, mode="same")
    return y_smooth
			
	
def date_from_pos(data, pos):
	dates = list()
	for p in pos:
		dates.append(str(datetime.fromtimestamp(data["timestamp"][p])))
	return dates
	
if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("Usage: %s <filename>" % sys.argv[0])
		sys.exit()
	
	data = parse_hist(sys.argv[1])

	sensors = list(set(data.keys()) - {"date", "time", "timestamp"})
	sensors.sort()
	n = len(data["timestamp"])
	if len(sensors) == 0:
		print("No sensors found. Line with sensor names missing?")
		sys.exit()
	print("Got %i samples per sensor." % (n,))
	print("Available sensors:")
	for i, sensor in enumerate(sensors):
		print("(%i): %s" % (i, sensor))
	selected_keys = list(filter(None, input("Sensors to display (comma separated): ").split(",")))
	if len(selected_keys) == 0:
		print("No sensors selected.")
		exit()
	selected_keysp = list()
	for key in selected_keys:
		if not key in sensors:
			try:
				key = sensors[int(key)]
			except ValueError:
				print("No such sensor \"%s\"." % (key,))
				sys.exit()
			except IndexError:
				print("Sensor index out of range.")
				sys.exit()
		selected_keysp.append(key)
		
	for key in selected_keysp:
		print("Got %i samples for sensor %s." % (len(data[key]) - data[key].count(NO_VALUE), key))
	
	gROOT.Reset()
	gStyle.SetCanvasPreferGL(True)
	field = DATAFIELDS[""]
	for key in selected_keysp:
		if key.rsplit("_", 1)[-1] in DATAFIELDS:
			field = DATAFIELDS[key.rsplit("_", 1)[-1]]
			break
	c1 = TCanvas("c1", field[0], 200, 10, 700, 500)
	leg1 = TLegend(0.1, 0.9-0.03*len(selected_keysp), 0.3, 0.9)
	#c1_h1 = TH2F("c1_h1", "Graph", 10, np.min(data["timestamp"]), np.max(data["timestamp"]), 10, -10, 35)
	#c1_h1.SetStats(False)
	#c1_h1.Draw()
	
	line_graphs = list()
	for key in selected_keysp:
		print("Replacing errors...")
		replace_stray_samples(data[key], 2)
		print("Plotting...")
		g1 = TGraph(n, data["timestamp"], data[key])
		x_axis = g1.GetXaxis()
		x_axis.SetTimeDisplay(1)
		x_axis.SetTitle("Time")
		y_axis = g1.GetYaxis()
		y_axis.SetRangeUser(-10, 40)
		y_axis.SetTitle(field[1])
		x_axis.SetTimeFormat("%H:%M:%S")
		g1.SetMarkerColor(2)
		g1.SetLineColor(len(line_graphs) + 2)
		g1.SetEditable(False)
		g1.Draw("AL" if len(line_graphs) == 0 else "L")
		#g1.Draw("L")
		line_graphs.append(g1)
		leg1.AddEntry(g1, key)
	
		c1.Update()
		leg1.Draw()
		
	if len(selected_keysp) > 1:
		data_of_interest = np.array([data[key] for key in selected_keysp])
		#data_diff = np.abs(data_of_interest.max(0) - data_of_interest.min(0))
		data_std = data_of_interest.std(0)
		data_mean = data_of_interest.mean(0)
		
		print("Computing extrema...")
		#Smooth the data so that extrema are easily detectable
		smoothed = smooth(data_mean, n//5)
		pos_min = (np.diff(np.sign(np.diff(smoothed))) > 0).nonzero()[0] + 1
		pos_max = (np.diff(np.sign(np.diff(smoothed))) < 0).nonzero()[0] + 1
		pos_extrema = np.sort(np.concatenate((pos_min, pos_max)))
		pos_extrema = np.insert(pos_extrema, 0, 0)
		pos_extrema = np.append(pos_extrema, len(smoothed)-1)
		extrema = list()
		for i, length in enumerate(np.diff(pos_extrema)):
			#Filter out extrema that are very close to one another
			if length > 10:
				extrema.append((int(pos_extrema[i+1]), pos_extrema[i+1] in pos_max))
		
		print("Plotting...")
		c_diff = TCanvas("c_diff", "Differences", 200, 10, 700, 500)
		c_diff_hist = TH2F("h1", "Deviation", 10, -10, 30, 10, 0, 3)
		c_diff_hist.SetStats(False)
		c_diff_hist.Draw()
		
		diff_graphs = list()
		prev_pos = 0
		for pos_extremum, is_maximum in extrema:
			g_diff = TGraph(pos_extremum - prev_pos, data_mean[prev_pos:pos_extremum], data_std[prev_pos:pos_extremum])
			g_diff.SetTitle("Deviation")
			x_axis = g_diff.GetXaxis()
			#x_axis.SetTimeDisplay(1)
			#x_axis.SetTitle("Time")
			#x_axis.SetTimeFormat("%H:%M:%S")
			x_axis.SetTitle(field[2])
			x_axis.SetRangeUser(-10, 40)
			y_axis = g_diff.GetYaxis()
			y_axis.SetRangeUser(0, 3)
			y_axis.SetTitle("Deviation")
			g_diff.SetLineColor(2 if is_maximum else 4)
			g_diff.SetEditable(False)
			g_diff.Draw("L")
			c_diff.Update()
			prev_pos = pos_extremum
			diff_graphs.append(g_diff)
		leg_diff = TLegend(0.1, 0.8, 0.3, 0.9)
		legend_has_inc = False
		legend_has_dec = False
		for graph in diff_graphs:
			if not legend_has_inc and graph.GetLineColor() == 2:
				leg_diff.AddEntry(graph, "Increasing Temp")
				legend_has_inc = True
			elif not legend_has_dec and graph.GetLineColor() != 2:
				leg_diff.AddEntry(graph, "Decreasing Temp")
				legend_has_dec = True
		leg_diff.Draw()
		c_diff.Update()
	
	answer = input("Search for constant intervals? ")
	if len(answer) > 0 and answer.lower()[0] == "y":
		if str(type(c1)) == "<class 'PyROOT_NoneType'>":
			print("Canvas was closed.")
			sys.exit()
		interval_mean = list()
		interval_std = list()
		interval_inc = list()
		
		error_graphs = list()
		for key in selected_keysp:
			print("Searching constant intervals...")
			const_intervals = find_constant_intervals(data[key], 50, 0.3)

			print("Plotting...")
			g4 = TGraphErrors(len(const_intervals))
			last_mean = NO_VALUE
			print("Mean±STD Interval_width(seconds) Interval_width(samples)")
			for i, ival in enumerate(const_intervals):
				part = data[key][ival[0]:ival[1]]
				ex = (data["timestamp"][ival[1]] - data["timestamp"][ival[0]]) / 2
				x = data["timestamp"][ival[0]] + ex
				y = np.mean(part)
				ey = np.std(part)
				print("%.3f±%.3f %.3f %i" % (y, ey, ex, ival[1]-ival[0]))
				g4.SetPoint(i, x, y)
				g4.SetPointError(i, ex, ey)
				interval_mean.append(y)
				interval_std.append(ey)
				interval_inc.append(last_mean < y)
				last_mean = y

			g4.SetEditable(False)
			g4.SetMarkerColor(4)
			g4.SetMarkerStyle(21)
			g4.Draw("P")
			error_graphs.append(g4)

			c1.Update()
		
		if len(interval_std) > 0:
			print("Mean of all STD values: %0.3f" % (np.mean(interval_std)))

		#img = TImage.Create()
		#img.FromPad(c1)
		#img.WriteImage("canvas.png")

		#sort the interval values according to their mean values
		interval_std = [y for (x,y) in sorted(zip(interval_mean, interval_std), key = lambda pair: pair[0])]
		interval_inc = [y for (x,y) in sorted(zip(interval_mean, interval_inc), key = lambda pair: pair[0])]
		interval_mean.sort()
		c2 = TCanvas("c2", "Mean and deviantion", 200, 10, 700, 500)
		n_points = interval_inc.count(True)
		if n_points != 0:
			g5 = TGraph(n_points)
			g5.SetName("g5")
			g5.SetTitle("Deviation over constant intervals")
			g5.SetMarkerColor(2)
			g5.SetMarkerStyle(21)
			g5.SetEditable(False)
		
		n_points = interval_inc.count(False)
		if n_points != 0:
			g6 = TGraph(n_points)
			g6.SetName("g6")
			g6.SetTitle("Deviation over constant intervals")
			g6.SetMarkerColor(4)
			g6.SetMarkerStyle(21)
			g6.SetEditable(False)
			
		i, j = 0, 0
		for ival_mean, ival_std, ival_inc in zip(interval_mean, interval_std, interval_inc):
			if ival_inc:
				g5.SetPoint(i, ival_mean, ival_std)
				i += 1
			else:
				g6.SetPoint(j, ival_mean, ival_std)
				j += 1
				
		leg2 = TLegend(0.1, 0.8, 0.3, 0.9)
		if i > 0:
			g5.Draw("AP")
			g5.GetXaxis().SetTitle(field[2])
			g5.GetYaxis().SetTitle("Standard deviation")
			leg2.AddEntry(g5, "Increasing Temp")
		if j > 0:
			g6.Draw("P")
			g6.GetXaxis().SetTitle(field[2])
			g6.GetYaxis().SetTitle("Standard deviation")
			leg2.AddEntry(g6, "Decreasing Temp")

		leg2.Draw()
		
		c2.Update()
input("Press enter to exit.")
