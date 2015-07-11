#!/usr/bin/env python
#  ERA.py
#  EVEOnline Ratting Assistant
#
#  AFK away and listen for a ding.
#
#  Written in python for you Alex....
#
# Copyright (c) 2015, QQHeresATissue <QQHeresATissue@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
###############################################################################

from time import gmtime
import time
from threading import *
import sys
from datetime import datetime, timedelta, date
import re
import json
import os
import platform
import logging
from utils import EVEDir
from universe import Universe
from intelmap import IntelMap
from settingsdialog import SettingsDialog

# Do initial checks, code taken from Pyfa... cause that shit rocks
if sys.version_info < (2,6) or sys.version_info > (3,0):
	print("ERA requires python 2.7\nExiting.")
	time.sleep(10)
	sys.exit(1)

	try:
		import wxversion
	except ImportError:
		print("Cannot find wxPython\nYou can download wxPython (2.8) from http://www.wxpython.org/")
		time.sleep(10)
		sys.exit(1)
	try:
		wxversion.select('2.8')
	except wxversion.VersionError:
		try:
			wxversion.ensureMinimal('2.8')
		except wxversion.VersionError:
			print("Installed wxPython version doesn't meet requirements.\nYou can download wxPython (2.8) from http://www.wxpython.org/")
			time.sleep(10)
			sys.exit(1)
		else:
			print("wxPython 2.8 not found; attempting to use newer version, expect errors")

import wx
import wx.media

# set a version
ver = "1.1.0b"

ID_HOSTILE_START = wx.NewId()
ID_LOOT_START = wx.NewId()

# Get current working direcroty
era_dir = os.path.dirname(__file__)

# Set wav names
hostile_sound = os.path.join( era_dir, "sounds", "hostile.wav")
done_sound = os.path.join( era_dir, "sounds", "sites_done.wav")
tags_and_ammo = os.path.join ( era_dir, "sounds", "cash_money.wav")

# Are we on windows or linux?
which_os = platform.system()

if which_os == "Windows":
	import winsound
	from winsound import PlaySound, SND_FILENAME

# Setup a class for text redirection
class RedirectText(object):
	def __init__(self,aWxTextCtrl):
		self.out=aWxTextCtrl

	# Write string to wx window
	def write(self,string):
		wx.CallAfter(self.out.AppendText, string)

# Main form for graphical ERA
class era(wx.Frame):

	def __init__(self,parent,id):

		# Create the main window with the title ERA <version number>
		#wx.Frame.__init__(self,parent,id,'ERA %s' % ver, size=(800,340), style = wx.DEFAULT_FRAME_STYLE & ~ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
		wx.Frame.__init__(self,parent,id,'ERA %s' % ver, size=(800,360), style = wx.DEFAULT_FRAME_STYLE)

		menubar = wx.MenuBar()
		fileMenu = wx.Menu()
		settingsMenu = wx.Menu()

		fitem = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit ERA')

		self.debug = settingsMenu.Append(wx.ID_ANY, 'Enable Debugging',
			'Enable Debugging', kind=wx.ITEM_CHECK)
		settingsMenu.Check(self.debug.GetId(), False)

		show_settings_menu = settingsMenu.Append(wx.ID_ANY, 'Settings')

		self.Bind(wx.EVT_MENU, self.Close, fitem)
		self.Bind(wx.EVT_MENU, self.toggle_debug, self.debug)
		self.Bind(wx.EVT_MENU, self.show_settings, show_settings_menu)

		menubar.Append(fileMenu, '&File')
		menubar.Append(settingsMenu, '&Settings')
		self.SetMenuBar(menubar)

		#self.toolbar = self.CreateToolBar()
		#self.toolbar.Realize()

		# Load settings
		dialog = SettingsDialog(self)
		era.settings = dialog.get_settings()
		dialog.Destroy()

		#
		self.Bind(wx.EVT_CLOSE, self.Close)

		# Create a panel in the windows
		self.panel = wx.Panel(self)

		input_sizer = wx.BoxSizer(wx.HORIZONTAL)

		# Setup logging early so we see it in the panel
		logbox = wx.TextCtrl(self.panel, wx.ID_ANY, size = (470, 360), style = wx.TE_MULTILINE | wx.TE_READONLY)

		# Redirect all printed messages to the panel
		redir = RedirectText(logbox)
		sys.stdout = redir
		sys.stderr = redir

		# Create a start and stop button for the loot watch
		self.loot_watch = wx.ToggleButton(self.panel, ID_LOOT_START, label="Loot Watch", size=(90,25))
		input_sizer.Add(self.loot_watch, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)

		# Define regions we have systems for in a list
		#region_list = [ 'dek', 'brn', 'ftn', 'fade', 'tnl', 'tri', 'vnl', 'vale', 'cr' ]
		region_list = [ 'dek' ]
		# Create text "Region" before the dropdown box
		input_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Region'), proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=8)

		# Create the dropdown box and use DEK as a default selection
		era.region_select = wx.ComboBox(self.panel, wx.ID_ANY, choices = region_list, style=wx.CB_DROPDOWN)
		era.region_select.SetSelection(0)
		input_sizer.Add(era.region_select, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)

		# Load triggers from json courtesty of Orestus, Narex Vivari for adding auto complete.
		era.universe = Universe(era_dir)
		era.universe.load()
		self.region_selection_changed(None)
		era.region_select.Bind(wx.EVT_COMBOBOX, self.region_selection_changed, era.region_select)

		# Create the system input box
		input_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'System'), proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=8)
		era.system_select = wx.TextCtrl(self.panel, wx.ID_ANY, '', size=(120,-1))
		era.system_select.Bind(wx.EVT_TEXT, self.system_text_changed, era.system_select)
		input_sizer.Add(era.system_select, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)

		# Create the range input box
		range_list = [ '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20' ]
		input_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Range'), proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=8)
		era.range_select = wx.ComboBox(self.panel, wx.ID_ANY, '', choices = range_list, style=wx.CB_DROPDOWN)
		era.range_select.SetSelection(15)
		input_sizer.Add(era.range_select, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)

		# Create a start and stop button for the hostile watch
		self.hostile_watch = wx.ToggleButton(self.panel, ID_HOSTILE_START, label="Hostile Watch", size=(95,25))
		input_sizer.Add(self.hostile_watch, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=4)

		# Bind button clicks to events (start|stop)
		self.Bind(wx.EVT_TOGGLEBUTTON, self.hostile_run, id=ID_HOSTILE_START)
		self.Bind(wx.EVT_TOGGLEBUTTON, self.loot_run, id=ID_LOOT_START)

		# Visual intel map
		era.intel_map = IntelMap(era.universe, self.panel, era.settings)

		# Main area layout
		main_sizer = wx.BoxSizer(wx.HORIZONTAL)
		main_sizer.Add(logbox, proportion=0, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=8)
		main_sizer.Add(era.intel_map.map_panel, proportion=1, flag=wx.EXPAND | wx.ALL, border=8)

		# App layout
		app_sizer = wx.BoxSizer(wx.VERTICAL)
		app_sizer.Add(input_sizer, proportion=0, flag=wx.TOP | wx.LEFT, border=8)
		app_sizer.Add(main_sizer, proportion=1, flag=wx.EXPAND | wx.LEFT, border=8)
		self.panel.SetSizer(app_sizer)

		# Set a watch variable to check later.  If we want the process to stop, self.watch becomes 1
		self.hostile_watcher = None
		self.loot_watcher = None

		self.timer = wx.Timer(self)

		# Shameless self adversiting
		print "EVEOnline Ratting Assistant v%s by QQHeresATissue" % ver

	def show_settings(self, event):
		size = wx.Size(300,260)
		pos = self.panel.ClientToScreen((0,0)) + (self.panel.Rect.Width / 2 - size.width / 2, self.panel.Rect.Height / 2 - size.height / 2)
		dialog = SettingsDialog(self, wx.ID_ANY, 'Settings', size=size, pos=pos)
		res = dialog.ShowModal()
		if res == wx.ID_OK:
			era.settings = dialog.get_settings()
			self.intel_map.update_settings(era.settings)
		dialog.Destroy()

	def region_selection_changed(self, event):
		era.universe.change_region(era.universe.region_short_name_to_id(era.region_select.GetValue()))

	def system_text_changed(self, event):
		if which_os == "Linux":
			caret = era.system_select.GetInsertionPoint() + 1
		else:
			caret = era.system_select.GetInsertionPoint()

		partial = era.system_select.GetValue()[:caret]
		match = era.universe.match_partial_system(partial)
		if match != None and len(partial) > 0:
			era.system_select.ChangeValue(match)
		else:
			era.system_select.ChangeValue(partial)
		era.system_select.SetInsertionPoint(caret)

	# Setup a functions to start the watcher thread
	def hostile_run(self, event):
		if not self.hostile_watcher:
			self.hostile_watch.SetLabel("Pause Hostile")
			self.hostile_watcher = StartHOSTILE(self)
		else:
			self.hostile_watch.SetLabel("Hostile Watch")
			# abort the thread
			self.hostile_watcher.abort()
			# set back to None so we can start it again
			self.hostile_watcher = None

	def loot_run(self, event):
		if not self.loot_watcher:
			self.loot_watch.SetLabel("Pause Loot")
			self.loot_watcher = StartLOOT(self)
		else:
			self.loot_watch.SetLabel("Loot Watch")
			# abort the thread
			self.loot_watcher.abort()
			# set back to None so we can start it again
			self.loot_watcher = None

	def Close(self, event):
		era.intel_map.Destroy()
		self.Destroy()

	#def get_clients(self, event):

	# This is rather bad and probably doesnt work... fix me
	def toggle_debug(self, event):
		if self.debug.IsChecked():
			print "Debugging enabled"
			sys.tracebacklimit = 1
		else:
			sys.tracebacklimit = 0


# Define watcher thread
class StartHOSTILE(Thread):

	def __init__(self, threadID):
		Thread.__init__(self)
		# Kill the thread when the main process is exited
		self.daemon = True
		self.threadID = threadID
		self._want_abort = 0
		self.start()
		era.intel_map.start_updating()

	def abort(self):
		print "Called to stop"
		self._want_abort = 1
		era.intel_map.stop_updating()

	# setup our log file watcher, only open it once and update when a new line is written
	def hostile_watch(self, logfile):

		fp = open(logfile, 'r')
		while self._want_abort == 0:

			# remove null padding (lol ccp)
			new = re.sub(r'[^\x20-\x7e]', '', fp.readline())

			if new:
				relevant_system = era.universe.find_system_in_string(new)
				if relevant_system:
					yield (relevant_system, new)
			else:
				time.sleep(0.01)

	# Start the main thread for alerting
	def run(self):

		print "Starting the Hostile Watcher"

		hostile_logdir = EVEDir.chat_logs

		# get region based on our dropdown box selection
		region = era.region_select.GetValue()
		# get the system based on our system input
		system = era.system_select.GetValue()
		era.intel_map.set_origin(system, int(era.range_select.GetValue()))

		# select identified logs and sort by date
		hostile_tmp = sorted([ f for f in os.listdir(hostile_logdir) if f.startswith("%s.imperium" % str(region))])
		# testing line so we shit up Corp chat not intel chans
		# hostile_tmp = sorted([ f for f in os.listdir(hostile_logdir) if f.startswith('Corp')])

		# grab the most recent file for each log
		logfile = os.path.join( hostile_logdir, hostile_tmp[-1] )

		# ignore status requests and clr reports
		status_words = [ "status",
						"Status",
						"clear",
						"Clear",
						"stat",
						"Stat",
						"clr",
						"Clr",
						"EVE System" ]

		# Print some initial info lines
		print "parsing from - Intel:  %s\n" % (hostile_tmp[-1])

		# if the word matches a trigger, move on
		for related_system, hostile_hit_sentence in self.hostile_watch(logfile):
			#print "%r | %r | %r | %r" % (related_system, self.hostile_words, hostile_hit_sentence)

			# if someone is just asking for status, ignore the hit
			if not any(status_word in hostile_hit_sentence for status_word in status_words):

				# find distance to the reported system
				distance = era.universe.find_system_distance(system, related_system, int(era.range_select.GetValue()))
				if distance != None:

					# get the current time for each event
					hit_time = time.strftime('%H:%M:%S')
					# get current date/time in UTC
					utc = time.strftime('[ %Y.%m.%d %H:%M', gmtime())[:17]

					# print the alert
					if which_os == "Windows":
						print "%s - HOSTILE ALERT!!\n" % (hit_time)
						print "%r (%s jumps)\n" % (hostile_hit_sentence, distance)
						wx.Yield()
					else:
						print "%s - HOSTILE ALERT!!" % (hit_time)
						print "%r (%s jumps)\n" % (hostile_hit_sentence, distance)
						wx.Yield()

					era.intel_map.ping(related_system)

					# play a tone to get attention, only if its recent!
					if utc in hostile_hit_sentence:
						sound_file = self.hostile_sound_for_distance(distance)
						if sound_file != None:
							if which_os == "Linux":
								os.system("aplay -q %r" % sound_file)

							elif which_os == "Windows":
								winsound.PlaySound("%s" % sound_file,SND_FILENAME)

							elif which_os == "Darwin":
								print('\a')
								print('\a')
								print('\a')

	def hostile_sound_for_distance(self, distance):
		if distance <= 5:
			if era.settings['close_range_sound'] == 'Voice':
				return os.path.join( era_dir, "sounds", "hostile_dist_%d.wav" % distance)
			elif era.settings['close_range_sound'] == 'Default':
				return hostile_sound
		else:
			if era.settings['long_range_sound'] == 'Default':
				return hostile_sound
		return None

# Define LOOT watcher thread
class StartLOOT(Thread):

	def __init__(self, threadID):
		Thread.__init__(self)
		# Kill the thread when the main process is exited
		self.daemon = True
		self.threadID = threadID
		self._want_abort = 0
		self.start()

	def abort(self):
		print "Called to stop"
		self._want_abort = 1

	# setup our log file watcher, only open it once and update when a new line is written
	def loot_watch(self, fn, words):
		done_count = 0

		fp = open(fn, 'r')
		while self._want_abort == 0:
			new = fp.readline()

			if new:
				done_count = 0
				for word in words:
					if word in new:
						yield (word, new)
			else:
				done_count = done_count + 1
				if done_count > 129:
					print "LOOT Notification"
					print "%r - Sites done (or something is wrong)\n" % (time.strftime('%H:%M:%S'))

					if which_os == "Linux":
						os.system("aplay -q %r" % done_sound)

					elif which_os == "Windows":
						winsound.PlaySound("%s" % done_sound,SND_FILENAME)

					elif which_os == "Darwin":
						print('\a')
						print('\a')
						print('\a')

					done_count = 0

				time.sleep(0.5)

	def run(self):
		count = 0

		logdir = EVEDir.game_logs

		# sort by date
		tmp = sorted([ f for f in os.listdir(logdir) if f.startswith('201')])

		# grab the most recent file
		fn = os.path.join( logdir, tmp[-1] )

		print "\nStarting the Loot Watcher"

		print "parsing from %s\n" % tmp[-1]

		# triggers to look for in the log file
		words = [ "Dread Guristas",
				"Dark Blood",
				"True Sansha",
				"Shadow Serpentis",
				"Sentient",
				"Domination",
				"Estamel Tharchon",
				"Vepas Minimala",
				"Thon Eney",
				"Kaikka Peunato",
				"Gotan Kreiss",
				"Hakim Stormare",
				"Mizuro Cybon",
				"Tobias Kruzhor",
				"Ahremen Arkah",
				"Draclira Merlonne",
				"Raysere Giant",
				"Tairei Namazoth",
				"Brokara Ryver",
				"Chelm Soran",
				"Selynne Mardakar",
				"Vizan Ankonin",
				"Brynn Jerdola",
				"Cormack Vaaja",
				"Setele Schellan",
				"Tuvan Orth", ]

		# Don't trigger if we are accepting or getting a contract
		false_pos = [ "following items",
					"question" ]

		for hit_word, hit_sentence in self.loot_watch(fn, words):

			if not any(false_word in hit_sentence for false_word in false_pos):

				if count < 1:
					count = count + 1
					# log the combat lines involving the spawn
					print "LOOT ALERT!!"
					print "%r - %r\n" % (time.strftime('%H:%M:%S'), hit_word)
					wx.Yield()
					# debug statement
					# print "%r" % (hit_sentence)

					# play a tone to get attention
					if which_os == "Linux":
						os.system("aplay -q %r" % tags_and_ammo)

					elif which_os == "Windows":
						winsound.PlaySound("%s" % tags_and_ammo,SND_FILENAME)

					elif which_os == "Darwin":
						print('\a')
						print('\a')
						print('\a')

					else:
						print "What fucking system are you running?"
						break

				elif count == 30:
					count = 0
					continue
				else:
					count = count + 1
					continue

if __name__ == '__main__':
	app=wx.App()
	frame=era(parent=None,id=wx.ID_ANY)
	frame.Show()
	app.MainLoop()
