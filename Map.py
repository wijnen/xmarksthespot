# encoding=utf-8
# Map class, for showing a map with stuff on it.

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
		self.gc = gtk.gdk.GC (window)
		self.gc.set_foreground (gtk.gdk.colormap_get_system ().alloc_color (self.color))
	def draw_marker (self, pos, active = False):
		p = self.map.pixel (pos)
		#print ('drawing marker at %s = %s' % (','.join (deg (pos)), str (p)))
		self.map.buffer.draw_line (self.gc, p[0], p[1] - 5, p[0], p[1] - 15)
		self.map.buffer.draw_line (self.gc, p[0], p[1] + 5, p[0], p[1] + 15)
		self.map.buffer.draw_line (self.gc, p[0] - 5, p[1], p[0] - 15, p[1])
		self.map.buffer.draw_line (self.gc, p[0] + 5, p[1], p[0] + 15, p[1])
		if active:
			self.map.buffer.draw_arc (self.gc, False, p[0] - 10, p[1] - 10, 20, 20, 0, 64 * 360)

class Map (gtk.DrawingArea):
	def __init__ (self, lat, lon):
		gtk.DrawingArea.__init__ (self)
		self.size = None
		self.buffer = None
		self.connect_after ('realize', self.realize)
		self.connect ('expose-event', self.expose)
		self.connect ('configure-event', self.configure)
		self.connect ('button-press-event', self.button_press)
		self.connect ('scroll-event', self.scroll)
		self.connect ('key-press-event', self.key_press)
		self.pos = (lat, lon)
		self.zoom = None
		self.layers = []
		self.positionlayer = None
		self.buffer = None
		self.gc = None
		self.set_can_focus (True)
		self.add_events (gtk.gdk.EXPOSURE_MASK | gtk.gdk.STRUCTURE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.SCROLL_MASK | gtk.gdk.KEY_PRESS_MASK)
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
		if not self.buffer or not self.gc:
			return True
		# Clear buffer.
		self.buffer.draw_rectangle (self.bggc, True, 0, 0, self.size[0], self.size[1])
		if not self.pos or not self.zoom:
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.size[0], self.size[1])
			return True
		for layer in self.layers:
			layer.draw ()
		self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.size[0], self.size[1])
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
		if event.direction == gtk.gdk.SCROLL_UP:
			dir = (0, -1)
		elif event.direction == gtk.gdk.SCROLL_DOWN:
			dir = (0, 1)
		elif event.direction == gtk.gdk.SCROLL_LEFT:
			dir = (-1, 0)
		elif event.direction == gtk.gdk.SCROLL_RIGHT:
			dir = (1, 0)
		# TODO
	def button_press (self, widget, event):
		'''Zoom in (button 1) or out (button 3) around the clicked spot'''
		if event.button == 1:
			factor = 2
		elif event.button == 3:
			factor = .5
		else:
			return
		spot = self.position ((event.x, event.y))
		delta = (event.x - self.size[0] / 2., event.y - self.size[1] / 2.)
		self.zoom *= factor
		x = self.pixel (spot)
		self.pos = self.position ([x[i] - delta[i] for i in range (2)])
		self.update ()
	def key_press (self, widget, event):
		print event

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
				self.map.buffer.draw_line (self.gc, pixt[p][0], pixt[p][1], pixt[p + 1][0], pixt[p + 1][1])

class PositionLayer (MarkerLayer):
	'''A layer showing the current position'''
	def __init__ (self, map, color):
		MarkerLayer.__init__ (self, map, color)
		self.markers = [[self.map.pos, 0]]
		assert self.map.positionlayer == None
		self.map.positionlayer = self
