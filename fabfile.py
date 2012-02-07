from __future__ import with_statement 

from fabric.api import cd, env, local, run
from fabric.colors import green
from fabric.contrib.files import exists

from server import create_app
from server.db import mongo, Disease, Finding, FindingWeight

import server.parseFile as parseFile

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
            
def init_db():
    '''
    Create tables necessary for this app to work.
    '''    
    print green( 'Use \"fab fill_db\" to fill the empty database with data.' )

def fill_db():
    '''
    Fill the database ( should be EMPTY ) based on the findings/disease CSV file
    '''
    # Create an app context so we can access the database
    app = create_app()
    mongo.init_app( app )
    with app.test_request_context():

        # Parse CSV file and grab the findings/disease lists
        print green( 'Parsing disease/finding CSV file...' )
        tbl = parseFile.createCSVTable()
        findings, diseasesList = parseFile.createDiseaseList(tbl)

        # Used to associate a finding name to the database object
        print green( 'Adding findings to database...' )
        finding_assoc = {}

        # Add findings to database
        if False:
            for obj in findings:
                fname = obj.strip().lower()

                if Finding.query.filter( {'name': fname} ).count() == 0:
                    finding = Finding( name=fname )
                    finding.save()

        # Add diseases to database
        print green( 'Adding diseases to database...' )
        for obj in diseasesList:

            disease = Disease( name=obj.name )

            # Findings are represented as [ Finding name, weight ]
            for fw in obj.findings:
                fname   = fw[ 0 ].strip().lower()
                weight  = float( fw[ 1 ] )

                disease.findings.append( FindingWeight( name=fname, weight=weight ) )

            disease.save()
