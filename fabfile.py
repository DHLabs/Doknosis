from __future__ import with_statement 

from fabric.api import cd, env, local, run
from fabric.colors import green
from fabric.contrib.files import exists

from server import create_app
from server.db import db

env.user = 'athlabs'
env.hosts = [ 'labs.athlabs.com' ]

PROJECT_NAME   = 'doknosis'
PRODUCTION_DIR = 'doknosis.athlabs.com'
GIT_LOCATION   = 'gitolite@igert8.ucsd.edu:doknosis.git'

def compile():
    '''
        Compile and minify JS and CSS sources.

        JS is compiled using Coffeescript
        CSS is compiled using SASS
    '''
    compile_js()
    compile_css()

def compile_js():
    print green( 'Compiling coffeescript into javascript...' )
    local( 'coffee -b -j doknosis.coffee -o server/static/js -c coffeescript' )

def compile_css():
    print green( 'Compiling sass into css...' )
    local( 'sass --update -t compressed sass/layout.scss:server/static/css/layout.css' )

def init_db():
    '''
        Create tables necessary for this app to work.
    '''
    app = create_app()
    db.init_app( app )
    with app.test_request_context():
        db.create_all()
    
def deploy():
    with cd( PRODUCTION_DIR ):
        # Clone the code if the source directory doesn't already exist
        print green( 'Cloning/pulling latest code...' )
        if not exists( PROJECT_NAME ):
            run( 'git clone %s' % ( GIT_LOCATION ) )
        else:
            # Update the source
            with cd( PROJECT_NAME ):
                run( 'git pull' )
        
        print green( 'restarting python instance' )
        # Finally restart our instance
        run( 'pkill python' )
            
