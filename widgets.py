# xmarksthespot - player for wherigo cartridges (custom widgets module).
# vim: set fileencoding=utf-8 foldmethod=marker :
# Copyright 2012 Bas Wijnen <wijnen@debian.org> {{{
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
# }}}

# Imports {{{
import gtk
import gui
import wherigo
import Map
import time
import re
# }}}

SIZE = gtk.ICON_SIZE_BUTTON

def fill_cache (media): # {{{
	if media._cache is not None:
		return
	for f in media._provider['File']:
		pl = gtk.gdk.PixbufLoader ()
		try:
			pl.write (wherigo._wfzopen (f[0]).read ())
			pl.close ()
		except:
			print ('Not using %s: %s' % (f[0], sys.exc_info ()[1]))
			continue
		media._cache = pl.get_pixbuf ()
		return
# }}}

class Book (gtk.Notebook): # {{{
	def __init__ (self, gui):
		gtk.Notebook.__init__ (self)
		self.connect ('page-added', self.no_new)	# Initialize tab labels.
		self.connect ('switch-page', self.no_new)
		self.set_show_tabs (True)
		self.set_tab_pos (gtk.POS_RIGHT)
		self.set_can_focus (False)
		self.button = gui.register_event ('button')
		def save_page ():
			p = self.get_current_page ()
			return lambda: self.set_current_page (p)
		gui.register_attribute ('save_page', save_page, self.set_current_page)
		gui.notebook_add ()
	def no_new (self, book, page, num):
		page = self.get_nth_page (num)
		page.new = False
		book.update_title (page)
	def update_title (self, page):
		t = page.tabname
		if not hasattr (page, 'no_size'):
			t += ' (%d)' % page.size
		t = '<span foreground="%s">%s</span>' % (page.color, t)
		if page.new:
			t = '<b>' + t + '</b>'
		label = gtk.Label ()
		label.set_markup (t)
		self.set_tab_label (page, label)
		page.show ()
# }}}

# Base classes {{{
class Details (gtk.VBox): # {{{
	def __init__ (self, gui, cb = True):
		self.gui = gui
		self.data = gui.data
		gtk.VBox.__init__ (self)
		self.alt = gtk.Label ()
		self.scrolledwindow = gtk.ScrolledWindow ()
		self.image = gtk.Image ()
		self.text = gtk.TextView ()
		self.text.set_wrap_mode (gtk.WRAP_WORD_CHAR)
		self.text.set_editable (False)
		self.buttons = gtk.VBox ()
		self.color = gui.gui.messagecolor
		self.tabname = 'Message'
		self.no_size = True
		if cb:
			gui.register_attribute ('set', None, self.set)
		else:
			self.cb = None
		self.scrolledwindow.set_policy (gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow.add_with_viewport (self.image)
		self.pack_start (self.alt, False, True)
		self.pack_start (self.scrolledwindow, True, True)
		self.pack_start (self.text, True, True)
		self.pack_start (self.buttons, False, True)
		self.show_all ()
		self.alt.hide ()
	def set (self, (media, text, buttons, cb)):
		# Media
		if isinstance (media, wherigo.ZMedia):
			fill_cache (media)
			if media._cache is None:
				self.alt.set_text (media.AltText)
				self.alt.show ()
				self.image.set_from_pixbuf (None)
				self.scrolledwindow.hide ()
			else:
				self.image.set_from_pixbuf (media._cache)
				self.scrolledwindow.show ()
				self.alt.hide ()
		else:
			self.image.set_from_pixbuf (None)
			self.scrolledwindow.hide ()
		# Text
		self.text.get_buffer ().set_text (text)
		# Buttons:
		# (commandname, pre-text, other-text, ((text, target), ...), source)
		# So:
		# not with: (command.Name, None, None, ((command.Text, None),), source)
		# with targets: (command.Name, command.Text, None, ((target.Name, target), ...), source)
		# no target: (command.Name, command.Text, command.EmptyTargetListText, (), source)
		# reciprocal: (command.Name, None, None, ((target.Name +':'+command.Text, source),), target)
		# multiple choice: (None, None, None, ((text, response), ...), None)
		#
		# text input: None
		while len (self.buttons.get_children ()) > 0:
			self.buttons.remove (self.buttons.get_children ()[0])
		entry = None
		for b in buttons:
			if b is None:
				# Text input.
				entry = gtk.Entry ()
				self.buttons.pack_start (entry, True, True)
				if callable (cb):
					entry.connect ('activate', cb)
				else:
					entry.set_sensitive (False)
					entry.set_text (cb or '')
				continue
			box = gtk.HBox ()
			if b[1] is not None:
				box.pack_start (gtk.Label (b[1]), False, True)
			if b[2] is not None:
				box.pack_start (gtk.HSeparator (), False, False)
				box.pack_start (gtk.Label (b[2]), True, True)
			for button in b[3]:
				if callable (cb):
					widget = gtk.Button (button[0])
					widget.connect ('clicked', cb, b[0], button[1], b[4])
				else:
					if cb == button[1]:
						widget = gtk.Frame ()
						subwidget = gtk.ToggleButton (button[0])
						subwidget.set_sensitive (False)
						widget.add (subwidget)
					else:
						widget = gtk.ToggleButton (button[0])
				box.pack_start (widget)
				if len (buttons) == 1 and len (b[3]) == 1:
					widget.grab_focus ()
			self.buttons.pack_start (box, True, True)
		self.buttons.show_all ()
		self.show ()
		if entry is not None:
			entry.grab_focus ()
# }}}
class List (gtk.VBox): # {{{
	def __init__ (self, gui, title):# {{{
		self.data = gui.data
		gtk.VBox.__init__ (self)
		self.store = gtk.ListStore (str, str, object, bool, bool, gtk.gdk.Pixbuf)
		self.treeview = gtk.TreeView (self.store)
		self.active_column = self.bool_column ('active', 3)
		self.visible_column = self.bool_column ('visible', 4)
		self.icon_column ('', 5)
		self.str_column (title, 0, 1)
		self.treeview.get_selection ().connect ('changed', self.selection_changed)
		self.details = Details (gui, False)
		win = gtk.ScrolledWindow ()
		self.pack_start (win)
		win.add (self.treeview)
		self.pack_start (self.details)
		self.changed = gui.register_event ('changed')
		gui.register_attribute ('select', None, self.select)
		gui.register_attribute ('update', None, lambda x: self.update ())
		self.data = gui.data
		self.show_all ()
		if not self.data.debug:
			self.active_column.set_visible (False)
			self.visible_column.set_visible (False)
	# }}}
	def bool_column (self, title, idx): # {{{
		ret = gtk.TreeViewColumn (title)
		renderer = gtk.CellRendererToggle ()
		self.treeview.append_column (ret)
		ret.pack_start (renderer)
		ret.add_attribute (renderer, 'active', idx)
		return ret
	# }}}
	def icon_column (self, title, idx): # {{{
		ret = gtk.TreeViewColumn (title)
		renderer = gtk.CellRendererPixbuf ()
		self.treeview.append_column (ret)
		ret.pack_start (renderer)
		ret.add_attribute (renderer, 'pixbuf', idx)
		return ret
	# }}}
	def str_column (self, title, idx, colidx): # {{{
		ret = gtk.TreeViewColumn (title)
		renderer = gtk.CellRendererText ()
		self.treeview.append_column (ret)
		ret.pack_start (renderer)
		ret.add_attribute (renderer, 'text', idx)
		ret.add_attribute (renderer, 'foreground', colidx)
		return ret
	# }}}
	def _find (self, model, path, iter, data): # {{{
		if model.get_value (iter, 2) == data[0]:
			data[1] = iter
			return True
	# }}}
	def select (self, item): # {{{
		data = [item, None]
		self.store.foreach (self._find, data)
		if data[1] != None:
			self.treeview.get_selection ().select_iter (data[1])
	# }}}
	def selection_changed (self, selection): # {{{
		'''Update details according to new selection.'''
		if not self.data.gameobject:
			return
		i = selection.get_selected ()[1]
		buttons = []
		if i:
			self.selected_item = self.store.get_value (i, 2)
			media = self.selected_item.Media
			text = self.selected_item.Description
			for c in self.selected_item.Commands:
				cmd = self.selected_item.Commands[c]
				if not cmd.Enabled:
					#print '%s: Command %s not enabled' % (self.selected_item.Name, cmd.Text)
					continue
				t = cmd.Text
				# Buttons:
				# (commandname, pre-text, other-text, ((text, target), ...), source)
				if cmd.CmdWith:
					l = []
					for k in [x for x in self.data.gameobject.AllZObjects.list () if isinstance (x, wherigo.ZItem) and x is not self.selected_item] if cmd.WorksWithAll else cmd.WorksWithList.list ():
						if k._is_visible (self.data.debug):
							l.append ((k.Name, k))
					if len (l) == 0:
						buttons.append ((c, t, cmd.EmptyTargetListText, (), self.selected_item))
					else:
						buttons.append ((c, t, None, l, self.selected_item))
				else:
					buttons.append ((c, None, None, ((t, cmd),), self.selected_item))
			for item in self.data.gameobject.AllZObjects.list ():
				if not item.Visible or not item.Active or not hasattr (item, 'Commands'):
					continue
				for c in item.Commands:
					cmd = item.Commands[c]
					if not cmd.Enabled or not cmd.CmdWith or cmd.WorksWithAll or self.selected_item not in cmd.WorksWithList.list () or not cmd.MakeReciprocal:
						continue
					buttons.append ((c, None, None, (('%s: %s' % (item.Name, cmd.Text), self.selected_item),), item))
		else:
			self.selected_item = None
			media = None
			text = ''
		def click (widget, name, item, source):
			if source is None:
				source = self.selected_item
			self.get_parent ().button (source, name, item)
		self.details.set ((media, text, buttons, click))
		self.changed ()
	# }}}
	def update (self): # {{{
		keys, full = [], []
		if self.data.gameobject:
			for i in self.data.gameobject.AllZObjects.list ():
				if self.must_show (i):
					keys.append (i)
					full.append ((i.Name, self.color, i, i.Active, i.Visible, None))
		self.size = 0
		# Step 1: remove all items that should not be present.
		current = self.store.get_iter_first ()
		while current:
			next = self.store.iter_next (current)
			k = self.store.get_value (current, 2)
			if k in keys:
				i = keys.index (k)
				self.size += 1
				keys.pop (i)
				full.pop (i)
			else:
				self.store.remove (current)
				self.remove_item (k)
				self.new = True
			current = next
		# Step 2: add all missing items
		for f in full:
			self.size += 1
			self.new = True
			self.store.append (f)
			self.add_item (f[2])
		# Step 3: update the information
		current = self.store.get_iter_first ()
		while current:
			i = self.store.get_value (current, 2)
			self.store.set_value (current, 3, i.Active != 0)
			self.store.set_value (current, 4, i.Visible != 0)
			self.store.set_value (current, 5, self.make_icon (i))
			current = self.store.iter_next (current)
		self.selection_changed (self.treeview.get_selection ())
		self.get_parent ().update_title (self)
		self.update_map ()
	# }}}
	def remove_item (self, item): # {{{
		pass
	# }}}
	def add_item (self, item): # {{{
		pass
	# }}}
	def update_map (self): # {{{
		pass
	# }}}
	def make_icon (self, item): # {{{
		'''Make Pixbuf icon for object.  Can be overridden.'''
		if item.Icon is None:
			return None
		fill_cache (item.Icon)
		if item.Icon._cache is None:
			return None
		size = gtk.icon_size_lookup (SIZE)
		return item.Icon._cache.scale_simple (size[0], size[1], gtk.gdk.INTERP_BILINEAR)
	# }}}
# }}}
class MarkerList (List): # {{{
	'''A list with links to markers on the map'''
	def __init__ (self, gui, title, layers): # {{{
		List.__init__ (self, gui, title)
		self.data = gui.data
		self.layers = layers
		self.layers = [gui.data.map.add_layer (Map.MarkerLayer (gui.data.map, color)) for color in layers]
		self.selected_item = None
		self.treeview.connect ('row-activated', self.activate)
	# }}}
	def activate (self, widget, path, column): # {{{
		i = self.store.get_iter (path)
		obj = self.store.get_value (i, 2)
		# TODO: trigger OnClicked?
		pos = obj._get_pos ()
		self.data.map.set_pos ((pos.latitude, pos.longitude))
	# }}}
	def update_stats (self): # {{{
		if self.selected_item:
			if self.selected_item.CurrentDistance.GetValue ('meters') < 1000:
				diststr = '%d m' % self.selected_item.CurrentDistance.GetValue ('meters')
			else:
				diststr = '%.2f km' % self.selected_item.CurrentDistance.GetValue ('kilometers')
			self.distance.set_text (diststr)
			self.bearing.set_text ('%d°' % self.selected_item.CurrentBearing.value)
			pos = self.selected_item._get_pos ()
			self.lat.set_text (make_str (pos.latitude))
			self.lon.set_text (make_str (pos.longitude))
			self.alt.set_text ('%d m' % pos.altitude)
		else:
			self.distance.set_text ('-')
			self.bearing.set_text ('-')
			self.lat.set_text ('-')
			self.lon.set_text ('-')
			self.alt.set_text ('-')
	# }}}
	def get_layer (self, info): # {{{
		# Overloadable for multi-layer lists.
		return self.layers[0]
	# }}}
	def selection_changed (self, selection): # {{{
		'''Refresh selected status of markers on the map.'''
		if self.selected_item is not None and self.selected_item._id is not None:
			layer = self.get_layer (self.selected_item)
			if len (layer.markers) > self.selected_item._id:
				layer.markers[self.selected_item._id][1][0] = False
			if len (layer.tracks) > self.selected_item._id:
				layer.tracks[self.selected_item._id][1][0] = False
		super (MarkerList, self).selection_changed (selection)
		if self.selected_item is not None and self.selected_item._id is not None:
			layer = self.get_layer (self.selected_item)
			if len (layer.markers) > self.selected_item._id:
				layer.markers[self.selected_item._id][1][0] = True
			if len (layer.tracks) > self.selected_item._id:
				layer.tracks[self.selected_item._id][1][0] = True
		self.data.map.update ()
	# }}}
	def remove_item (self, item): # {{{
		if item._id is not None:
			layer = self.get_layer (item)
			del layer.markers[item._id]
			for check in layer.markers:
				if check[2]._id > item._id:
					check[2]._id -= 1
	# }}}
	def add_item (self, item): # {{{
		pos = item._get_pos ()
		if pos:
			layer = self.get_layer (item)
			item._id = len (layer.markers)
			layer.markers += ([(pos.latitude, pos.longitude), [False, item.Active and item.Visible], item],)
			self.data.map.update ()
		else:
			item._id = None
	# }}}
	def update_map (self): # {{{
		# Refresh all marker coordinates on the map.
		for layer in self.layers:
			for marker in layer.markers:
				p = marker[2]._get_pos ()
				marker[0] = (p.latitude, p.longitude)
	# }}}
	def _debug_update_map (self, item): # {{{
		'Update active and visible status on map'
		if item._id is not None:
			layer = self.get_layer (item)
			layer.markers[item._id][1][1] = item.Active and item.Visible
	# }}}
# }}}
# }}}

# Widgets {{{
widgets = {'Message': Details, 'Book': Book}
class Locations (MarkerList): # {{{
	# Compass and list of locations; selected location is shown on compass.
	def __init__ (self, gui):
		self.data = gui.data
		self.color = gui.gui.locationcolor
		self.tabname = 'Locations'
		self.size = 0
		MarkerList.__init__ (self, gui, 'Location', (self.color,))
	def must_show (self, item):
		if not isinstance (item, wherigo.Zone):
			return False
		if self.data.debug or (item.Active and item.Visible):
			return True
		return False
	def update_map (self):
		# Add zone boundaries.
		for layer in self.layers:
			for track in layer.tracks:
				track[0] = []
				points = track[2].Points.list ()
				for point in points:
					track[0].append ((point.latitude, point.longitude))
				if len (points) > 0:
					track[0].append ((points[0].latitude, points[0].longitude))
	def add_item (self, item): # {{{
		pos = item._get_pos ()
		if pos:
			layer = self.get_layer (item)
			item._id = len (layer.tracks)
			layer.tracks += ([[(pos.latitude, pos.longitude)], [False, item.Active and item.Visible], item],)
			self.data.map.update ()
		else:
			item._id = None
	# }}}
	def remove_item (self, item): # {{{
		if item._id is not None:
			layer = self.get_layer (item)
			del layer.tracks[item._id]
			for check in layer.markers:
				if check[2]._id > item._id:
					check[2]._id -= 1
	# }}}
widgets['Locations'] = Locations
# }}}
class Inventory (List): # {{{
	def __init__ (self, gui):
		self.data = gui.data
		self.color = gui.gui.objectcolor
		self.tabname = 'Inventory'
		self.size = 0
		List.__init__ (self, gui, 'Item')
	def must_show (self, item):
		return item._is_visible (self.data.debug) and item.Container is wherigo.Player
widgets['Inventory'] = Inventory
# }}}
class Environment (MarkerList): # {{{
	def __init__ (self, gui):
		self.data = gui.data
		self.color = gui.gui.objectcolor
		self.tabname = 'Environment'
		self.size = 0
		MarkerList.__init__ (self, gui, 'Item or person', (self.color,))
	def must_show (self, item):
		#if settings.show_start:
		#	kret = [wherigo._starting_marker.Name]
		#	fret = [(wherigo._starting_marker.Name, config['positioncolor'], wherigo._starting_marker, True, True)]
		if not isinstance(item, wherigo.ZItem):
			return False
		#print('item %s %s %s %s %s' % (item.Name, item.Active, item.Visible, item._is_visible(self.data.debug), item.Container))
		return item._is_visible (self.data.debug) and item.Container is not wherigo.Player and isinstance (item, wherigo.ZItem)
widgets['Environment'] = Environment
# }}}
class Tasks (List): # {{{
	def __init__ (self, gui):
		self.data = gui.data
		self.color = gui.gui.taskcolor
		self.tabname = 'Tasks'
		self.size = 0
		List.__init__ (self, gui, 'Task')
	def must_show (self, item):
		return isinstance (item, wherigo.ZTask) and (self.data.debug or (item.Active and item.Visible))
	def make_icon (self, item):
		orig = List.make_icon (self, item)
		if not item.Complete:
			state = self.render_icon (gtk.STOCK_EXECUTE, SIZE)
		elif not item.CorrectState or item.CorrectState.lower () not in ('incorrect', 'notcorrect'):
			state = self.render_icon (gtk.STOCK_APPLY, SIZE)
		else:
			state = self.render_icon (gtk.STOCK_CANCEL, SIZE)
		if orig is None:
			return state
		size = gtk.icon_size_lookup (SIZE)
		ret = gtk.gdk.Pixbuf (gtk.gdk.COLORSPACE_RGB, True, 8, size[0] * 2, size[1])
		ret.fill (0)
		state.copy_area (0, 0, size[0], size[1], ret, 0, 0)
		orig.copy_area (0, 0, size[0], size[1], ret, size[0], 0)
		return ret
widgets['Tasks'] = Tasks
# }}}
class History (gtk.VBox): # {{{
	def __init__ (self, gui):
		self.color = gui.gui.historycolor
		self.tabname = 'History'
		self.size = 0
		gtk.VBox.__init__ (self)
		self.store = gtk.ListStore (str, str, object)
		self.selector = gtk.ComboBox (self.store)
		cell = gtk.CellRendererText ()
		self.selector.pack_start (cell)
		self.selector.show ()
		self.selector.add_attribute (cell, 'text', 0)
		self.pack_start (self.selector, False)
		self.timelabel = gtk.Label ()
		self.timelabel.show ()
		self.pack_start (self.timelabel, False)
		self.detail = Details (gui, False)
		self.pack_start (self.detail, True)
		self.detail.show ()
		self.selector.connect ('changed', self.update)
		self.size = 0
		gui.register_attribute ('add', None, self.add_item)
	def add_item (self, (media, text, buttons, choice)):
		title = text.split ('\n')[0][:30]
		timestamp = time.strftime ('%X')
		self.store.append ((title, timestamp, (media, text, buttons, choice)))
		self.size += 1
		self.get_parent ().update_title (self)
	def update (self, widget):
		i = self.selector.get_active_iter ()
		if i is None:
			self.timelabel.set_text ('')
			self.detail.set (media = None, text = '', buttons = (), cb = None)
		else:
			self.timelabel.set_text (self.store.get_value (i, 1))
			self.detail.set (self.store.get_value (i, 2))
widgets['History'] = History
# }}}
class Log (gtk.TreeView): # {{{
	def __init__ (self, gui):
		self.color = gui.gui.logcolor
		self.tabname = 'Log'
		self.size = 0
		self.store = gtk.ListStore (str, str, str, str, object, float, float, float, float)	# time, location, level, message, datetime, lat, lon, alt, error
		gtk.TreeView.__init__ (self, self.store)
		self.columns = [gtk.TreeViewColumn (x) for x in ('Time', 'Location', 'Level', 'Message')]
		self.renderer = [gtk.CellRendererText () for x in range (len (self.columns))]
		for c in range (len (self.columns)):
			self.append_column (self.columns[c])
			self.columns[c].pack_start (self.renderer[c])
			self.columns[c].add_attribute (self.renderer[c], 'text', c)
	def add_log (self, level, levelname, text):
		t = time.strftime ('%X')
		self.store.append ((t, '', levelname, text, t, 0, 0, 0, 0))
		self.size += 1
		self.new = True
		self.get_parent ().update_title (self)
widgets['Log'] = Log
# }}}
class Timers (gtk.TreeView): # {{{
	def __init__ (self, gui):
		self.data = gui.data
		self.colors = gui.get_attribute ('colors', default = '#f00,#0f0').split (',', 1)
		signature = (str, str, bool, str, str, str, object)
		self.store = gtk.ListStore (*signature)
		gtk.TreeView.__init__ (self, self.store)
		self.set_can_focus (False)
		self.columns = [gtk.TreeViewColumn (x) for x in ('Name', 'Type', 'Running', 'Remaining', 'Duration')]
		self.renderer = [gtk.CellRendererToggle () if signature[c] == bool else gtk.CellRendererText () for c in range (len (self.columns))]
		for c, col in enumerate (self.columns):
			self.append_column (col)
			col.pack_start (self.renderer[c], True)
			col.add_attribute (self.renderer[c], 'active' if signature[c] is bool else 'text', c)
			if signature[c] is not bool:
				col.add_attribute (self.renderer[c], 'foreground', 5)
		self.set_reorderable (True)
		gui.register_attribute ('skip', self.skip, None)
		gui.register_attribute ('update', None, lambda x: self.update ())
	def update (self):
		if not self.data.gameobject:
			return [], []
		keys = []
		full = []
		for i in self.data.gameobject.AllZObjects.list ():
			if isinstance (i, wherigo.ZTimer):
				keys += (i.Name,)
				full += ((i.Name, '', False, '', '', self.colors[0], i),) # Actual values are filled in below, in step 3.
		# Step 1: remove all items that should not be present.
		current = self.store.get_iter_first ()
		while current:
			next = self.store.iter_next (current)
			k = self.store.get_value (current, 0)
			if k not in keys:
				self.store.remove (current)
			else:
				i = keys.index (k)
				keys.pop (i)
				full.pop (i)
			current = next
		# Step 2: add all missing items
		for f in full:
			self.store.append (f)
		# Step 3: update contents.
		current = self.store.get_iter_first ()
		while current:
			i = self.store.get_value (current, 6)
			self.store.set_value (current, 1, i.Type)
			self.store.set_value (current, 2, i._target is not None)
			self.store.set_value (current, 5, self.colors[i._target is not None])
			self.store.set_value (current, 3, int (i.Remaining))
			self.store.set_value (current, 4, '%6.3f' % i.Duration)
			current = self.store.iter_next (current)
	def skip (self):
		'''Compute time which must be skipped ahead until next timeout'''
		if not self.data.gameobject:
			return
		times = [t.Remaining for t in self.data.gameobject.AllZObjects.list () if isinstance (t, wherigo.ZTimer) and t._target]
		if len (times) == 0:
			return 0
		return min (times)
		#skipped_time += shortest_time
		#update ()	# This is the global update function; it will set the game object's time to the new value.
		#gameobject._reschedule_timers ()
widgets['Timers'] = Timers
# }}}
# }}}
