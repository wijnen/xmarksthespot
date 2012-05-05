# module containing wherigo stuff that will be accessed by the lua code from the cartridge.

import sys
import math
import time
import gtk
import gobject
import lua

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

# Class definitions. All these classes are used by lua code and can be inspected and changed by both lua and python code.
class Bearing:
	'A direction from one point to another, in degrees. 0 means north, 90 means east.'
	def __init__ (self, value):
		self.value = value % 360
	def __repr__ (self):
		return 'Bearing (%f)' % self.value

class Distance:
	'A distance between two points.'
	def __init__ (self, value, unit = 'meters'):
		if unit == 'feet':
			self.value = value * 1609.344 / 5280.
		elif unit == 'miles':
			self.value = value * 1609.344
		elif unit == 'meters':
			self.value = value
		elif unit == 'kilometers':
			self.value = value * 1000.
		elif unit == 'nauticalmiles':
			self.value = value * 1852.
		else:
			raise AssertionError ('invalid length unit %s' % unit)
	def GetValue (self, luaself, unit = 'meters'):
		if unit in ('feet', 'ft'):
			return self.value / 1609.344 * 5280.
		elif unit == 'miles':
			return self.value / 1609.344
		elif unit in ('meters', 'm'):
			return self.value
		elif unit in ('kilometers', 'km'):
			return self.value / 1000.
		elif unit == 'nauticalmiles':
			return self.value / 1852.
		else:
			raise AssertionError ('invalid length unit %s' % unit)
	def __repr__ (self):
		return 'Distance (%f, "meters")' % self.value

class ZCommand:
	'A command usable on a character, item, zone, etc. Included in ZCharacter.Commands table.'
	def __init__ (self, arg):
		self.Text = arg['Text']
		self.EmptyTargetListText = arg['EmptyTargetListText']
		self.Enabled = arg['Enabled']
		self.CmdWith = arg['CmdWith']
	def __repr__ (self):
		return '<ZCommand\n\t' + '\n\t'.join (['%s:%s' % (x, str (getattr (self, x))) for x in dir (self) if not x.startswith ('_')]) + '\n>'

class ZObject (object):
	def __init__ (self, cartridge, container = None):
		self.Active = True
		self.Cartridge = cartridge
		self.Container = container
		self.Commands = []
		self.CommandsArray = []
		self.CurrentBearing = 0
		self.CurrentDistance = 0
		self.Description = '[Description for this object is not set]'
		self.Icon = None
		self.Id = None
		self.Inventory = []
		self.Media = None
		self.Name = '[Name for this object is not set]'
		self.ObjectLocation = INVALID_ZONEPOINT
		self.ObjIndex = len (cartridge.AllZObjects) + 1
		self.Visible = True
		cartridge.AllZObjects += (self,)
	def _show (self):
		return '<ZObject\n\t' + '\n\t'.join (['%s:%s' % (x, str (getattr (self, x))) for x in dir (self) if not x.startswith ('_')]) + '\n>'

class ZonePoint:
	'A specific geographical point, or the INVALID_ZONEPOINT constant to represent no value.'
	def __init__ (self, latitude, longitude, altitude):
		self.latitude = latitude
		self.longitude = longitude
		self.altitude = altitude
	def __repr__ (self):
		return 'ZonePoint (%f, %f, %f)' % (self.latitude, self.longitude, self.altitude)

class ZReciprocalCommand (ZObject):
	'Unsure.'
	def __init__ (self, *a):
		print a, self, sys._getframe().f_code.co_name
		pass

# All the following classes implement the ZObject interface.
class ZCartridge (ZObject):
	_instance = None
	def __new__ (cls, *a, **aa):
		if cls._instance is None:
			cls._instance = super (ZCartridge, cls).__new__ (cls, *a, **aa)
			cls._instance.AllZObjects = [] # This must be done before ZObject.__init__, because that registers this object.
			ZObject.__init__ (cls._instance, cls._instance)
			cls._instance._mediacount = -1
			cls._instance.Activity = 'Undefined'
			cls._instance.Author = 'Undefined'
			cls._instance.BuilderVersion = None
			cls._instance.Company = None
			cls._instance.Complete = False
			cls._instance.CountryId = 0
			cls._instance.CreateDate = None
			cls._instance.Description = 'Undefined'
			cls._instance.Icon = ZMedia (cls._instance)
			cls._instance.Icon.Id = None
			cls._instance.Id = 'Undefined'
			cls._instance.LastPlayedDate = None
			cls._instance.Media = ZMedia (cls._instance)
			cls._instance.Media.Id = None
			cls._instance.MsgBoxCBFuncs = []
			cls._instance.Name = 'Undefined'
			cls._instance.PublishDate = None
			cls._instance.StartingLocation = INVALID_ZONEPOINT
			cls._instance.StartingLocationDescription = 'Undefined'
			cls._instance.StateId = '1'
			cls._instance.TargetDevice = 'Undefined'
			cls._instance.TargetDeviceVersion = None
			cls._instance.UpdateDate = None
			cls._instance.UseLogging = False
			cls._instance.Version = 'Undefined'
			cls._instance.Visible = True
			cls._instance.ZVariables = []
			cls._instance.OnEnd = None
			cls._instance.OnRestore = None
			cls._instance.OnStart = None
			cls._instance.OnSync = None
		return cls._instance
	def __init__ (self):
		pass
	def RequestSync (self, luaself):
		self._cb.save ()
	def _setup (self, cart, cbs, script):
		global Player
		self.Activity = cart.gametype
		self.Author = cart.author
		self.Description = cart.description
		self.Icon.Id = cart.iconId
		self.Id = cart.guid
		self.Media.Id = cart.splashId
		self.Name = cart.name
		self.StartingLocation = ZonePoint (cart.latitude, cart.longitude, cart.altitude)
		self.StartingLocationDescription = cart.startdesc
		self.TargetDevice = cart.device
		self.Version = cart.version
		self._mediacount = 1
		self._image = {}
		self._sound = {}
		self._cb = cbs
		# According to the wiki, both the global "Player" and "wherigo.Player" should be a reference to the current player.
		# For technical reasons, the python value wherigo.Player is not available in lua without the statement below.
		Player = ZCharacter (self)
		# Player should not be in the list, and it should have a negative index.
		Player.ObjIndex = -1
		Player.Name = cart.user
		Player.CompletionCode = cart.completion_code
		script.run ('Wherigo.Player = Player', 'Player', Player, 'setting Player variables')
		self.AllZObjects.pop ()
		ret = script.run (cart.data[0])[0]
		# Set up media.
		for i in self.AllZObjects:
			if not isinstance (i, ZMedia) or i._id < 1:
				continue
			r = lua.as_list (i.Resources)[0]
			if r['Type'] in ('wav', 'mp3'):
				self._sound[i.Id] = cart.data[i._id]
			else:
				px = gtk.gdk.PixbufLoader ()
				px.write (cart.data[i._id])
				px.close ()
				self._image[i.Id] = px.get_pixbuf ()
		return ret

class ZCharacter (ZObject):
	def __init__ (self, cartridge):
		#print 'making character'
		ZObject.__init__ (self, cartridge)
		self.name = 'Unnamed character'
		self.InsideOfZones = []
		self.Inventory = []
		self.ObjectLocation = INVALID_ZONEPOINT
		self.PositionAccuracy = Distance (5)
		self.Visible = False

class ZTimer (ZObject):
	'A timer object allowing time or activity tracking.'
	# attributes: Type ('Countdown'|'Interval'), Duration (Number), Id, Name, Visible
	def __init__ (self, cartridge):
		ZObject.__init__ (self, cartridge)
		self.Type = 'Countdown'
		self.Duration = -1
		self.Remaining = -1
		self.OnStart = None
		self.OnStop = None
		self.OnTick = None
		self._target = None	# time for next tick, or None.
		self._source = None
	def Start (self, luaself):
		if self._target is not None:
			print 'Not starting timer: already running.'
			return
		if self.OnStart:
			self.OnStart (self)
		#print 'Timer started, settings:\n' + '\n'.join (['%s:%s' % (x, getattr (self, x)) for x in dir (self) if not x.startswith ('_')])
		if self.Remaining < 0:
			self.Remaining = self.Duration
		self._source = gobject.timeout_add (int (self.Remaining * 1000), self.Tick, self)
		self._target = time.time () + self.Duration
	def Stop (self, luaself):
		if self._target is None:
			print 'Not stopping timer: not running.'
			return
		gobject.source_remove (self._source)
		self._target = None
		self._source = None
		if self.OnStop:
			self.OnStop (self)
		#print 'Timer stopped, settings:\n' + '\n'.join (['%s:%s' % (x, getattr (self, x)) for x in dir (self) if not x.startswith ('_')])
	def Tick (self, luaself):
		if self.Type == 'Interval':
			self._target += self.Duration
			now = time.time ()
			if self._target < now:
				self._target = now
			self._source = gobject.timeout_add (int ((self._target - now) * 1000), self.Tick, self)
		else:
			self._target = None
			self._source = None
			self.Remaining = -1
		if self.OnTick:
			self.OnTick (self)
		#print 'Timer ticked, settings:\n' + '\n'.join (['%s:%s' % (x, getattr (self, x)) for x in dir (self) if not x.startswith ('_')])
		return False

class ZInput (ZObject):
	'A user input field.'
	def __init__ (self, cartridge):
		ZObject.__init__ (self, cartridge)

class ZItem (ZObject):
	'An item which can be placed in a zone or held by a character.'
	def __init__ (self, arg):
		ZObject.__init__ (self, arg.Cartridge, arg.Container)

class Zone (ZObject):
	'Geographical area defined by several ZonePoints.'
	def __init__ (self, cartridge):
		ZObject.__init__ (self, cartridge)
		self._inside = False
		self._active = True
		self._state = 'NotInRange'
		self.OriginalPoint = INVALID_ZONEPOINT
	def __str__ (self):
		return '<Zone at %s>' % str (self.OriginalPoint)

class ZTask (ZObject):
	'A task the user can attempt to accomplish.'
	def __init__ (self, cartridge):
		ZObject.__init__ (self, cartridge)

class ZMedia (ZObject):
	'A media file such as an image or sound.'
	def __init__ (self, cartridge):
		ZObject.__init__ (self, cartridge)
		self._id = cartridge._mediacount
		if cartridge._mediacount > 0:
			cartridge._mediacount += 1

# These functions are called from lua to make the application do things.
def Dialog (table):
	'Displays a dialog to the user. Parameter table may include two named values: Text, a string value containing the message to display; and Media, a ZMedia object to display in the dialog.'
	ZCartridge ()._cb.dialog (table)

def MessageBox (table):
	'Displays a dialog to the user with the possibility of user actions triggering additional events. Parameter table may take four named values: Text, a string value containing the message to display; Media, a ZMedia object to display in the dialog; Buttons, a table of strings to display as button options for the user; and Callback, a function reference to a function taking one parameter, the name of the button the user pressed to dismiss the dialog.'
	ZCartridge ()._cb.message (table)

def GetInput (inp):
	'Displays the provided ZInput dialog and returns the value entered or selected by the user.'
	ZCartridge ()._cb.get_input (inp)

def PlayAudio (media):
	'Plays a sound file. Single parameter is a ZMedia object representing a sound file.'
	ZCartridge ()._cb.play (media)

def ShowStatusText (text):
	'Updates the status text displayed on PPC players to the specified value. At this time, the Garmin Colorado does not support status text.'
	ZCartridge ()._cb.set_status (text)

def Command (text):
	if text == 'SaveClose':
		ZCartridge ()._cb.save ()
		ZCartridge ()._cb.quit ()
	elif text == 'DriveTo':
		ZCartridge ()._cb.drive_to ()
	elif text == 'StopSound':
		ZCartridge ()._cb.stop_sound ()
	elif text == 'Alert':
		ZCartridge ()._cb.alert ()
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
	ZCartridge ()._cb.log (level, _log_names[level], text)

def ShowScreen (screen, item = None):
	'Switches the currently displayed screen to one specified by the screen parameter. The several SCREEN constants defined in the Wherigo object allow the screen to be specified. If DETAILSCREEN is specified, the optional second parameter item specifies the zone, character, item, etc. to display the detail screen of.'
	screen = int (screen + .5)
	assert 0 <= screen < len (_screen_names)
	ZCartridge ()._cb.show (screen, item)

# These functions seem to be for doing dirty work which is too slow or annoying in lua...
def NoCaseEquals (s1, s2):
	'Compares two strings for equality, ignoring case. Uncertain parameters.'
	print sys._getframe().f_code.co_name
	return s1.lower () == s2.lower ()

def Inject ():
	'Unknown parameters and function.'
	print sys._getframe().f_code.co_name
	pass

def _intersect (point, segment):
	'Compute whether a line from the north pole to point intersects with the segment. Return 0 or 1.'
	lon1 = segment[0].longitude
	lon2 = segment[1].longitude
	# Sort lon1 and lon2, so the shortest curve is used.
	if (lon2 - lon1) % 360 > 180:
		lon1 = segment[1].longitude
		lon2 = segment[0].longitude
	d = lon2 - lon1
	lonp = point.longitude
	if (lonp - lon1) % 360 > 180 or (lon1 + d - lonp) % 360 > 180:
		return 0
	# Use simple interpolation. TODO: this is not correct on the spherical surface.
	lat = segment[0].latitude + (segment[1].latitude - segment[0].latitude) * ((lonp - lon1) % 360) / d
	if lat > point.latitude:
		return 1
	return 0

def IsPointInZone (point, zone):
	'Unknown parameters; presumably checks whether a specified ZonePoint is within a specified Zone.'
	# Spherical trigonometry: every closed curve cuts the world in two pieces. If point is in the same piece as the OriginalPoint, it is considered "inside".
	# This means that any line from OriginalPoint to point has an even number of intersections with zone segments.
	# This line doesn't need to be the shortest path. It is much easier if it isn't. I'm using a two-segment line: One segment straight north to the pole, one straight south to OriginalPoint.
	num = 0
	points = lua.as_list (zone.Points)
	points += (points[0],)
	for i in range (len (points) - 1):
		num += _intersect (point, (points[i], points[i + 1]))
		num += _intersect (zone.OriginalPoint, (points[i], points[i + 1]))
	return num % 2 == 0

def VectorToSegment (point, p1, p2):
	'Unknown parameters and function.'
	# Compute shortest distance and bearing to get from point to anywhere on segment.
	d1, b1 = VectorToPoint (p1, point)
	d1 = math.radians (d1.GetValue (d1, 'nauticalmiles') / 60.)
	ds, bs = VectorToPoint (p1, p2)
	dist = math.asin (math.sin (d1) * math.sin (math.radians (b1.value - bs.value)))
	dat = math.acos (math.cos (d1) / math.cos (dist))
	if dat <= 0:
		return VectorToPoint (point, p1)
	elif dat >= math.radians (ds.GetValue (ds, 'nauticalmiles') / 60.):
		return VectorToPoint (point, p2)
	intersect = TranslatePoint (p1, Distance (dat * 60, 'nauticalmiles'), bs)
	return VectorToPoint (point, intersect)

def VectorToZone (point, zone):
	'Unknown parameters and function.'
	# Compute shortest distance and bearing to get from point inside a zone.
	if IsPointInZone (point, zone):
		return Distance (0), Bearing (0)
	# Use VectorToSegment multiple times.
	points = lua.as_list (zone.Points)
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
	lat1 = math.radians (p1.latitude)
	lon1 = math.radians (p1.longitude)
	lat2 = math.radians (p2.latitude)
	lon2 = math.radians (p2.longitude)
	# Formula of haversines. This is a numerically stable way of determining the distance.
	dist = 2 * math.asin (math.sqrt (math.sin ((lat1 - lat2) / 2) ** 2 + math.cos (lat1) * math.cos (lat2) * math.sin ((lon1 - lon2) / 2) ** 2))
	# And the bearing.
	bearing = math.atan2 (math.sin (lon2 - lon1) * math.cos(lat2), math.cos (lat1) * math.sin (lat2) - math.sin (lat1) * math.cos (lat2) * math.cos (lon2 - lon1))
	# To get a distance, use nautical miles: 1 nautical mile is by definition equal to 1 minute, so 60 nautical miles is 1 degree.
	return Distance (math.degrees (dist) * 60, 'nauticalmiles'), Bearing (math.degrees (bearing))

def TranslatePoint (point, distance, bearing):
	'''Returns a ZonePoint object calculated by starting at the provided point and moving Distance from that point at the specified angle.
	Signature is zonepoint=Wherigo.TranslatePoint(startzonepoint, distance, bearing), where
		startzonepoint is an instance of ZonePoint,
		distance is an instance of Distance,
		and bearing is an Instance of Bearing.'''
	d = math.radians (distance.GetValue (distance, 'nauticalmiles') / 60.)
	b = math.radians (bearing.value)
	lat1 = math.radians (point.latitude)
	lat2 = math.asin (math.sin (lat1) * math.cos (d) + math.cos (lat1) * math.sin (d) * math.cos(b))
	dlon = math.atan2 (math.sin(b) * math.sin (d) * math.cos (lat1), math.cos (d) - math.sin (lat1) * math.sin (lat2))
	return ZonePoint (math.degrees (lat2), point.longitude + math.degrees (dlon), point.altitude)

# Test some stuff.
#print _intersect (ZonePoint (0, 8, 0), (ZonePoint (10,6,0), ZonePoint (10,7,0)))
