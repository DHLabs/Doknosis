import sys, os
INTERP = "/home/athlabs/env/bin/python"
if sys.executable != INTERP: os.execl(INTERP, INTERP, *sys.argv)

os.chdir( 'doknosis' )
sys.path.append( os.getcwd() )

from server import create_app
application = create_app( 'server.settings.Production' )
