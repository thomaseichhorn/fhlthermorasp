#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

import datetime
import os
import os.path
import threading
import time
import enum
import json
from math import isnan

import sensor_monitor
from w1_temp import W1TempSensor
from sht21 import SHT21
from dht11 import DHT11
from bme280 import BME280
from sht75 import SHT75
from bme680 import BME680

def show_warning(parent, message):
	warnDialog = Gtk.MessageDialog(parent=parent,
		flags=Gtk.DialogFlags.MODAL,
		type=Gtk.MessageType.WARNING,
		buttons=Gtk.ButtonsType.OK,
		message_format="Warning: %s" % (message,))
	warnDialog.run()
	warnDialog.destroy()

	
def show_error(parent, message):
	errDialog = Gtk.MessageDialog(parent=parent,
		flags=Gtk.DialogFlags.MODAL,
		type=Gtk.MessageType.ERROR,
		buttons=Gtk.ButtonsType.OK,
		message_format="Error: %s" % (message,))
	errDialog.run()
	errDialog.destroy()


class SensorAddDialog(Gtk.Dialog):
	class SensorOptionTypes(enum.Enum):
		TEXT = 1
		NAT_NUM = 2
		PIN = 3
	
	KNOWN_SENSORS = {
		#Name: [Module, [(OptionName, OptionType, DisableWhenDetect)]]
		"W1Temp": (W1TempSensor, [("Name", SensorOptionTypes.TEXT, True)]),
#		"SHT21": (SHT21, [("SCL pin", SensorOptionTypes.PIN, True),
#			("SDA pin", SensorOptionTypes.PIN, True)]),
		"SHT21": (SHT21, [("I²C bus", SensorOptionTypes.NAT_NUM, True),
			("I²C address (decimal!)", SensorOptionTypes.NAT_NUM, True)]),
		"DHT11": (DHT11, [("Pin", SensorOptionTypes.PIN, True)]),
		"BME280": (BME280, [("I²C bus", SensorOptionTypes.NAT_NUM, True),
			("I²C address (decimal!)", SensorOptionTypes.NAT_NUM, True)]),
		"SHT75": (SHT75, [("SCL pin", SensorOptionTypes.PIN, True),
			("SDA pin", SensorOptionTypes.PIN, True)]),
		"BME680": (BME680, [("I²C bus", SensorOptionTypes.NAT_NUM, True),
			("I²C address (decimal!)", SensorOptionTypes.NAT_NUM, True)])
	}
	
	def __init__(self, parent):
		Gtk.Dialog.__init__(self, "Add a sensor", parent, 0,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
				Gtk.STOCK_OK, Gtk.ResponseType.OK),
			flags=Gtk.DialogFlags.MODAL)
				
		self.set_default_size(150, 100)
		box = self.get_content_area()
		
		self._typebox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		box.pack_start(self._typebox, True, False, 0)
		self._typelabel = Gtk.Label("Type: ")
		self._typebox.pack_start(self._typelabel, False, False, 0)
		self._typecombo = Gtk.ComboBoxText()
		for sensor_name, sensor_info in self.KNOWN_SENSORS.items():
			self._typecombo.append_text(sensor_name)
		self._typecombo.connect("changed", self._on_type_changed)
		self._typebox.pack_start(self._typecombo, True, True, 0)
		
		self._optionsbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
		box.pack_start(self._optionsbox, True, False, 3)
		self._option_entries = list()
		
		self._typecombo.set_active(0)
		self.show_all()
		
	def _on_type_changed(self, combobox):
		self._setup_optionsbox()
	
	def _setup_optionsbox(self):
		children = self._optionsbox.get_children()
		for child in children:
			self._optionsbox.remove(child)
		self._option_entries.clear()
			
		detect_button = Gtk.CheckButton("Auto-detect")
		detect_button.connect("toggled", self._on_detect_button_toggled)
		detect_button.set_active(True)
		self._detect_button = detect_button
		self._optionsbox.pack_start(detect_button, False, False, 0)
			
		sensor_name = self._typecombo.get_active_text()
		options = self.KNOWN_SENSORS[sensor_name][1]
		for option in options:
			optionbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
			self._optionsbox.pack_start(optionbox, False, False, 0)
			
			label = Gtk.Label(option[0] + ": ")
			optionbox.pack_start(label, False, False, 0)
			if option[1] == self.SensorOptionTypes.TEXT:
				entry = Gtk.Entry()
			elif option[1] == self.SensorOptionTypes.NAT_NUM:
				entry = Gtk.SpinButton()
				entry.set_numeric(True)
				adjustment = Gtk.Adjustment(0, 0, 99999, 1, 10, 0)
				entry.set_adjustment(adjustment)
				entry.set_value(1)
			elif option[1] == self.SensorOptionTypes.PIN:
				entry = Gtk.SpinButton()
				entry.set_numeric(True)
				adjustment = Gtk.Adjustment(0, 0, 27, 1, 10, 0)
				entry.set_adjustment(adjustment)
				entry.set_value(0)
			optionbox.pack_start(entry, True, False, 0)
			self._option_entries.append(entry)
			if option[2]:
				entry.set_sensitive(False)
			
		self.show_all()
		
	def _on_detect_button_toggled(self, button):
		sensor_name = self._typecombo.get_active_text()
		options = self.KNOWN_SENSORS[sensor_name][1]
		for i, entry in enumerate(self._option_entries):
			if options[i][2] and button.get_active():
				entry.set_sensitive(False)
			else:
				entry.set_sensitive(True)
				
	def get_sensors(self):
		sensor_name = self._typecombo.get_active_text()
		sensor_class, sensor_options = self.KNOWN_SENSORS[sensor_name]
		if self._detect_button.get_active():
			return sensor_class.detect_sensors()
		else:
			known_opt = self.KNOWN_SENSORS[sensor_name][1]
			options = list()
			for i, entry in enumerate(self._option_entries):
				option_type = known_opt[i][1]
				if option_type == self.SensorOptionTypes.TEXT:
					options.append(entry.get_text())
				elif option_type == self.SensorOptionTypes.PIN:
					options.append(entry.get_value_as_int())
		
			return [sensor_class(*options)]


class SensorView(Gtk.Box):
	__gsignals__ = {
		"sensor-added": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
		"sensor-removed": (GObject.SIGNAL_RUN_FIRST, None, (object,))
	}
	
	def __init__(self):
		Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=2)
		
		self._treeviewscroll = Gtk.ScrolledWindow()
		self._treeviewscroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self.pack_start(self._treeviewscroll, True, True, 0)
		model = Gtk.ListStore(str, str, str)
		self._treeview = Gtk.TreeView(model)
		self._treeview.connect("cursor-changed", self._on_treeview_cursor)
		self._treeviewscroll.add(self._treeview)
		
		for i, title in enumerate(["Type", "Name", "Fields"]):
			renderer = Gtk.CellRendererText()
			column = Gtk.TreeViewColumn(title, renderer, text=i)
			self._treeview.append_column(column)
			
		self._button_box = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
		self.pack_start(self._button_box, False, False, 0)
		
		self._add_button = Gtk.Button("Add...")
		self._add_button.connect("clicked", self._on_add_clicked)
		self._button_box.pack_start(self._add_button, True, True, 0)
		self._count_label = Gtk.Label("0 sensors")
		self._button_box.pack_start(self._count_label, False, False, 0)
		self._remove_button = Gtk.Button("Remove")
		self._remove_button.set_sensitive(False)
		self._remove_button.connect("clicked", self._on_remove_clicked)
		self._button_box.pack_start(self._remove_button, True, True, 0)
		
		self._sensors = list()
		self._changes_allowed = True
		
	def _on_treeview_cursor(self, tree_view):
		if not self._changes_allowed:
			self._remove_button.set_sensitive(False)
		else:
			selection = self._treeview.get_selection()
			model, selected = selection.get_selected()
			if selected is None:
				self._remove_button.set_sensitive(False)
			else:
				self._remove_button.set_sensitive(True)

	def _on_add_clicked(self, button):
		top = self.get_toplevel()
		dialog = SensorAddDialog(top)
		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			try:
				sensors = dialog.get_sensors()
			except ValueError as e:
				dialog.destroy()
				show_error(top, e.args[0])
			else:
				dialog.destroy()
				known_sensor_names = [sensor.get_sensor_name() for sensor in self._sensors]
				duplicates = False
				for sensor in sensors:
					if sensor.get_sensor_name() in known_sensor_names:
						duplicates = True
						continue
					self.add_sensor(sensor)
				if len(sensors) == 0:
					show_warning(top, "No sensors could be added.")
				elif duplicates:
					if len(sensors) == 1:
						show_warning(top, "Sensor was already added.")
					else:
						show_warning(top, "Some sensors were already added.")
		else:
			dialog.destroy()
		
	def _on_remove_clicked(self, button):
		selection = self._treeview.get_selection()
		model, selected = selection.get_selected()
		index = model.get_path(selected).get_indices()[0]
		model.remove(selected)
		sensor = self._sensors.pop(index)
		self._update_count_label()
		self.emit("sensor-removed", sensor)
		
	def _update_count_label(self):
		num_sensors = len(self._sensors)
		if num_sensors == 1:
			self._count_label.set_text("1 sensor")
		else:
			self._count_label.set_text("%i sensors" % (num_sensors,))
		
	def add_sensor(self, sensor):
		model = self._treeview.get_model()
		model.append([sensor.get_sensor_type_name(),
			sensor.get_sensor_name(),
			", ".join(sensor.get_sensor_fields())])
		self._sensors.append(sensor)
		self._update_count_label()
		self.emit("sensor-added", sensor)
		
	def get_sensors(self):
		return self._sensors.copy()
		
	def allow_changes(self, allow):
		self._changes_allowed = allow
		self._add_button.set_sensitive(allow)
		
		selection = self._treeview.get_selection()
		model, selected = selection.get_selected()
		if not selected is None:
			self._remove_button.set_sensitive(allow)
		else:
			self._remove_button.set_sensitive(False)
			
class LimitsBox(Gtk.Box):
	__gsignals__ = {
		"limit-changed": (GObject.SIGNAL_RUN_FIRST, None, (str, float, float))
	}
	
	def __init__(self, desc, field_name):
		Gtk.Box.__init__(self, orientation = Gtk.Orientation.HORIZONTAL)
		
		self._label = Gtk.Label("%s limits: " % (desc,))
		self.pack_start(self._label, False, False, 0)
		
		self._enable_button = Gtk.CheckButton("Enable")
		self._enable_button.connect("toggled", self._on_enable_button_toggled)
		self._enable_button.set_active(False)
		self.pack_start(self._enable_button, False, False, 0)
		
		adjustment = Gtk.Adjustment(0, -273, 273, 1, 10, 0)
		self._limit1_button = Gtk.SpinButton(adjustment = adjustment)
		self._limit1_button.set_numeric(True)
		self._limit1_button.set_sensitive(False)
		self._limit1_button.connect("value-changed", self._on_limit_changed)
		self.pack_start(self._limit1_button, True, True, 3)
		
		adjustment = Gtk.Adjustment(0, -273, 273, 1, 10, 0)
		self._limit2_button = Gtk.SpinButton(adjustment = adjustment)
		self._limit2_button.set_numeric(True)
		self._limit2_button.set_sensitive(False)
		self._limit2_button.connect("value-changed", self._on_limit_changed)
		self.pack_start(self._limit2_button, True, True, 3)
		
		self.field_name = field_name
		
	def _on_enable_button_toggled(self, button):
		self._limit1_button.set_sensitive(button.get_active())
		self._limit2_button.set_sensitive(button.get_active())
		self._emit_changed()
		
	def _on_limit_changed(self, spinbutton):
		self._emit_changed()
		
	def _emit_changed(self):
		if self._enable_button.get_active():
			limit1 = self._limit1_button.get_value()
			limit2 = self._limit2_button.get_value()
		else:
			limit1 = limit2 = float("nan")
		self.emit("limit-changed", self.field_name, limit1, limit2)
		
	def set_limits(self, limit1, limit2):
		if limit1 is None or isnan(limit1):
			self._enable_button.set_active(False)
		else:
			self._limit1_button.set_value(limit1)
			self._limit2_button.set_value(limit2)
			self._enable_button.set_active(True)


class LogWindow(Gtk.ScrolledWindow):
	ts_format = "%Y-%m-%d %H:%M:%S"
	
	def __init__(self):
		Gtk.ScrolledWindow.__init__(self)
		self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._view = Gtk.TextView()
		self._view.set_editable(False)
		self.add(self._view)
		
	def add_message(self, text, show_ts = True):
		if show_ts:
			timestamp = datetime.datetime.now().strftime(self.ts_format)
			line = "[%s] %s" % (timestamp, text)
		else:
			line = "%s" % (text,)
		buf = self._view.get_buffer()
		end = buf.get_end_iter()
		buf.insert(end, line + "\n")
		self.scroll_bottom()
		print(line)
		
	def scroll_bottom(self):
		adj = self.get_vadjustment()
		adj.set_value(adj.get_upper() - adj.get_page_size())
		self.set_vadjustment(adj)
		

class SensorMonitorWindow(Gtk.Window):
	__gsignals__ = {
		"measurement_taken": (GObject.SIGNAL_RUN_FIRST, None, (str,))
	}

	def __init__(self, config_file_path = "sensor_monitor_settings.json"):
		Gtk.Window.__init__(self, title="Sensor Monitor")
		self.set_border_width(10)
		self.set_default_size(400, 500)
		
		self._main_box = Gtk.Box(orientation = Gtk.Orientation.VERTICAL, spacing = 5)
		self.add(self._main_box)
		
		self._sensorview = SensorView()
		self._sensorview.connect("sensor-added", self._on_sensor_added)
		self._sensorview.connect("sensor-removed", self._on_sensor_removed)
		self._main_box.pack_start(self._sensorview, True, True, 0)
		
		self._interval_box = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)
		self._main_box.pack_start(self._interval_box, False, False, 0)
		self._interval_label = Gtk.Label("Interval: ")
		self._interval_box.pack_start(self._interval_label, False, False, 0)
		adjustment = Gtk.Adjustment(10, 0, 9999, 1, 10, 0)
		self._interval_spin = Gtk.SpinButton(adjustment = adjustment)
		self._interval_spin.set_numeric(True)
		self._interval_spin.set_value(10)
		self._interval_box.pack_start(self._interval_spin, True, True, 0)
		
		self._tempbox = LimitsBox("Temperature", "temp")
		self._tempbox.connect("limit-changed", self._on_limit_changed)
		self._main_box.pack_start(self._tempbox, False, False, 0)
		
		self._humbox = LimitsBox("Humidity", "hum")
		self._humbox.connect("limit-changed", self._on_limit_changed)
		self._main_box.pack_start(self._humbox, False, False, 0)
		
		self._presbox = LimitsBox("Pressure", "pres")
		self._presbox.connect("limit-changed", self._on_limit_changed)
		self._main_box.pack_start(self._presbox, False, False, 0)
		
		self._alarmnum_box = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)
		self._main_box.pack_start(self._alarmnum_box, False, False, 0)
		self._alarmnum_label = Gtk.Label("Ring alarm after ")
		self._alarmnum_box.pack_start(self._alarmnum_label, False, False, 0)
		adjustment = Gtk.Adjustment(1, 1, 100, 1, 10, 0)
		self._alarmnum_spin = Gtk.SpinButton(adjustment = adjustment)
		self._alarmnum_spin.set_numeric(True)
		self._alarmnum_spin.set_value(1)
		self._alarmnum_spin.connect("value-changed", self._on_alarmnum_changed)
		self._alarmnum_box.pack_start(self._alarmnum_spin, True, True, 0)
		
		self._directory_box = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)
		self._main_box.pack_start(self._directory_box, False, False, 0)
		self._directory_label = Gtk.Label("Output directory: ")
		self._directory_box.pack_start(self._directory_label, False, False, 0)
		self._directory_button = Gtk.FileChooserButton()
		self._directory_button.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
		self._directory_button.connect("file-set", self._on_directory_set)
		directory_path = os.getcwd()
		self._directory_button.set_filename(directory_path)
		self._directory_box.pack_start(self._directory_button, True, True, 0)
		
		self._start_button = Gtk.Button("Start measuring")
		self._start_button.connect("clicked", self._on_start_clicked)
		self._main_box.pack_start(self._start_button, False, False, 0)
		
		self._log_window = LogWindow()
		self._log_window.set_size_request(-1, 100)
		self._main_box.pack_start(self._log_window, False, False, 0)
		
		self.show_all()
		
		self._monitor = sensor_monitor.SensorMonitor(dict(),
			os.path.join(directory_path, "readings.txt"),
			os.path.join(directory_path, "readings_log.txt"),
			alarm_number = 1)
		self._meas_running = False
		self._meas_thread = False
		self._config_file = config_file_path
		
		self.load_options()
		self.add_log_message("Sensor GUI started.")
		GObject.idle_add(self._log_window.scroll_bottom)
		
	def _on_sensor_added(self, view, sensor):
		self.add_log_message("Added sensor '%s'." % (sensor.get_sensor_name(),))
		self._monitor.add_sensor(sensor)
		
	def _on_sensor_removed(self, view, sensor):
		self.add_log_message("Removed sensor '%s'." % (sensor.get_sensor_name(),))
		self._monitor.remove_sensor(sensor)
		
	def _on_limit_changed(self, limitbox, field_name, limit1, limit2):
		if limit1 is None or isnan(limit1):
			self._monitor.unset_alarm_for(field_name)
		else:
			self._monitor.set_alarm_limits(field_name, limit1, limit2)
			
	def _on_alarmnum_changed(self, spinbutton):
		self._monitor.set_alarm_number(self._alarmnum_spin.get_value_as_int())
		
	def _on_start_clicked(self, widget):
		if not self._meas_running:
			self.start_measurements()
			self._interval_box.set_sensitive(False)
			self._directory_box.set_sensitive(False)
			self._sensorview.allow_changes(False)
			self._tempbox.set_sensitive(False)
			self._humbox.set_sensitive(False)
			self._presbox.set_sensitive(False)
			self._alarmnum_box.set_sensitive(False)
			self._start_button.set_label("Stop measuring")
		else:
			self.stop_measurements()
			self._interval_box.set_sensitive(True)
			self._directory_box.set_sensitive(True)
			self._sensorview.allow_changes(True)
			self._tempbox.set_sensitive(True)
			self._humbox.set_sensitive(True)
			self._presbox.set_sensitive(True)
			self._alarmnum_box.set_sensitive(True)
			self._start_button.set_label("Start measuring")
		
	def _on_directory_set(self, file_chooser_button):
		path = file_chooser_button.get_filename()
		readings_path = os.path.join(path, "readings.txt")
		try:
			open(readings_path, "w")
		except PermissionError:
			show_error(self, "No permission to write to the chosen output directory.")
			path = os.getcwd()
			readings_path = os.path.join(path, "readings.txt")
		readings_log_path = os.path.join(path, "readings_log.txt")
		self._monitor.set_readings_path(readings_path)
		self._monitor.set_readings_log_path(readings_log_path)
		
	def do_measurement_taken(self, line):
		GObject.idle_add(self.add_log_message, line, False)

	def add_log_message(self, text, show_ts = True):
		self._log_window.add_message(text, show_ts)
		
	def start_measurements(self):
		self._meas_running = True
		if self._meas_thread and self._meas_thread.is_alive():
			return
		self.save_options()
			
		interval = self._interval_spin.get_value_as_int()
		log_fields = self._monitor.save_log_fields()
		self._meas_thread = threading.Thread(target=self.take_measurements, args=(interval,), daemon=True)
		self._meas_thread.start()
		self.add_log_message("Started measuring with interval %i." % (interval,))
		self.add_log_message(log_fields, False)
		
	def stop_measurements(self):
		self._meas_running = False
		if not self._meas_thread or not self._meas_thread.is_alive():
			return
		self._monitor.abort()
		self._meas_thread.join()
		self.add_log_message("Stopped measuring.")
		
	def take_measurements(self, interval):
		while self._meas_running:
			next_measurement_time = time.time() + interval
			readings = self._monitor.get_readings()
			line = self._monitor.save_readings(datetime.datetime.now(), readings)
			self.emit("measurement_taken", line)
			while time.time() < next_measurement_time and self._meas_running:
				time.sleep(0.1)
				
	def save_options(self, save_path = None):
		if save_path is None:
			save_path = self._config_file
		options = self._monitor.get_options()
		options["interval"] = self._interval_spin.get_value_as_int()
		
		try:
			fp = open(save_path, "w")
		except PermissionError:
			return
		json.dump(options, fp, indent=4)
		fp.close()
		
	def load_options(self, load_path = None):
		if load_path is None:
			load_path = os.path.join(os.getcwd(), self._config_file)
		if hasattr(json, "JSONDecodeError"):
			JSONDecodeError = json.JSONDecodeError #>=python3.5
		else:
			JSONDecodeError = ValueError #<python3.5
		
		try:
			options, sensors = self._monitor.set_options_from_file(load_path)
		except (OSError, PermissionError, FileNotFoundError):
			return
		except (JSONDecodeError, ValueError, TypeError, KeyError) as e:
			self.add_log_message("Contents of the options file are invalid: '%s': %s" % (os.path.basename(load_path), str(e)))
			show_warning(self, "Contents of the options file are invalid (see log).")
			return
		for sensor in sensors:
			self._sensorview.add_sensor(sensor)
		self._tempbox.set_limits(*self._monitor.get_alarm_limits("temp"))
		self._humbox.set_limits(*self._monitor.get_alarm_limits("hum"))
		self._presbox.set_limits(*self._monitor.get_alarm_limits("pres"))
		self._alarmnum_spin.set_value(self._monitor.get_alarm_number())
		if "interval" in options:
			self._interval_spin.set_value(options["interval"])
		

if __name__ == "__main__":
	from argparse import ArgumentParser
	
	parser = ArgumentParser(description="Monitor various sensors over time with GUI.")
	parser.add_argument("--config", "-c", type=str, help="A JSON config file to read configuration (enabled sensors etc.) from.")
	args = parser.parse_args()
	
	if not args.config is None:
		try:
			f = open(args.config)
			f.close()
		except (FileNotFoundError, PermissionError):
			print("Could not open config file.")
		win = SensorMonitorWindow(args.config)
	else:
		win = SensorMonitorWindow()
	win.connect("delete-event", Gtk.main_quit)
	Gtk.main()
