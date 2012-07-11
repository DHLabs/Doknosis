import json

SUCCESS = { 'success': True }
FAILURE = { 'success': False }

def success( msg=None ):
	res = dict( SUCCESS )

	if msg is not None:
		res[ 'msg' ] = msg

	return json.dumps( res )

def failure( msg=None ):
	res = dict( FAILURE )

	if msg is not None:
		res[ 'msg' ] = msg

	return json.dumps( res )