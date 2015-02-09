'''
Available functions:

All of them need argument req={consumerToken=''}
All return Status={StatusCode=short,StatusMessage=''}

GetCartridgeInfo(IncludeUserInformation=bool,WGCode='') -> (Cartridge={...},UserInformation={...})
SearchCartridges(PageNumber=short,ResultsPerPage=short,SearchArguments={CartridgeName='',CountryID=short,ExternalAuthorNameOrGroupName='',IsOpenSource=bool,IsPlayAnywhere=bool,Latitude=float,Longitude=float,OrderSearchBy=PublishDate(2)|Distance(0)|Name(1)|CompletionTime,SearchRadiusInKm=float,StateID=short,UserHasCompleted=bool,UserHasNotPlayed=bool,UserHasPartiallyPlayed=bool,UserOwns=bool}) -> (Cartridges=[...],TotalSearchResults=int)
DownloadCartridge(WGCode='') -> (CartridgeBytes='base64')
UserCompletedCartridge(CompletionCode='',NamesOfOtherUsersPlaying=[''], WGCode='') -> (OtherUserCompletionSuccessfullyMarked=[bool])
GetCartridgeSource(VersionNumber=int,WGCode='') -> (GWZ='base64')
GetCountryList() -> (CountryIDs=[short],CountryNames=[''])
GetRegionList(CountryID=short) -> (RegionIDs=[short],RegionNames=[''])

Test() -> ()
GetUserInfo(UserGUID=guid,UserName='') -> (AvatarUrl='',CartridgesCompleted=int,Locale='',MembershipLevel=int,MembershipLevelString='',UserGUID=guid,UserName='')
GetCartridgeLogs
AddCartridgeLog
GetCartridgeVersions
UpdateCartridgeSource
UploadNewCartridge
UpdateLog
ArchiveLog
UpdateCartridgeContributors
ArchiveCartridge
AttachLogMedia
DeleteLogMedia
UpdateLogMedia
UpdateCartridgeMedia
UpdateListing
UploadCartridgePlaythroughs
GetCartridgeVariables
SetCartridgeVariables
GetUserCartridges
ValidLogTypes
'''

site = 'http://foundation.rangerfox.com/API/APIv1JSON.svc/'
token = None

import urllib2
import json
import gtk

def _call(function, args):
	assert token is not None
	args['consumerToken'] = token
	data = json.dumps({'req': args})
	result = json.loads(urllib2.urlopen(urllib2.Request(site + function, data, {'Content-Type': 'application/json'})).read())
	if result['Status']['StatusCode'] != 0:
		raise ValueError(result['Status']['StatusMessage'])
	return result

def _makebytes(data):
	return ''.join([chr(x) for x in data])

def GetCountryList():
	result = _call('GetCountryList', {})
	ret = {}
	for name, id in zip(result['CountryNames'], result['CountryIDs']):
		ret[name] = id
	return ret

def GetRegionList(CountryID):
	result = _call('GetRegionList', {'CountryId': CountryID})
	ret = {}
	for name, id in zip(result['RegionNames'], result['RegionIDs']):
		ret[name] = id
	return ret

def SearchCartridges(
		PageNumber,
		ResultsPerPage,
		CartridgeName = None,
		CountryID = None,
		ExternalAuthorNameOrGroupName = None,
		IsOpenSource = None,
		IsPlayAnywhere = None,
		Latitude = None,
		Longitude = None,
		OrderSearchBy = None,
		SearchRadiusInKm = None,
		StateID = None,
		UserHasCompleted = None,
		UserHasNotPlayed = None,
		UserHasPartiallyPlayed = None,
		UserOwns = None):
	search = {}
	if CartridgeName is not None: search['CartridgeName'] = CartridgeName
	if CountryID is not None: search['CountryID'] = CountryID
	if ExternalAuthorNameOrGroupName is not None: search['ExternalAuthorNameOrGroupName'] = ExternalAuthorNameOrGroupName
	if IsOpenSource is not None: search['IsOpenSource'] = IsOpenSource
	if IsPlayAnywhere is not None: search['IsPlayAnywhere'] = IsPlayAnywhere
	if Latitude is not None: search['Latitude'] = Latitude
	if Longitude is not None: search['Longitude'] = Longitude
	if OrderSearchBy is not None: search['OrderSearchBy'] = OrderSearchBy
	if SearchRadiusInKm is not None: search['SearchRadiusInKm'] = SearchRadiusInKm
	if StateID is not None: search['StateID'] = StateID
	if UserHasCompleted is not None: search['UserHasCompleted'] = UserHasCompleted
	if UserHasNotPlayed is not None: search['UserHasNotPlayed'] = UserHasNotPlayed
	if UserHasPartiallyPlayed is not None: search['UserHasPartiallyPlayed'] = UserHasPartiallyPlayed
	if UserOwns is not None: search['UserOwns'] = UserOwns
	result = _call('SearchCartridges', {'PageNumber': PageNumber, 'ResultsPerPage': ResultsPerPage, 'SearchArguments': search})
	return result['Cartridges'], result['TotalSearchResults']

def GetCartridgeInfo(WGCode):
	result = _call('GetCartridgeInfo', {'IncludeUserInformation': False, 'WGCode': WGCode})
	return result['Cartridge']

def DownloadCartridge(WGCode):
	result = _call('DownloadCartridge', {'WGCode': WGCode})
	return _makebytes(result['CartridgeBytes'])

def GetCartridgeVersions(WGCode):
	result = _call('GetCartridgeVersions', {'WGCode': WGCode})
	if not result['CanDownloadSourceCode']:
		return []
	return [x for x in result['Versions'] if x['SourceCodeIsAvailable']]

def GetCartridgeSource(WGCode, version):
	result = _call('GetCartridgeSource', {'WGCode': WGCode, 'VersionNumber': version})
	return _makebytes(result['GWZ'])

def UserCompletedCartridge(WGCode, CompletionCode):
	_call('UserCompletedCartridge', {'WGCode': WGCode, 'CompletionCode': CompletionCode})

def search():
	print('search activated')

def events(custom):
	events = {'search': search}
	events.update(custom)
	return events

def inputs():
	return ('search_page_list',
		'search_page',
		'search_resultsperpage',
		'search_name_valid',
		'search_name',
		'search_coord_valid',
		'search_latitude',
		'search_longitude',
		'search_radius',
		'search_play_anywhere_valid',
		'search_play_anywhere',
		'search_open_source_valid',
		'search_open_source')

def outputs():
	return ()
