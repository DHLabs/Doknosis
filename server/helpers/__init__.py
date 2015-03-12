import json
from flask import flash

SUCCESS = { 'success': True }
FAILURE = { 'success': False }

def success( msg=None ):
	res = dict( SUCCESS )

	if msg is not None:
		res[ 'msg' ] = msg
		flash(msg,'success')

	return json.dumps( res )

def failure( msg=None ):
	res = dict( FAILURE )

	if msg is not None:
		res[ 'msg' ] = msg
		flash(msg,'error')

	return json.dumps( res )
