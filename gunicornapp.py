import sys, os

# Only need to set this on Dreamhost
PYTHON_INTERP 		= None #'/home/ubuntu/.pyenvs/doknosis/bin/python'

# Project name/settings
PROJECT_NAME 	 	= 'doknosis'
PROJECT_SETTINGS 	= 'server.settings.Production'

if PYTHON_INTERP and sys.executable != PYTHON_INTERP: 
	os.execl( PYTHON_INTERP, PYTHON_INTERP, *sys.argv )

sys.path.append( os.getcwd() )

from server import create_app
application = create_app( PROJECT_SETTINGS )