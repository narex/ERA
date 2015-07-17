import wx
import os
import json

class SettingsDialog(wx.Dialog):
	def __init__(self, *args, **kwargs):
		wx.Dialog.__init__(self, *args, **kwargs)

		# Load settings if they exist, otherwise use defaults
		self.settings_file = 'config.json'

		self.settings = { 'long_range_sound': 'None', 'close_range_sound': 'Default', 'ping_duration': 300, 'update_interval': 5, 'system_spacing': 8 }

		if os.path.isfile(self.settings_file):
			settings_data = open(self.settings_file)
			self.settings = json.load(settings_data)
			settings_data.close()
		else:
			self.save_settings()


		self.panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)


		# Hostile Watcher
		subtitle = wx.StaticText(self.panel, wx.ID_ANY, 'Hostile')
		font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD)
		subtitle.SetFont(font)
		vbox.Add(subtitle, proportion=0, flag=wx.LEFT | wx.TOP, border=6)

		grid_sizer = wx.FlexGridSizer(2, 2, 4, 4)

		grid_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Close Range Sound'), proportion=0, flag=wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
		self.close_range_sound_select = wx.ComboBox(self.panel, size=(100,25), choices=['Default', 'Voice', 'None'], style=wx.CB_READONLY)
		self.close_range_sound_select.SetValue(self.settings['close_range_sound'])
		grid_sizer.Add(self.close_range_sound_select, proportion=0)

		grid_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Long Range Sound'), flag=wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
		self.long_range_sound_select = wx.ComboBox(self.panel, size=(100,25), choices=['None', 'Default'], style=wx.CB_READONLY)
		self.long_range_sound_select.SetValue(self.settings['long_range_sound'])
		grid_sizer.Add(self.long_range_sound_select, proportion=0)

		vbox.Add(grid_sizer, proportion=0, flag=wx.TOP | wx.LEFT, border=6)


		# Intel Map
		subtitle = wx.StaticText(self.panel, wx.ID_ANY, 'Intel Map')
		font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD)
		subtitle.SetFont(font)
		vbox.Add(subtitle, proportion=0, flag=wx.LEFT | wx.TOP, border=6)

		grid_sizer = wx.FlexGridSizer(3, 2, 4, 4)

		grid_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Ping Duration (seconds)'), proportion=0, flag=wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
		self.ping_duration = wx.TextCtrl(self.panel, value=str(self.settings['ping_duration']))
		grid_sizer.Add(self.ping_duration, proportion=0)

		grid_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Update Interval (seconds)'), proportion=0, flag=wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
		self.update_interval = wx.TextCtrl(self.panel, value=str(self.settings['update_interval']))
		grid_sizer.Add(self.update_interval, proportion=0)

		grid_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'System Spacing'), proportion=0, flag=wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
		self.system_spacing = wx.TextCtrl(self.panel, value=str(self.settings['system_spacing']))
		grid_sizer.Add(self.system_spacing, proportion=0)

		vbox.Add(grid_sizer, proportion=0, flag=wx.TOP | wx.LEFT, border=6)


		# OK/Cancel buttons
		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.button_ok = wx.Button(self.panel, label="OK")
		self.button_ok.Bind(wx.EVT_BUTTON, self.on_ok)
		self.button_cancel = wx.Button(self.panel, label="Cancel")
		self.button_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
		button_sizer.Add(self.button_cancel, proportion=0)
		button_sizer.Add(self.button_ok, proportion=0, flag=wx.LEFT, border=10)

		vbox.Add(button_sizer, proportion=0, flag=wx.TOP | wx.LEFT, border=10)

		self.panel.SetSizerAndFit(vbox)

	def on_cancel(self, e):
		self.EndModal(wx.ID_CANCEL)

	def on_ok(self, e):
		self.settings['close_range_sound'] = self.close_range_sound_select.GetValue()
		self.settings['long_range_sound'] = self.long_range_sound_select.GetValue()
		self.settings['ping_duration'] = int(self.ping_duration.GetValue())
		self.settings['update_interval'] = int(self.update_interval.GetValue())
		self.settings['system_spacing'] = int(self.system_spacing.GetValue())
		self.save_settings()
		self.EndModal(wx.ID_OK)

	def get_settings(self):
		return self.settings

	def save_settings(self):
		json.dump(self.settings, open(self.settings_file, 'w'))
