import os
import json

class Universe:
	def __init__(self, era_dir):
		self.systems = []
		self.jumps = []
		self.era_dir = era_dir
		self.current_systems = []
		self.current_jumps = []

	def load(self):
		json_data = open(os.path.join( self.era_dir, "universe", "systems.json"))
		self.systems = json.load(json_data)
		json_data.close()
		json_data = open(os.path.join( self.era_dir, "universe", "jumps.json"))
		self.jumps = json.load(json_data)
		json_data.close()

	def change_region(self, regions):
		self.current_systems = [x for x in self.systems if x['regionID'] in regions]
		self.current_jumps = [x for x in self.jumps if x['fromRegionID'] in regions and x['toRegionID'] in regions]

	def region_short_name_to_ids(self, name):
		return { 'brn': [10000055], 'dek': [10000035], 'fade': [10000046, 10000023], 'ftn': [10000058], 'tnl': [10000045], 'tri': [10000010], 'vale': [10000003], 'vnl': [10000015], 'fade-only': [10000046], 'pb-only': [10000023] }[name]

	def match_partial_system(self, text):
		for system in self.current_systems:
			if system['solarSystemName'].startswith(text):
				return system['solarSystemName']
		return None

	def find_system_in_string(self, string):
		for system in self.current_systems:
			if system['solarSystemName'] in string:
				return system['solarSystemName']
		return None

	def system_name_to_id(self, system):
		return [x['solarSystemID'] for x in self.current_systems if x['solarSystemName'] == system][0]

	def find_system_distance(self, start_system, dest_system, range):
		routes_found = []
		# find the distance of all routes from start system to destination system
		self.system_distance_recursive(self.system_name_to_id(start_system), self.system_name_to_id(dest_system), 0, range, [], routes_found)
		# return shortest path
		return min(routes_found) if len(routes_found) else None

	def system_distance_recursive(self, cur_system, dest_system, distance, range, checked, routes_found):
		# exit if out of range or system is already checked
		if distance > range or cur_system in checked:
			return

		if cur_system == dest_system:
			# destination found, so we don't need to check further connections
			routes_found.append(distance)
			return

		for connected_system in self.get_connected_systems(cur_system):
			# duplicate existing path and append this system
			now_checked = list(checked)
			now_checked.append(cur_system)
			# recursively find distance, if a path exists
			conn_dist = self.system_distance_recursive(connected_system, dest_system, distance + 1, range, now_checked, routes_found)
			if conn_dist >= 0:
				# this system is part of a path to destination, so add the distance
				routes_found.append(conn_dist)

	def get_connected_systems(self, system_id):
		# find the system and return its connections
		connected = []
		for jump in self.current_jumps:
			if jump['fromSolarSystemID'] == system_id:
				connected.append(jump['toSolarSystemID'])
		return connected

	def get_connected_systems_with_data(self, system_id):
		connected_systems = self.get_connected_systems(system_id)
		return map(lambda conn: self.get_system_data(conn), connected_systems)

	def get_system_data(self, system_id):
		return [x for x in self.current_systems if x['solarSystemID'] == system_id][0]
