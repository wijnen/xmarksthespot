#!/usr/bin/env python
# gwc.py - Read gwc files for xmarksthespot
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

import struct
import zipfile
import os
import lua
import sys
import wherigo

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

def _wshort (num):
	return struct.pack ('<h', num)

def _wint (num):
	return struct.pack ('<i', num)

def _wdouble (num):
	return struct.pack ('<d', num)

def _wstring (s):
	assert '\0' not in s
	return s + '\0'

class cartridge:
	def __init__ (self, file, script, cbs, config):
		if type (file) is not str:
			file = file.read ()
		if not file.startswith (_CARTID):
			if os.path.isdir (file):
				# This is a gwz directory.
				gwc = False
				data = self._read_gwz (file, True, config)
			else:
				file = open (file).read ()
				if file.startswith (_CARTID):
					# This is a gwc file.
					gwc  = True
					self._read_gwc (file)
				else:
					# This should be a gwz file.
					gwc = False
					data = self._read_gwz (file, False, config)
		else:
			self._read_gwc (file)
		env = {}
		for i in config:
			if i.startswith ('env-'):
				env[i[4:]] = config[i]
		env['Downloaded'] = int (env['Downloaded'])
		if not env['CartFilename']:
			env['CartFilename'] = os.path.splitext (file)[0]
		if not env['Device']:
			env['Device'] = self.device
		wherigo._script.run ('', 'Env', env, name = 'setting Env')
		if not gwc:
			self._read_gwz_2 (cbs, data, config)
		else:
			cartridge = wherigo.ZCartridge ()
			cartridge._setup (self, cbs)
	def _read_gwc (self, file):
		pos = [len (_CARTID)]	# make this an array so it can be changed by functions.
		num = _short (file, pos)
		offset = [None] * num
		rid = [None] * num
		#self.filetype = [None] * num
		self.data = [None] * num
		for i in range (num):
			rid[i] = _short (file, pos)
			assert rid[i] < num
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
			if file[pos[0]] == '\0':
				continue
			pos[0] += 1
			filetype = _int (file, pos)	# Not used.
			size = _int (file, pos)
			self.data[rid[i]] = file[pos[0]:pos[0] + size]
	def _read_gwz (self, gwz, isdir, config):
		# Read gwz file or directory. gwz is path to data. Media files are given their id from the lua source.
		data = {}
		code = None	# This is the name of the lua code file.
		if isdir:
			names = os.listdir (gwz)
		else:
			z = zipfile.ZipFile (gwz, 'r')
			names = z.namelist ()
		for n in names:
			ln = n.lower ()
			assert ln not in data
			if isdir:
				data[ln] = open (os.path.join (gwz, n), 'rb').read ()
			else:
				data[ln] = z.read (n)
			if os.path.splitext (ln)[1] == os.extsep + 'lua':
				assert code is None
				code = ln
		# There must be lua code.
		assert code is not None
		self.data = [data.pop (code)]
		# Set up external properties.
		for key in ('gametype', 'author', 'description', 'guid', 'name', 'latitude', 'longitude', 'altitude', 'startdesc', 'url', 'device', 'version', 'user', 'completion_code'):
			setattr (self, key, config[key])
		return data
	def _read_gwz_2 (self, cbs, data, config):
		cartridge = wherigo.ZCartridge ()
		media = cartridge._getmedia (self, self.data[0], cbs)
		self.data += [None] * len (media)
		map = {}
		for m in range (len (media)):
			assert media[m]._id == m + 1
			r = media[m].Resources.list ()
			if len (r) < 1:
				continue
			r = r[0]
			#t = r['Type'] Use?
			n = r['Filename']
			map[n.lower ()] = m + 1
			self.data[m + 1] = data.pop (n.lower ())
		if config['icon'] is not None:
			if config['icon'] in data:
				self.iconId = len (self.data)
				self.data.append (data.pop (config['icon']))
			elif config['icon'] in map:
				self.iconId = map[config['icon']]
			else:
				print ("Not setting icon to %s, because media doesn't exist" % config['icon'])
				self.iconId = 0
		else:
			self.iconId = 0
		if config['splash'] is not None and config['splash'] in data:
			self.splash = data.pop (config['splash'])
			if config['splash'] in data:
				self.splashId = len (self.data)
				self.data.append (data.pop (config['splash']))
			elif config['splash'] in map:
				self.splashId = map[config['splash']]
			else:
				print ("Not setting splash to %s, because media doesn't exist" % config['splash'])
				self.splashId = 0
		else:
			self.splashId = 0
		if len (data) != 0:
			print 'ignoring unused media: %s.' % (', '.join (data.keys ()))
		cartridge._setup (self, None)

def write_cartridge (target, info, lua, files):
	if hasattr (info, 'splash'):
		splashid = len (files)
		files += (info.splash,)
	else:
		splashid = 0
	if hasattr (info, 'icon'):
		iconid = len (files)
		files += (info.icon,)
	else:
		iconid = 0
	if type (target) is str:
		target = open (target, 'wb')
	header = ''
	header += _wdouble (info.latitude)
	header += _wdouble (info.longitude)
	header += _wdouble (info.altitude)
	header += '\0' * 8
	header += _wshort (splashid)
	header += _wshort (iconid)
	header += _wstring (info.gametype)
	header += _wstring (info.user)
	header += '\0' * 8
	header += _wstring (info.name)
	header += _wstring (info.guid)
	header += _wstring (info.description)
	header += _wstring (info.startdesc)
	header += _wstring (info.version)
	header += _wstring (info.author)
	header += _wstring (info.url)
	header += _wstring (info.device)
	header += '\0' * 4
	header += _wstring (info.completion_code)
	data = [_wint (len (lua)) + lua]
	for f in files:
		# TODO: Filetype is now always 0; it isn't used by my player, but can be used by other players.
		if f is None:
			data += ('\0',)
		else:
			data += ('\1' + _wint (0) + _wint (len (f)) + f,)
	target.write (_CARTID)
	target.write (_wshort (len (data)))
	offset = len (_CARTID) + 2 + 6 * len (data) + 4 + len (header)
	for i in range (len (data)):
		target.write (_wshort (i))
		target.write (_wint (offset))
		offset += len (data[i])
	target.write (_wint (len (header)) + header)
	for i in data:
		target.write (i)
