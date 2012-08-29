# encoding=utf-8
# Map.py - Map class, for showing a map with stuff on it, used by xmarksthespot.
# Copyright 2012 Bas Wijnen <wijnen@debian.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gtk
import math

def deg (pos):
	return ['%d°%f' % (int (pos[i]), (pos[i] - int (pos[i])) * 60) for i in range (len (pos))]

class Layer:
	'''Base class for layers. Implementations must define draw(self, pos) to update the contents.
	Drawing must be done on self.map.buffer.'''
	def __init__ (self, map, color):
		self.map = map
		self.color = color
	def _realize (self, window):
		self.gc = [gtk.gdk.GC (window) for t in range (2)]
		c = gtk.gdk.colormap_get_system ().alloc_color (self.color)
		for t in range (2):
			self.gc[t].set_foreground (c)
		self.gc[1].set_dashes (0, (3, 4))
		self.gc[1].set_line_attributes (1, gtk.gdk.LINE_ON_OFF_DASH, gtk.gdk.CAP_BUTT, gtk.gdk.JOIN_BEVEL)
	def draw_marker (self, pos, details):
		p = self.map.pixel (pos)
		gc = self.gc[0 if details[1] else 1]
		if 0 <= p[0] < self.map.size[0] and 0 <= p[1] < self.map.size[1]:
			#print ('drawing marker at %s = %s' % (','.join (deg (pos)), str (p)))
			self.map.buffer.draw_line (gc, p[0], p[1] - 5, p[0], p[1] - 15)
			self.map.buffer.draw_line (gc, p[0], p[1] + 5, p[0], p[1] + 15)
			self.map.buffer.draw_line (gc, p[0] - 5, p[1], p[0] - 15, p[1])
			self.map.buffer.draw_line (gc, p[0] + 5, p[1], p[0] + 15, p[1])
			if details[0]:
				self.map.buffer.draw_arc (gc, False, p[0] - 10, p[1] - 10, 20, 20, 0, 64 * 360)
		else:
			p = [float (x) for x in p]
			center = [float (x) for x in self.map.pixel (self.map.pos)]
			# Draw an arrow at the border of the screen.
			if p[0] < 0:
				# Compute intersection on left side.
				# Compute a and b in y = ax + b.
				a = (p[1] - center[1]) / (p[0] - center[0])
				b = p[1] - a * p[0]
				# b is the intersection point.
				if b < 0:
					# intersection is on top side.
					intersection = self.intersect_top (p, center)
				elif b >= self.map.size[1]:
					# intersection is on bottom side.
					intersection = self.intersect_bottom (p, center)
				else:
					intersection = (0, b)
			elif p[0] >= self.map.size[0]:
				# Compute intersection on right side.
				# Compute a and b in y = ax + b.
				a = (p[1] - center[1]) / (p[0] - center[0])
				b = p[1] - a * p[0]
				point = a * self.map.size[0] + b
				if point < 0:
					# intersection is on top side.
					intersection = self.intersect_top (p, center)
				elif point >= self.map.size[1]:
					# intersection is on bottom side.
					intersection = self.intersect_bottom (p, center)
				else:
					intersection = (self.map.size[0], point)
			elif p[1] < 0:
				intersection = self.intersect_top (p, center)
			else:
				intersection = self.intersect_bottom (p, center)
			delta = [p[t] - center[t] for t in range (2)]
			dist = math.sqrt (sum ([delta[t] ** 2 for t in range (2)]))
			unit = [delta[t] / dist for t in range (2)]
			if details[0]:
				self.map.buffer.draw_line (gc, int (intersection[0] - 20 * unit[0]), int (intersection[1] - 20 * unit[1]), int (intersection[0] - 5 * unit[0]), int (intersection[1] - 5 * unit[1]))
				self.map.buffer.draw_line (gc, int (intersection[0] - 5 * unit[0] + 5 * unit[1]), int (intersection[1] - 5 * unit[1] - 5 * unit[0]), int (intersection[0]), int (intersection[1]))
				self.map.buffer.draw_line (gc, int (intersection[0] - 5 * unit[0] - 5 * unit[1]), int (intersection[1] - 5 * unit[1] + 5 * unit[0]), int (intersection[0]), int (intersection[1]))
				self.map.buffer.draw_line (gc, int (intersection[0] - 5 * unit[0] + 5 * unit[1]), int (intersection[1] - 5 * unit[1] - 5 * unit[0]), int (intersection[0] - 5 * unit[0] - 5 * unit[1]), int (intersection[1] - 5 * unit[1] + 5 * unit[0]))
			else:
				self.map.buffer.draw_line (gc, int (intersection[0] - 10 * unit[0]), int (intersection[1] - 10 * unit[1]), int (intersection[0]), int (intersection[1]))
	def intersect_top (self, p, center):
		'Prevent division by zero: swap x and y.'
		a = (p[0] - center[0]) / (p[1] - center[1])
		b = p[0] - a * p[1]
		return (b, 0)
	def intersect_bottom (self, p, center):
		'Prevent division by zero: swap x and y.'
		a = (p[0] - center[0]) / (p[1] - center[1])
		b = p[0] - a * p[1]
		return (a * self.map.size[1] + b, self.map.size[1])
	def boundingbox (self, box):
		return box

class Map (gtk.DrawingArea):
	def __init__ (self, lat, lon):
		gtk.DrawingArea.__init__ (self)
		self.force_position = None
		self.size = None
		self.buffer = None
		self.connect_after ('realize', self.realize)
		self.connect ('expose-event', self.expose)
		self.connect ('configure-event', self.configure)
		self.connect ('button-press-event', self.button_press)
		self.connect ('scroll-event', self.scroll)
		self.connect ('key-press-event', self.key_press)
		self.connect ('motion-notify-event', self.motion)
		self.pos = (lat, lon)
		self.zoom = None
		self.layers = []
		self.positionlayer = None
		self.buffer = None
		self.gc = None
		self.set_can_focus (True)
		self.add_events (gtk.gdk.EXPOSURE_MASK | gtk.gdk.STRUCTURE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.SCROLL_MASK | gtk.gdk.KEY_PRESS_MASK | gtk.gdk.BUTTON2_MOTION_MASK)
	def add_layer (self, layer):
		self.layers += (layer,)
		w = self.get_window ()
		if w:
			layer._realize (w)
		self.update ()
	def set_pos (self, pos):
		self.pos = pos
		self.update ()
	def set_zoom (self, zoom):
		self.zoom = float (zoom)
		self.update ()
	def pixel (self, pos):
		'''Convert a position (lat, long) to a pixel (x, y).'''
		#self.map.pos is the center of the image.
		#self.map.zoom is the number of pixels per longitudinal degree.
		# latitudinal number of pixels per degree is the value for the longitude of pos, it is used for the entire image.
		# in y direction, the zoom is negative so higher numbers are at the top of the screen. The y direction is the latitude.
		zoom = (-self.zoom, self.zoom * math.cos (math.radians (self.pos[0])))
		fromcenter = [pos[i] - self.pos[i] for i in range (2)]
		# Note that x and y are reversed.
		return [int (self.size[i] / 2. + fromcenter[1 - i] * zoom[1 - i]) for i in range (2)]
	def position (self, pixel):
		'''Convert a pixel (x, y) to a position (long, lat).'''
		zoom = (-self.zoom, self.zoom * math.cos (math.radians (self.pos[0])))
		fromcenter = [pixel[i] - self.size[i] / 2. for i in range (2)]
		return [self.pos[i] + fromcenter[1 - i] / zoom[i] for i in range (2)]
	def update (self):
		w = self.get_window ()
		if not w or not self.buffer or not self.gc:
			return True
		# Clear buffer.
		self.buffer.draw_rectangle (self.bggc, True, 0, 0, self.size[0], self.size[1])
		if not self.pos or not self.zoom:
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.size[0], self.size[1])
			return True
		for layer in self.layers:
			layer.draw ()
		w.draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.size[0], self.size[1])
		return True
	def realize (self, widget):
		gtk.DrawingArea.realize (self)
		self.gc = gtk.gdk.GC (self.get_window ())
		self.gc.set_foreground (gtk.gdk.colormap_get_system ().alloc_color ('black'))
		self.bggc = gtk.gdk.GC (self.get_window ())
		self.bggc.set_foreground (gtk.gdk.colormap_get_system ().alloc_color ('white'))
		for l in self.layers:
			l._realize (self.get_window ())
	def expose (self, widget, event):
		if not self.buffer or not self.gc:
			return True
		self.get_window ().draw_drawable (self.gc, self.buffer, event.area[0], event.area[1], event.area[0], event.area[1], event.area[2], event.area[3])
	def configure (self, widget, event):
		x, y, width, height = widget.get_allocation()
		self.size = width, height
		self.buffer = gtk.gdk.Pixmap (self.get_window (), width, height)
		self.update ()
	def scroll (self, widget, event):
		part = .25	# When using scroll events, scroll this amount of the width or height per event.
		if event.direction == gtk.gdk.SCROLL_UP:
			zero = self.position ((0, 0))
			self.pos = (self.pos[0] - (self.pos[0] - zero[0]) * part, self.pos[1])
		elif event.direction == gtk.gdk.SCROLL_DOWN:
			zero = self.position ((0, 0))
			self.pos = (self.pos[0] + (self.pos[0] - zero[0]) * part, self.pos[1])
		elif event.direction == gtk.gdk.SCROLL_LEFT:
			zero = self.position ((0, 0))
			self.pos = (self.pos[0], self.pos[1] - (self.pos[1] - zero[1]) * part)
		elif event.direction == gtk.gdk.SCROLL_RIGHT:
			zero = self.position ((0, 0))
			self.pos = (self.pos[0], self.pos[1] + (self.pos[1] - zero[1]) * part)
		self.update ()
	def button_press (self, widget, event):
		'''Zoom in (button 1) or out (button 3) around the clicked spot'''
		self.grab_focus ()
		if event.button == 1:
			if event.state & gtk.gdk.CONTROL_MASK:
				# Clicking with control will send the coordinate back to the application.
				# This can be used to force the application to behave as if the user is at this position.
				self.force_position = self.position ((event.x, event.y))
				return
			factor = 2
		elif event.button == 2:
			self.motion_pos = event.x, event.y
			return True
		elif event.button == 3:
			factor = .5
		else:
			return False
		spot = self.position ((event.x, event.y))
		delta = (event.x - self.size[0] / 2., event.y - self.size[1] / 2.)
		self.zoom *= factor
		x = self.pixel (spot)
		self.pos = self.position ([x[i] - delta[i] for i in range (2)])
		self.update ()
	def motion (self, widget, event):
		dx = event.x - self.motion_pos[0]
		dy = event.y - self.motion_pos[1]
		center = self.pixel (self.pos)
		self.pos = self.position ((center[0] - dx, center[1] - dy))
		self.motion_pos = event.x, event.y
		self.update ()
	def get_force_position (self):
		ret = self.force_position
		self.force_position = None
		return ret
	def key_press (self, widget, event):
		part = .25	# When using arrow keys, scroll this amount of the width or height per key press.
		if event.keyval == gtk.keysyms.Up:
			zero = self.position ((0, 0))
			self.pos = (self.pos[0] - (self.pos[0] - zero[0]) * part, self.pos[1])
		elif event.keyval == gtk.keysyms.Down:
			zero = self.position ((0, 0))
			self.pos = (self.pos[0] + (self.pos[0] - zero[0]) * part, self.pos[1])
		elif event.keyval == gtk.keysyms.Left:
			zero = self.position ((0, 0))
			self.pos = (self.pos[0], self.pos[1] - (self.pos[1] - zero[1]) * part)
		elif event.keyval == gtk.keysyms.Right:
			zero = self.position ((0, 0))
			self.pos = (self.pos[0], self.pos[1] + (self.pos[1] - zero[1]) * part)
		elif event.keyval == gtk.keysyms.Page_Up:
			self.zoom *= 2.
		elif event.keyval == gtk.keysyms.Page_Down:
			self.zoom /= 2.
		elif event.keyval == gtk.keysyms.Return and event.state & gtk.gdk.CONTROL_MASK:
			self.force_position = self.pos
		elif event.keyval == gtk.keysyms.Home and event.state & gtk.gdk.CONTROL_MASK:
			# Fit everything to screen.
			box = None
			for l in self.layers:
				box = l.boundingbox (box)
			self.pos = ((box[0] + box[2]) / 2., (box[1] + box[3]) / 2.)
			size = (box[2] - box[0], box[3] - box[1])
			if size[0] == 0:
				size = (.00001, size[1])
			if size[1] == 0:
				size = (size[0], .00001)
			pixels = self.get_window ().get_size ()
			zoomlat = pixels[1] / size[0]
			zoomlon = pixels[0] / (size[1] * math.cos (math.radians (self.pos[0])))
			self.zoom = min (zoomlat, zoomlon) * 0.95
		elif event.keyval == gtk.keysyms.Home:
			# Move view to current location.
			if self.positionlayer and len (self.positionlayer.markers) > 0:
				self.pos = self.positionlayer.markers[0][0]
		self.update ()
		return True

class MapLayer (Layer):
	'''A layer showing a map'''
	def __init__ (self, map):
		Layer.__init__ (self, map, 'black')
	def draw (self):
		pass	#TODO

class GridLayer (Layer):
	'''A layer showing a grid'''
	def __init__ (self, map, color):
		Layer.__init__ (self, map, color)
	def draw (self):
		pass	#TODO

class MarkerLayer (Layer):
	'''A layer showing markers and tracks'''
	def __init__ (self, map, color):
		Layer.__init__ (self, map, color)
		self.markers = []
		self.tracks = []
	def draw (self):
		for m in self.markers:
			self.draw_marker (m[0], m[1])
		for t in self.tracks:
			pixt = [self.map.pixel (x) for x in t]
			for p in range (len (pixt) - 1):
				self.map.buffer.draw_line (self.gc[0], pixt[p][0], pixt[p][1], pixt[p + 1][0], pixt[p + 1][1])
	def boundingbox (self, box):
		for m in self.markers:
			box = self.boundingbox_add (box, m[0])
		for t in self.tracks:
			for p in t:
				box = self.boundingbox_add (box, p)
		return box
	def boundingbox_add (self, box, point):
		if box is None:
			return [point[0], point[1], point[0], point[1]]
		if box[0] > point[0]:
			box[0] = point[0]
		if box[1] > point[1]:
			box[1] = point[1]
		if box[2] < point[0]:
			box[2] = point[0]
		if box[3] < point[1]:
			box[3] = point[1]
		return box

class PositionLayer (MarkerLayer):
	'''A layer showing the current position'''
	def __init__ (self, map, color):
		MarkerLayer.__init__ (self, map, color)
		self.markers = [[self.map.pos, [False, True]]]
		assert self.map.positionlayer == None
		self.map.positionlayer = self
