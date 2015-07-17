import wx
import threading
import time

class IntelMap:
	def __init__(self, universe, parent, settings):
		self.axis1 = 'x'
		self.axis2 = 'z'
		self.universe = universe
		self.update_timer = None
		self.origin_system = None
		self.range = 0
		self.current_sub_map = []
		self.pings = []

		self.map_region = None
		self.map_panel = wx.Panel(parent)
		self.map_panel.SetDoubleBuffered(True)
		self.map_panel.SetBackgroundColour(wx.WHITE)
		self.map_panel.Bind(wx.EVT_PAINT, self.redraw_map)
		self.map_panel.Bind(wx.EVT_SIZE, self.resized)

		# Appearance
		self.system_size = wx.Point2D(50, 14)
		self.map_scale = wx.Point2D(1, 1)
		self.system_font_size = 8
		self.connection_color = 'blue'
		self.connection_thickness = 1
		self.connection_color_regional = 'green'
		self.connection_thickness_regional = 2
		self.system_border_color = (100, 100, 100)
		self.default_system_color = (230, 230, 230)
		self.origin_system_color = (140, 200, 255)
		self.pinged_system_color = (255, 60, 60)
		self.update_settings(settings)

	def Destroy(self):
		self.stop_updating()

	def update_settings(self, settings):
		self.update_interval = settings['update_interval']
		self.ping_duration = settings['ping_duration']
		self.system_spacing = wx.Point2D(settings['system_spacing'], settings['system_spacing'])
		self.redraw()
		if self.update_timer != None:
			self.stop_updating()
			self.start_updating()

	def start_updating(self):
		self.set_interval(self.update_pings, self.update_interval)

	def stop_updating(self):
		if self.update_timer != None:
			self.update_timer.cancel()
			self.update_timer = None

	def set_interval(self, func, sec):
		def func_wrapper():
			self.set_interval(func, sec)
			func()
		self.update_timer = threading.Timer(sec, func_wrapper)
		self.update_timer.start()

	def update_pings(self):
		current_time = time.time()
		old_len = len(self.pings)
		if old_len > 0:
			self.pings[:] = [x for x in self.pings if x['time'] + self.ping_duration > current_time]
			self.redraw()

	def resized(self, event):
		self.redraw()

	def redraw(self):
		self.map_panel.Refresh()

	def redraw_map(self, event):
		self.map_region = self.map_panel.Rect

		if self.origin_system is not None:
			dc = wx.PaintDC(self.map_panel)
			dc.BeginDrawing()

			map_center = wx.Point2D(self.origin_system[self.axis1], self.origin_system[self.axis2])

			connections_drawn = []
			for system_map in self.current_sub_map:
				for connected_system_data in system_map['connections']:
					sys_names = sorted([system_map['system']['solarSystemName'], connected_system_data['solarSystemName']])
					conn_key = "%s_%s" % (sys_names[0], sys_names[1])
					if not conn_key in connections_drawn:
						connections_drawn.append(conn_key)
						self.draw_connection(dc, map_center, system_map['system'], connected_system_data)

			systems_drawn = []
			for system_map in self.current_sub_map:
				self.draw_system(dc, map_center, system_map['system'], systems_drawn)
				for connected_system_data in system_map['connections']:
					self.draw_system(dc, map_center, connected_system_data, systems_drawn)

			dc.EndDrawing()
			del dc

	def get_sub_map(self, system, range, sub_map, checked):
		if not system in checked:
			checked.append(system)
			connected = self.universe.get_connected_systems_with_data(system['solarSystemID'])
			sub_map.append({ 'system': system, 'connections': connected })
			if range > 1:
				for connected_system in connected:
					sub_map = self.get_sub_map(connected_system, range - 1, sub_map, checked)
		return sub_map

	def convert_pos(self, map_center, system_data):
		delta_x, delta_y = system_data[self.axis1] - map_center.x, map_center.y - system_data[self.axis2]

		return wx.Point2D(delta_x * (self.system_size.x + self.system_spacing.x) * self.map_scale.x, delta_y * (self.system_size.y + self.system_spacing.y) * self.map_scale.y)

	def draw_connection(self, dc, map_center, system1_data, system2_data):
		x, y = self.map_region.Width / 2 + self.system_size.x / 2, self.map_region.Height / 2 + self.system_size.y / 2

		sys1_pos = self.convert_pos(map_center, system1_data)
		sys2_pos = self.convert_pos(map_center, system2_data)
		x -= self.system_size.x/2
		y -= self.system_size.y/2

		if system1_data['regionID'] == system2_data['regionID']:
			dc.SetPen(wx.Pen(self.connection_color, self.connection_thickness))
		else:
			dc.SetPen(wx.Pen(self.connection_color_regional, self.connection_thickness_regional))
		dc.DrawLine(x + sys1_pos.x, y + sys1_pos.y, x + sys2_pos.x, y + sys2_pos.y)

	def draw_system(self, dc, map_center, system_data, systems_drawn):
		if system_data in systems_drawn:
			return

		systems_drawn.append(system_data)

		x, y = self.map_region.Width / 2 + self.system_size.x / 2, self.map_region.Height / 2 + self.system_size.y / 2

		x -= self.system_size.x
		y -= self.system_size.y

		conn_pos = self.convert_pos(map_center, system_data)

		dc.SetPen(wx.Pen(self.system_border_color, 1))
		dc.SetBrush(wx.Brush(self.color_for_system(system_data)))
		dc.SetFont(wx.Font(self.system_font_size, wx.DEFAULT, wx.NORMAL, wx.NORMAL))

		text = system_data['solarSystemName']
		rect = wx.Rect(x + conn_pos.x, y + conn_pos.y, self.system_size.x, self.system_size.y)
		dc.DrawRoundedRectangleRect(rect, 4)
		tw, th = dc.GetTextExtent(text)
		dc.DrawText(text, x + conn_pos.x + (self.system_size.x-tw) / 2, y + conn_pos.y + (self.system_size.y-th) / 2)

	def color_for_system(self, system_data):
		ping = [x for x in self.pings if x['system'] == system_data['solarSystemName']]
		if len(ping) > 0:
			return self.interpolate_color(self.pinged_system_color, self.default_system_color, (time.time() - ping[0]['time']) / self.ping_duration)
		if system_data == self.origin_system:
			return self.origin_system_color
		return self.default_system_color

	def ping(self, system_name):
		ping = [x for x in self.pings if x['system'] == system_name]
		if len(ping):
			ping[0]['time'] = time.time()
		else:
			self.pings.append({ 'time': time.time(), 'system': system_name })
		self.redraw()

	def interpolate_color(self, col1, col2, t):
		return (col1[0] - (col1[0] - col2[0]) * t, col1[1] - (col1[1] - col2[1]) * t, col1[2] - (col1[2] - col2[2]) * t)

	def set_origin(self, system_name, range):
		system_id = self.universe.system_name_to_id(system_name)
		self.origin_system = self.universe.get_system_data(system_id)
		self.range = range
		self.current_sub_map = self.get_sub_map(self.origin_system, self.range, [], [])
		self.redraw()
