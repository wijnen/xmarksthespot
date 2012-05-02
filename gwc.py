# Read (and write?) gwc files.

import struct

_CARTID = '\x02\x0aCART\x00'

def _short (file, pos):
	ret = struct.unpack ('<h', file[pos[0]:pos[0] + 2])[0]
	pos[0] += 2
	return ret

def _int (file, pos):
	ret = struct.unpack ('<i', file[pos[0]:pos[0] + 4])[0]
	pos[0] += 4
	return ret

def _double (file, pos):
	ret = struct.unpack ('<d', file[pos[0]:pos[0] + 8])[0]
	pos[0] += 8
	return ret

def _string (file, pos):
	ret = ''
	p = file.find ('\0', pos[0])
	assert p >= 0
	ret = file[pos[0]:p]
	pos[0] = p + 1
	return ret

class cartridge:
	def __init__ (self, file):
		if type (file) is not str:
			file = file.read ()
		elif not file.startswith (_CARTID):
			file = open (file).read ()
		assert file.startswith (_CARTID)
		pos = [len (_CARTID)]	# make this an array so it can be changed by functions.
		num = _short (file, pos)
		offset = [None] * num
		self.id = {}
		self.rid = [None] * num
		self.filetype = [None] * num
		self.data = [None] * num
		self.image = {}
		self.sound = {}
		for i in range (num):
			self.rid[i] = _short (file, pos)
			assert self.rid[i] not in self.id
			self.id[self.rid[i]] = i
			offset[i] = _int (file, pos)
		size = _int (file, pos)
		self.latitude = _double (file, pos)
		self.longitude = _double (file, pos)
		self.altitude = _double (file, pos)
		pos[0] += 4 + 4
		self.splashId = _short (file, pos)
		self.iconId = _short (file, pos)
		self.gametype = _string (file, pos)
		self.user = _string (file, pos)
		pos[0] += 4 + 4
		self.name = _string (file, pos)
		self.guid = _string (file, pos)
		self.description = _string (file, pos)
		self.startdesc = _string (file, pos)
		self.version = _string (file, pos)
		self.author = _string (file, pos)
		self.url = _string (file, pos)
		self.device = _string (file, pos)
		pos[0] += 4
		self.completion_code = _string (file, pos)
		assert pos[0] == len (_CARTID) + 2 + num * 6 + 4 + size
		# read lua bytecode.
		pos[0] = offset[0]
		size = _int (file, pos)
		self.data[0] = file[pos[0]:pos[0] + size]
		# read all other files.
		for i in range (1, num):
			pos[0] = offset[i]
			if file[pos[0]] == 0:
				continue
			pos[0] += 1
			self.filetype[i] = _int (file, pos)
			size = _int (file, pos)
			self.data[self.rid[i]] = file[pos[0]:pos[0] + size]
			# TODO?: detect file type and load image or sound. This is now done by ZMedia.Resources.Type, which works fine.
