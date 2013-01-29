# wherigo.py - Module containing wherigo stuff that will be accessed by the lua code from the wherigo cartridge.
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

# All spherical _math formulae were taken from http://www.movable-type.co.uk/scripts/latlong.html

import math as _math
import lua as _lang
import struct as _struct
import zipfile as _zipfile
import os as _os
import sys as _sys

INVALID_ZONEPOINT = False	# Constant representing a coordinate which does not exist, used to indicate that a variable should not hold a real value.

DETAILSCREEN = 0 	# Constant referencing the detail screen of a Wherigo character, item, zone, etc.
INVENTORYSCREEN = 1	# Constant referencing the player's inventory screen.
ITEMSCREEN = 2		# Constant referencing the visible item list screen.
LOCATIONSCREEN = 3	# Constant referencing the visible locations list screen.
MAINSCREEN = 4		# Constant referencing the main Wherigo screen allowing access to the various list screens.
TASKSCREEN = 5		# Constant referencing the visible task list screen.
_screen_names = ('Detail', 'Inventory', 'Item', 'Location', 'Main', 'Tasks')

LOGDEBUG = 0		# For log messages, indicates the message is a Debugging message. (messages are not displayed at default log level)
LOGCARTRIDGE = 1	# For log messages, indicates the message is a default message.
LOGINFO = 2		# For log messages, indicates the message is Informational, and not as severe as a Warning. (no coordinates are recorded)
LOGWARNING = 3		# For log messages, indicates the message is a Warning, but not as severe as an Error. (no coordinates are recorded)
LOGERROR = 4		# For log messages, indicates the message is an Error.
_log_names = ('DEBUG', 'CARTRIDGE', 'INFO', 'WARNING', 'ERROR')

# This global is required by the system. It is created in ZCartridge._setup.
Player = None
# All functions should be able to call lua functions.
_script = None
# All functions should be able to call callbacks. It would be nicer if those would be per-cartridge, but they aren't called with the cartridge as argument.
_cb = None

def _table_arg (f):
	'''Decorator for functions allowing a table as a single argument.'''
	def ret (self, *a, **ka):
		if len (ka) > 0 or len (a) > 1 or not isinstance (a[0], _lang.Table):
			return f (self, *a, **ka)
		print a[0].dict ()
		return f (self, **a[0].dict ())
	return ret

def _load (file, cbs, config):
	'''Load a cartridge gwc or gwz file or directory for playing; return the ZCartridge object.'''
	# This function used to be a separate module. This is why it looks so messy. These subfunctions are not put at global level, to avoid namespace pollution.
	global _cb
	global _script
	_cb = cbs
	_CARTID = '\x02\x0aCART\x00'
	def _short (file, pos):
		ret = _struct.unpack ('<h', file[pos[0]:pos[0] + 2])[0]
		pos[0] += 2
		return ret
	def _int (file, pos):
		ret = _struct.unpack ('<i', file[pos[0]:pos[0] + 4])[0]
		pos[0] += 4
		return ret
	def _double (file, pos):
		ret = _struct.unpack ('<d', file[pos[0]:pos[0] + 8])[0]
		pos[0] += 8
		return ret
	def _string (file, pos):
		ret = ''
		p = file.find ('\0', pos[0])
		assert p >= 0
		ret = file[pos[0]:p]
		pos[0] = p + 1
		return ret
	def _wshort (num):
		return _struct.pack ('<h', num)
	def _wint (num):
		return _struct.pack ('<i', num)
	def _wdouble (num):
		return _struct.pack ('<d', num)
	def _wstring (s):
		assert '\0' not in s
		return s + '\0'
	def _read_gwc (data, file):
		pos = [len (_CARTID)]	# make this an array so it can be changed by functions.
		num = _short (file, pos)
		offset = [None] * num
		rid = [None] * num
		#data['filetype'] = [None] * num
		data['data'] = [None] * num
		for i in range (num):
			rid[i] = _short (file, pos)
			assert rid[i] < num
			offset[i] = _int (file, pos)
		size = _int (file, pos)
		data['Latitude'] = _double (file, pos)
		data['Longitude'] = _double (file, pos)
		data['Altitude'] = _double (file, pos)
		pos[0] += 4 + 4
		data['MediaId'] = _short (file, pos)
		data['IconId'] = _short (file, pos)
		data['Activity'] = _string (file, pos)
		data['PlayerName'] = _string (file, pos)
		pos[0] += 4 + 4
		data['Name'] = _string (file, pos)
		data['Id'] = _string (file, pos)
		data['Description'] = _string (file, pos)
		data['StartingLocationDescription'] = _string (file, pos)
		data['Version'] = _string (file, pos)
		data['Author'] = _string (file, pos)
		data['URL'] = _string (file, pos)	# unused.
		data['TargetDevice'] = _string (file, pos)
		pos[0] += 4
		data['CompletionCode'] = _string (file, pos)
		data['Copyright'] = 'copyright not included in gwc'
		data['License'] = 'license not included in gwc'
		data['Company'] = 'company not included in gwc'
		data['BuilderVersion'] = 'builder version not included in gwc'
		data['CreateDate'] = 'create date not included in gwc'
		data['UpdateDate'] = 'update date not included in gwc'
		data['PublishDate'] = 'publish date not included in gwc'
		data['LastPlayedDate'] = 'last played date not included in gwc'
		data['TargetDeviceVersion'] = 'target device version not included in gwc'
		assert pos[0] == len (_CARTID) + 2 + num * 6 + 4 + size
		# read lua bytecode.
		pos[0] = offset[0]
		size = _int (file, pos)
		data['data'][0] = file[pos[0]:pos[0] + size]
		# read all other files.
		for i in range (1, num):
			pos[0] = offset[i]
			if file[pos[0]] == '\0':
				continue
			pos[0] += 1
			filetype = _int (file, pos)	# Not used.
			size = _int (file, pos)
			data['data'][rid[i]] = (filetype > 0x10, file[pos[0]:pos[0] + size])
	def _read_gwz (data, gwz, isdir, config):
		# Read gwz file or directory. gwz is path to data. Media files are given their id from the lua source.
		d = {}
		code = None	# This is the name of the lua code file.
		if isdir:
			names = _os.listdir (gwz)
		else:
			z = _zipfile.ZipFile (gwz, 'r')
			names = z.namelist ()
		for n in names:
			ln = n.lower ()
			assert ln not in d
			if isdir:
				d[ln] = open (_os.path.join (gwz, n), 'rb').read ()
			else:
				d[ln] = z.read (n)
			if _os.path.splitext (ln)[1] == _os.extsep + 'lua':
				assert code is None
				code = ln
		# There must be lua code.
		assert code is not None
		data['data'] = [d.pop (code)]
		# Set up extra properties. These should later come from a metadata file.
		for key in ('Name', 'Version', 'Description', 'Author', 'Copyright', 'License', 'Company', 'Activity', 'StartingLocationDescription', 'BuilderVersion', 'Media', 'Icon', 'CreateDate', 'UpdateDate'):
			data[key] = ''
		for key in ('Latitude', 'Longitude', 'Altitude'):
			data[key] = 0.0
		# Set up compile-time settings.
		for key in ('URL', 'TargetDevice', 'TargetDeviceVersion', 'PlayerName', 'CompletionCode', 'Id', 'PublishDate'):
			data[key] = config[key] if key in config else ''
		# Set up boot-time settings.
		for key in ('LastPlayedDate',):
			data[key] = config[key] if key in config else ''
		return d
	def _read_gwz_2 (data, d, config):
		cartridge = ZCartridge._setup (data)
		media = cartridge._getmedia ()
		data['data'] += [None] * len (media)
		map = {}
		for m in range (len (media)):
			assert media[m]._id == m + 1
			r = media[m].Resources.list ()
			if len (r) < 1:
				continue
			r = r[0]	# TODO: choose best, not first; don't warn about rest.
			t = r['Type']
			n = r['Filename']
			map[n.lower ()] = m + 1
			data['data'][m + 1] = (t in ('wav', 'mp3', 'fdl', 'ogg', 'flac', 'au'), d.pop (n.lower ()))
		if len (d) != 0:
			print 'ignoring unused media: %s.' % (', '.join (d.keys ()))
		cartridge._setup_media (data)
		return cartridge
	# Prepare the lua parser.
	_script = _lang.lua ()
	_script.module ('Wherigo', _sys.modules[__name__])
	data = {}
	if type (file) is not str:
		file = file.read ()
	if not file.startswith (_CARTID):
		filename = file
		if _os.path.isdir (file):
			# This is a gwz directory.
			gwc = False
			d = _read_gwz (data, file, True, config)
		else:
			filedata = open (file).read ()
			if filedata.startswith (_CARTID):
				# This is a gwc file.
				gwc  = True
				_read_gwc (data, filedata)
			else:
				# This should be a gwz file.
				gwc = False
				d = _read_gwz (data, file, False, config)
	else:
		filename = 'undefined'
		_read_gwc (data, file)
	env = {}
	for i in config:
		if i.startswith ('env-'):
			env[i[4:]] = config[i]
	env['Downloaded'] = int (env['Downloaded'])
	if not env['CartFilename']:
		env['CartFilename'] = _os.path.splitext (filename)[0]
	if not env['Device']:
		env['Device'] = data['TargetDevice']
	_script.run ('', 'Env', env, name = 'setting Env')
	if not gwc:
		cartridge = _read_gwz_2 (data, d, config)
	else:
		cartridge = ZCartridge._setup (data)
		cartridge._setup_media (data)
	return cartridge

# Class definitions. All these classes are used by lua code and can be inspected and changed by both lua and python code.
class Bearing:
	'A direction from one point to another, in degrees. 0 means north, 90 means east.'
	def __init__ (self, value):
		self.value = value % 360
	def __repr__ (self):
		return 'Bearing (%f)' % self.value

class Distance:
	'A distance between two points.'
	def __init__ (self, value, units = 'meters'):
		if units in ('feet', 'ft'):
			self.value = value * 1609.344 / 5280.
		elif units in ('miles', 'mi'):
			self.value = value * 1609.344
		elif units in ('meters', 'm'):
			self.value = value
		elif units in ('kilometers', 'km'):
			self.value = value * 1000.
		elif units == 'nauticalmiles':
			self.value = value * 1852.
		else:
			raise AssertionError ('invalid length unit %s' % units)
	@_table_arg
	def GetValue (self, units = 'meters', **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to Distance: %s\n' % ka)
		if units in ('feet', 'ft'):
			return self.value / 1609.344 * 5280.
		elif units == 'miles':
			return self.value / 1609.344
		elif units in ('meters', 'm'):
			return self.value
		elif units in ('kilometers', 'km'):
			return self.value / 1000.
		elif units == 'nauticalmiles':
			return self.value / 1852.
		else:
			raise AssertionError ('invalid length unit %s' % units)
	def __call__ (self, units = 'meters'):
		return self.GetValue (units)
	def __repr__ (self):
		return 'Distance (%f, "meters")' % self.value
	def __cmp__ (self, other):
		assert isinstance (other, Distance)
		return self.value - other.value

class ZCommand (object):
	'A command usable on a character, item, zone, etc. Included in ZCharacter.Commands table.'
	@_table_arg
	def __init__ (self, Cartridge = None, Text = '', EmptyTargetListText = '', Enabled = True, CmdWith = False, WorksWithAll = False, WorksWithList = None, MakeReciprocal = True, **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to ZCommand: %s\n' % ka)
		self.Text = Text
		self.EmptyTargetListText = EmptyTargetListText
		self.Enabled = Enabled
		self.CmdWith = CmdWith
		self.WorksWithAll = WorksWithAll
		self.WorksWithList = WorksWithList if WorksWithList is not None  else _script.make_table ()
		self.MakeReciprocal = MakeReciprocal
	def x__getattribute__ (self, key):
		k = 'Get' + key
		obj = super (ZCommand, self)
		if hasattr (obj, k):
			return getattr (obj, k) ()
		else:
			return getattr (obj, key)
	def _show (self):
		return '<ZCommand\n\t' + '\n\t'.join (['%s:%s' % (x, str (getattr (self, x))) for x in dir (self) if not x.startswith ('_')]) + '\n>'

class ZObject (object):
	@_table_arg
	def __init__ (self, Cartridge, Container = None, **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to ZObject: %s\n' % ka)
		self.Active = True
		self.Container = None
		self.Commands = _script.make_table ()
		#self.CommandsArray = _script.make_table ()
		self.CurrentBearing = Bearing (0)
		self.CurrentDistance = Distance (0)
		self.Description = '[Description for this object is not set]'
		self.Icon = None
		#self.Id = None
		self.Inventory = _script.make_table ()
		#self.Locked = False
		self.Media = None
		self.Name = '[Name for this object is not set]'
		self.ObjectLocation = INVALID_ZONEPOINT
		self.Visible = True
		self.Cartridge = Cartridge
		if Cartridge is None:
			# This is a special case for the creation of Player. At that point, the ZCartridge is not yet instantiated.
			# Check that this happens during initialization.
			assert hasattr (ZCartridge, '_settings')
			self.ObjIndex = -1
			return
		if self.Cartridge._store:
			self.ObjIndex = len (self.Cartridge.AllZObjects) + 1
			self.Cartridge.AllZObjects += (self,)
		if Container:
			self.MoveTo (Container)
	def Contains (self, obj):
		if obj == Player:
			return IsPointInZone (Player.ObjectLocation, self)
		p = obj
		while True:
			if p == self:
				return True
			if not hasattr (p, 'Container') or not p.Container:
				return False
			p = p.Container
	def MoveTo (self, owner):
		if self.Container:
			l = self.Container.Inventory.list ()
			if self in l:
				self.Container.Inventory.pop (l.index (self))
		self.Container = owner
		if self.Container:
			self.Container.Inventory += (self,)
	def _is_visible (self, debug):
		if not (debug or (self.Active and self.Visible)):
			return False
		if isinstance (self, Zone):
			return True
		if self.Container == None:
			return False
		if self.Container == Player:
			return True
		if not self.Container.Active or not isinstance (self.Container, Zone):
			return False
		if self.Container.ShowObjects == 'OnEnter':
			if self.Container.State != 'Inside':
				return False
		elif self.Container.ShowObjects == 'OnProximity':
			if self.Container.State not in ('Inside', 'Proximity'):
				return False
		elif self.Container.ShowObjects == 'Always':
			return True
		else:
			print ('invalid (or at least unknown) value for ShowObjects: %s' % self.Container.ShowObjects)
		return True
	def _show (self):
		return '<ZObject\n\t' + '\n\t'.join (['%s:%s' % (x, str (getattr (self, x))) for x in dir (self) if not x.startswith ('_')]) + '\n>'
	def __str__ (self):
		return 'a %s instance' % self.__class__.__name__
	@classmethod
	def made (cls, obj):
		return isinstance (obj, cls)
	def __getattribute__ (self, key):
		if key == 'InsideOfZones':
			ret = []
			pos = self._get_pos ()
			if pos is None:
				return None
			for i in self.Cartridge.AllZObjects.list ():
				if not isinstance (i, Zone) or not i.Active:
					continue
				if IsPointInZone (pos, i):
					ret.append (i)
			return _script.make_table (ret)
		else:
			return super (ZObject, self).__getattribute__ (key)
	def _get_pos (self):
		if isinstance (self, Zone):
			return self.OriginalPoint
		if not isinstance (self, (ZCharacter, ZItem)):
			return None
		if not hasattr (self, 'ObjectLocation') or not self.ObjectLocation:
			if hasattr (self, 'Container') and self.Container:
				return self.Container._get_pos ()
			else:
				#print ('Warning: object %s (type %s) has no location' % (self.Name, type (self)))
				return None
		return self.ObjectLocation

class ZonePoint (object):
	'A specific geographical point, or the INVALID_ZONEPOINT constant to represent no value.'
	@_table_arg
	def __init__ (self, latitude = 0, longitude = 0, altitude = 0, **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to ZonePoint: %s\n' % ka)
		# Don't trigger update_map when constructing new ZonePoints.
		object.__setattr__ (self, 'latitude', latitude)
		object.__setattr__ (self, 'longitude', longitude)
		object.__setattr__ (self, 'altitude', altitude)
	def __setattr__ (self, key, value):
		object.__setattr__ (self, key, value)
		if key in ('latitude', 'longitude'):
			_cb.update_map ()
	def __repr__ (self):
		return 'ZonePoint (%f, %f, %f)' % (self.latitude, self.longitude, self.altitude)

# This class exists according to the documentation, but I've not seen any use of it by an actual cartridge.
#class ZReciprocalCommand (ZObject):
#	'Unsure.'
#	def __init__ (self, *a):
#		pass

# All the following classes implement the ZObject interface.
class ZCartridge (ZObject):
	def __init__ (self):
		self.AllZObjects = _script.make_table () # This must be done before ZObject.__init__, because that registers this object.
		self._store = True
		ZObject.__init__ (self, self)
		self.ZVariables = _script.make_table ()
		self.OnEnd = None
		self.OnRestore = None
		self.OnStart = None
		self.OnSync = None
		# Settings from the metadata.
		self.Name = ZCartridge._settings['Name']
		self.Description = ZCartridge._settings['Description']
		self.Version = ZCartridge._settings['Version']
		self.Author = ZCartridge._settings['Author']
		self.Copyright = ZCartridge._settings['Copyright']	# This wasn't there originally.
		self.License = ZCartridge._settings['License']	# This wasn't there originally.
		self.Company = ZCartridge._settings['Company']
		self.Activity = ZCartridge._settings['Activity']
		self.StartingLocation = ZonePoint (ZCartridge._settings['Latitude'], ZCartridge._settings['Longitude'], ZCartridge._settings['Altitude'])
		self.StartingLocationDescription = ZCartridge._settings['StartingLocationDescription']
		self.BuilderVersion = ZCartridge._settings['BuilderVersion']
		self.CreateDate = ZCartridge._settings['CreateDate']
		self.UpdateDate = ZCartridge._settings['UpdateDate']
		self.Sound = _script.make_table ()
		self.Image = _script.make_table ()
		# With metadata, this is the point where images and sounds are created. Then also Icon and Media can be set.
		# Now they are ignored. They are not normally used by the cartridge anyway.
		self.Icon = None
		self.Media = None
		# Compile-time settings.
		self.TargetDevice = ZCartridge._settings['TargetDevice']
		self.TargetDeviceVersion = ZCartridge._settings['TargetDeviceVersion']
		self.Id = ZCartridge._settings['Id']
		self.PublishDate = ZCartridge._settings['PublishDate']
		# Boot-time settings.
		self.LastPlayedDate = ZCartridge._settings['LastPlayedDate']
		# ?
		self.UseLogging = False	# ?
		self.CountryId = 0	# ?
		self.StateId = '1'	# ?
		self.Complete = False	# ?
		del ZCartridge._settings
		self._mediacount = 1
	def GetAllOfType (self, type):
		return _script.make_table ([x for x in self.AllZObjects if isinstance (x, ZObject) and x.__class__.__name__ == type])
	def RequestSync (self):
		_cb.save ()
	@classmethod
	def _new (cls):
		'Clean up all objects and data.'
		global Player, _script
		Player = None
		_script = None
	@classmethod
	def _setup (cls, cart):
		global Player
		cls._settings = cart
		Player = ZCharacter (None)
		Player.Name = cart['PlayerName']
		Player.CompletionCode = cart['CompletionCode']
		# For technical reasons, the python value wherigo.Player is not available in lua without the statement below. See python-lua manual page for details.
		_script.run ('Wherigo.Player = Player', 'Player', Player, name = 'setting Player variable')
		ret = _script.run (cart['data'][0], name = 'cartridge setup')[0]
		# Create a starting marker object, which can be used for drawing a marker on the map, but which is invisible for the cartridge.
		global _starting_marker
		_starting_marker = ZItem (ret)
		_starting_marker.ObjectLocation = ret.StartingLocation
		_starting_marker.Name = 'The start of this cartridge'
		_starting_marker.Media = ret.Icon
		_starting_marker.Description = ret.StartingLocationDescription
		return ret
	def _setup_media (self, cart):
		self._image = {}
		self._sound = {}
		for i in self.AllZObjects.list ():
			if not isinstance (i, ZMedia):
				continue
			if i._id not in cart['data']:
				continue
			if cart['data'][i._id][0]:
				self._sound[i.Id] = cart['data'][i._id][1]
			else:
				self._image[i.Id] = cart['data'][i._id][1]
	def _getmedia (self):
		return [x for x in self.AllZObjects.list () if isinstance (x, ZMedia) and x._id > 0]
	def _update (self, position, time):
		self._time = time
		# Update Timers. Do this before everything else, so Remaining is set correctly when callbacks are invoked.
		for i in self.AllZObjects.list ():
			if isinstance (i, ZTimer) and i._target != None:
				i.Remaining = i._target - time
		update_all = False
		if not position:
			return False
		Player.ObjectLocation = ZonePoint (position.lat, position.lon, position.alt)
		for i in self.AllZObjects.list ():
			# Update all object distances and bearings.
			if (isinstance (i, ZItem) and i.Container is not Player) or isinstance (i, ZCharacter):
				if not i.Active:
					continue
				pos = i._get_pos ()
				if not pos:
					continue
				i.CurrentDistance, i.CurrentBearing = VectorToPoint (Player.ObjectLocation, pos)
			# Update container info, and call OnEnter or OnExit.
			elif isinstance (i, Zone):
				if i._active != i.Active:
					# TODO: Doing this here means that OnSetActive fires after the lua callback has returned. Setting a zone active and immediately inactive doesn't make it fire, while it should make it fire twice.
					i._active = i.Active
					if hasattr (i, 'OnSetActive'):
						#print 'OnSetActive %s' % i.Name
						i.OnSetActive (i)
						update_all = True
				if not i.Active:
					continue
				inside = IsPointInZone (Player.ObjectLocation, i)
				if inside != i._inside:
					update_all = True
					i._inside = inside
					if inside:
						if i._state == 'NotInRange' and hasattr (i, 'OnDistant') and i.OnDistant:
							#print 'OnDistant 1 %s' % i.Name
							i.OnDistant (i)
						if i._state != 'Proximity' and hasattr (i, 'OnProximity') and i.OnProximity:
							#print 'OnProximity %s' % i.Name
							i.OnProximity (i)
						if hasattr (i, 'OnEnter') and i.OnEnter:
							#print 'OnEnter %s' % i.Name
							i.OnEnter (i)
					else:
						#print 'no longer inside %s' % i.Name
						if hasattr (i, 'OnExit') and i.OnExit:
							#print 'OnExit %s' % i.Name
							i.OnExit (i)
				if inside:
					i.State = 'Inside'
					i._state = i.State
				else:
					# See how close we are.
					i.CurrentDistance, i.CurrentBearing = VectorToZone (Player.ObjectLocation, i)
					if i.CurrentDistance < i.ProximityRange:
						if i._state == 'NotInRange' and hasattr (i, 'OnDistant') and i.OnDistant:
							#print 'OnDistant 2 %s (from %s)' % (i.Name, i.State)
							i.OnDistant (i)
							update_all = True
						i.State = 'Proximity'
					elif i.DistanceRange < Distance (0) or i.CurrentDistance < i.DistanceRange:
						if i._state == 'Inside' and hasattr (i, 'OnProximity') and i.OnProximity:
							#print 'OnProximity %s' % i.Name
							i.OnProximity (i)
							update_all = True
						i.State = 'Distant'
					else:
						if i._state == 'Inside' and hasattr (i, 'OnProximity') and i.OnProximity:
							#print 'OnProximity %s' % i.Name
							i.OnProximity (i)
							update_all = True
						if i._state in ('Inside', 'Proximity') and hasattr (i, 'OnDistant') and i.OnDistant:
							#print 'OnDistant 3 %s (from %s)' % (i.Name, i.State)
							i.OnDistant (i)
							update_all = True
						i.State = 'NotInRange'
					if i.State != i._state:
						#print 'new state for %s: %s' % (i.Name, i.State)
						s = i._state
						i._state = i.State
						attr = 'On' + i.State
						if hasattr (i, attr) and getattr (i, attr):
							#print '%s %s (from %s)' % (attr, i.Name, s)
							getattr (i, attr) (i)
							update_all = True
		return update_all
	def _inside_list (self):
		return [zone for zone in self.AllZObjects.list () if isinstance (zone, Zone) and zone.Active and zone._inside]
	def _reschedule_timers (self):
		for t in self.AllZObjects.list ():
			if isinstance (t, ZTimer):
				t._reschedule ()

class ZCharacter (ZObject):
	@_table_arg
	def __init__ (self, Cartridge, Container = None, **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to ZCharacter: %s\n' % ka)
		#print 'making character'
		ZObject.__init__ (self, Cartridge, Container)
		self.name = 'Unnamed character'
		self.PositionAccuracy = Distance (5)

class ZTimer (ZObject):
	'A timer object allowing time or activity tracking.'
	# attributes: Type ('Countdown'|'Interval'), Duration (Number), Id, Name, Visible
	@_table_arg
	def __init__ (self, Cartridge, Type = 'Countdown', Duration = -1, Remaining = -1, OnStart = None, OnStop = None, OnTick = None, **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to ZTimer: %s\n' % ka)
		ZObject.__init__ (self, Cartridge)
		self.Type = Type
		self.Duration = Duration
		self.Remaining = Remaining
		self.OnStart = OnStart
		self.OnStop = OnStop
		self.OnTick = OnTick
		self._target = None	# time for next tick, or None.
		self._source = None
	def Start (self):
		if self._target is not None:
			print 'Not starting timer: already running.'
			return
		if self.OnStart:
			#print 'OnStart timer %s' % self.Name
			self.OnStart (self)
		#print 'Timer started, settings:\n' + '\n'.join (['%s:%s' % (x, getattr (self, x)) for x in dir (self) if not x.startswith ('_')])
		if self.Remaining < 0:
			self.Remaining = self.Duration
		self._source = _cb.add_timer (self.Remaining, self.Tick)
		self._target = self.Cartridge._time + self.Duration
	def Stop (self):
		if self._target is None:
			print 'Not stopping timer: not running.'
			return
		_cb.remove_timer (self._source)
		self._target = None
		self._source = None
		if self.OnStop:
			#print 'OnStop %s' % self.Name
			self.OnStop (self)
		#print 'Timer stopped, settings:\n' + '\n'.join (['%s:%s' % (x, getattr (self, x)) for x in dir (self) if not x.startswith ('_')])
	def _reschedule (self):
		if self._target is None:
			return
		_cb.remove_timer (self._source)
		self._source = _cb.add_timer (self.Remaining, self.Tick)
	def Tick (self):
		if self.Type == 'Interval':
			now = self.Cartridge._time
			# If this is called manually, skip the remaining time.
			if self._target > now:
				self._target = now
			self._target += self.Duration
			self._target.Remaining = self._target - now
			# If execution is too slow, skip ticks.
			if self._target < now:
				self._target = now
			self._source = _cb.add_timer (self._target - now, self.Tick)
		else:
			self._target = None
			self._source = None
			self.Remaining = -1
		if self.OnTick:
			#print 'OnTick %s' % self.Name
			self.OnTick (self)
		#print 'Timer ticked, settings:\n' + '\n'.join (['%s:%s' % (x, getattr (self, x)) for x in dir (self) if not x.startswith ('_')])
		return False

class ZInput (ZObject):
	'A user input field.'
	@_table_arg
	def __init__ (self, Cartridge, Text = '', OnGetInput = None, **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to ZInput: %s\n' % ka)
		ZObject.__init__ (self, Cartridge)
		self.Text = Text
		self.OnGetInput = OnGetInput

class ZItem (ZObject):
	'An item which can be placed in a zone or held by a character.'
	@_table_arg
	def __init__ (self, Cartridge, Container = None, **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to ZItem: %s\n' % ka)
		ZObject.__init__ (self, Cartridge, Container)

class Zone (ZObject):
	'Geographical area defined by several ZonePoints.'
	@_table_arg
	def __init__ (self, Cartridge, OriginalPoint = INVALID_ZONEPOINT, ShowObjects = 'OnEnter', State = 'NotInRange', Inside = False, OnEnter = None, OnExit = None, OnProximity = None, OnDistant = None, ProximityRange = Distance (-1), DistanceRange = Distance (-1), **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to Zone: %s\n' % ka)
		ZObject.__init__ (self, Cartridge)
		self.OriginalPoint = OriginalPoint
		self.Points = _script.make_table ()
		self.ShowObjects = ShowObjects
		self.State = State
		self._inside = Inside
		self._active = True
		self._state = 'Inside' if Inside else 'NotInRange'
		self.OnEnter = OnEnter
		self.OnExit = OnExit
		self.OnProximity = OnProximity
		self.OnDistant = OnDistant
		self.ProximityRange = ProximityRange
		self.DistanceRange = DistanceRange
	def __str__ (self):
		if hasattr (self, 'OriginalPoint'):
			return '<Zone at %s>' % str (self.OriginalPoint)
		else:
			return '<Zone>'

class ZTask (ZObject):
	'A task the user can attempt to accomplish.'
	@_table_arg
	def __init__ (self, Cartridge, Complete = False, CorrectState = False, **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to ZTask: %s\n' % ka)
		ZObject.__init__ (self, Cartridge)
		self.Complete = Complete
		self.CorrectState = CorrectState

class ZMedia (ZObject):
	'A media file such as an image or sound.'
	@_table_arg
	def __init__ (self, Cartridge, **ka):
		if len (ka) > 0:
			sys.stderr.write ('unknown commands given to ZMedia: %s\n' % ka)
		ZObject.__init__ (self, Cartridge)
		self._id = Cartridge._mediacount
		Cartridge._mediacount += 1

# These functions are called from lua to make the application do things.
def Dialog (table):
	'Displays a dialog to the user. Parameter table may include two named values: Text, a string value containing the message to display; and Media, a ZMedia object to display in the dialog.'
	_cb.dialog (table)

def MessageBox (table):
	'Displays a dialog to the user with the possibility of user actions triggering additional events. Parameter table may take four named values: Text, a string value containing the message to display; Media, a ZMedia object to display in the dialog; Buttons, a table of strings to display as button options for the user; and Callback, a function reference to a function taking one parameter, the name of the button the user pressed to dismiss the dialog.'
	_cb.message (table)

def GetInput (inp):
	'Displays the provided ZInput dialog and returns the value entered or selected by the user.'
	_cb.get_input (inp)

def PlayAudio (media):
	'Plays a sound file. Single parameter is a ZMedia object representing a sound file.'
	_cb.play (media)

def ShowStatusText (text):
	'Updates the status text displayed on PPC players to the specified value. At this time, the Garmin Colorado does not support status text.'
	_cb.set_status (text)

def Command (text):
	if text == 'SaveClose':
		_cb.save ()
		_cb.quit ()
	elif text == 'DriveTo':
		_cb.drive_to ()
	elif text == 'StopSound':
		_cb.stop_sound ()
	elif text == 'Alert':
		_cb.alert ()
	else:
		raise AssertionError ('unknown command %s' % text)

def LogMessage (text, level = LOGCARTRIDGE):
	'Allows messages to be added to the cartridge play log at one of the defined log levels. Parameters are the actual text and an optional log level at which the text is displayed. If level is not specified it defaults to LOGCARTRIDGE. There are two possible calling conventions: as individual parameters or as a table parameter with named values.'
	if isinstance (text, dict):
		if 'Level' in text:
			level = text['Level']
		text = text['Text']
	level = int (level + .5)
	assert 0 <= level < _log_names
	_cb.log (level, _log_names[level], text)

def ShowScreen (screen, item = None):
	'Switches the currently displayed screen to one specified by the screen parameter. The several SCREEN constants defined in the Wherigo object allow the screen to be specified. If DETAILSCREEN is specified, the optional second parameter item specifies the zone, character, item, etc. to display the detail screen of.'
	screen = int (screen + .5)
	assert 0 <= screen < len (_screen_names)
	_cb.show (screen, item)

# These functions seem to be for doing dirty work which is too slow or annoying in lua...
def NoCaseEquals (s1, s2):
	'Compares two strings for equality, ignoring case. Uncertain parameters.'
	if isinstance (s1, str):
		s1 = s1.lower ()
	if isinstance (s2, str):
		s2 = s2.lower ()
	return s1 == s2

# This class exists according to the documentation, but I've not seen any use of it by an actual cartridge.
#def Inject ():
#	'Unknown parameters and function.'
#	pass

def _intersect (point, segment, name = ''):
	'Compute whether a line from the north pole to point intersects with the segment. Return 0 or 1.'
	# Use simple interpolation for latitude. TODO: this is not correct on the spherical surface.
	lon1 = segment[0].longitude
	lon2 = segment[1].longitude
	lonp = point.longitude
	if (lon2 - lon1) % 360 > 180:
		# lon1 > lon2
		if (lonp - lon2) % 360 > 180 or (lon1 - lonp) % 360 >= 180 or lon1 == lonp:
			return 0
		lat = segment[0].latitude + (segment[1].latitude - segment[0].latitude) * ((lonp - lon2) % 360) / ((lon1 - lon2) % 360)
	else:
		if (lonp - lon1) % 360 > 180 or (lon2 - lonp) % 360 >= 180 or lon2 == lonp:
			return 0
		lat = segment[0].latitude + (segment[1].latitude - segment[0].latitude) * ((lonp - lon1) % 360) / ((lon2 - lon1) % 360)
	if lat > point.latitude:
		return 1
	return 0

def IsPointInZone (point, zone):
	'Unknown parameters; presumably checks whether a specified ZonePoint is within a specified Zone.'
	# Spherical trigonometry: every closed curve cuts the world in two pieces. If point is in the same piece as the OriginalPoint, it is considered "inside".
	# This means that any line from OriginalPoint to point has an even number of intersections with zone segments.
	# This line doesn't need to be the shortest path. It is much easier if it isn't. I'm using a two-segment line: One segment straight north to the pole, one straight south to OriginalPoint.
	num = 0
	points = zone.Points.list ()
	points += (points[0],)
	for i in range (len (points) - 1):
		num += _intersect (point, (points[i], points[i + 1], zone.Name))
		num += _intersect (zone.OriginalPoint, (points[i], points[i + 1], zone.Name))
	return num % 2 == 0

def VectorToSegment (point, p1, p2):
	'Unknown parameters and function.'
	# Compute shortest distance and bearing to get from point to anywhere on segment.
	d1, b1 = VectorToPoint (p1, point)
	d1 = _math.radians (d1.GetValue ('nauticalmiles') / 60.)
	ds, bs = VectorToPoint (p1, p2)
	dist = _math.asin (_math.sin (d1) * _math.sin (_math.radians (b1.value - bs.value)))
	dat = _math.acos (_math.cos (d1) / _math.cos (dist))
	if dat <= 0:
		return VectorToPoint (point, p1)
	elif dat >= _math.radians (ds.GetValue ('nauticalmiles') / 60.):
		return VectorToPoint (point, p2)
	intersect = TranslatePoint (p1, Distance (dat * 60, 'nauticalmiles'), bs)
	return VectorToPoint (point, intersect)

def VectorToZone (point, zone):
	'Unknown parameters and function.'
	# Compute shortest distance and bearing to get from point inside a zone.
	if IsPointInZone (point, zone):
		return Distance (0), Bearing (0)
	# Use VectorToSegment multiple times.
	points = zone.Points.list ()
	current = VectorToSegment (point, points[-1], points[0])
	for p in range (1, len (points)):
		this = VectorToSegment (point, points[p - 1], points[p])
		if this[0].value < current[0].value:
			current = this
	return current

def VectorToPoint (p1, p2):
	'd,b=VectorToPoint(zonepoint1,zonepoint2). Accepts two ZonePoint instance. Returns distance and bearing from zonepoint1 to zonepoint2. d is a Distance instance; b is a Bearing instance.'
	# Special case for points on the same longitude (in particular, for p1 == p2).
	if p1.longitude == p2.longitude:
		return Distance (abs (p1.latitude - p2.latitude) * 60, 'nauticalmiles'), Bearing (0 if p1.latitude <= p2.latitude else 180)
	lat1 = _math.radians (p1.latitude)
	lon1 = _math.radians (p1.longitude)
	lat2 = _math.radians (p2.latitude)
	lon2 = _math.radians (p2.longitude)
	# Formula of haversines. This is a numerically stable way of determining the distance.
	dist = 2 * _math.asin (_math.sqrt (_math.sin ((lat1 - lat2) / 2) ** 2 + _math.cos (lat1) * _math.cos (lat2) * _math.sin ((lon1 - lon2) / 2) ** 2))
	# And the bearing.
	bearing = _math.atan2 (_math.sin (lon2 - lon1) * _math.cos(lat2), _math.cos (lat1) * _math.sin (lat2) - _math.sin (lat1) * _math.cos (lat2) * _math.cos (lon2 - lon1))
	# To get a distance, use nautical miles: 1 nautical mile is by definition equal to 1 minute, so 60 nautical miles is 1 degree.
	return Distance (_math.degrees (dist) * 60, 'nauticalmiles'), Bearing (_math.degrees (bearing))

def TranslatePoint (point, distance, bearing):
	'''Returns a ZonePoint object calculated by starting at the provided point and moving Distance from that point at the specified angle.
	Signature is zonepoint=Wherigo.TranslatePoint(startzonepoint, distance, bearing), where
		startzonepoint is an instance of ZonePoint,
		distance is an instance of Distance,
		and bearing is an Instance of Bearing.'''
	d = _math.radians (distance.GetValue ('nauticalmiles') / 60.)
	b = _math.radians (bearing.value)
	lat1 = _math.radians (point.latitude)
	lat2 = _math.asin (_math.sin (lat1) * _math.cos (d) + _math.cos (lat1) * _math.sin (d) * _math.cos(b))
	dlon = _math.atan2 (_math.sin(b) * _math.sin (d) * _math.cos (lat1), _math.cos (d) - _math.sin (lat1) * _math.sin (lat2))
	return ZonePoint (_math.degrees (lat2), point.longitude + _math.degrees (dlon), point.altitude)
