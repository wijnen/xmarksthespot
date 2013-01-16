# xmtsconfig.py - Configuration stuff for xmarksthespot
# vim: set encoding=utf-8
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

import glib
import os

def load_config ():
	'''Check that config file exists, create it if it doesn't, and load it. '''
	d = os.path.join (glib.get_user_config_dir (), 'xmarksthespot')
	f = os.path.join (d, 'config.txt')

	if not os.path.exists (d):
		os.makedirs (d)
	if not os.path.exists (f):
		handle = open (f, 'w')
		handle.write ('''\
# Configuration for xmarksthespot.
# Empty lines and lines starting with # are ignored.
# The first words is the configuration option key. The rest of the line is the value.
Id			0
URL			about:blank
Device			PocketPC
PlayerName		Monty Python
CompletionCode		completion-code

# Env settings.
env-Platform		xmarksthespot
env-CartFolder		/whatever
env-SyncFolder		/whatever
env-LogFolder		/whatever
env-PathSep		/
env-DeviceID		Python
env-Version		2.11-compatible
env-Downloaded		0
env-CartFilename	
env-Device		

# Color definitions.
# Stuff on the map.
	# zonescolor is also used in the zones tab.
zonescolor		#00f
characterscolor		#f00
objectscolor		#880
positioncolor		#000
gridcolor		#ccc

# Stuff in the tabs.
environmentcolor	#f00
inventorycolor		#880
taskcolor		#000
messagecolor		#000
historycolor		#888
logcolor		#080
timercolor		#f0f
''')
		handle.close ()
	
	ret = {}
	for l in open (f).readlines ():
		l = l.strip ().split (None, 1)
		if len (l) == 0 or l[0].startswith ('#'):
			continue
		ret[l[0]] = l[1] if len (l) > 1 else None
		override = os.getenv ('XMTT_' + l[0].upper ().replace ('-', '_'))
		if override is not None:
			ret[l[1]] = override if override != '' else None
	return ret
