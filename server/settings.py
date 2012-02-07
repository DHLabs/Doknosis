'''
settings.py
    
Contains the settings for the Flask application. 
See http://flask.pocoo.org/docs/config/ for more details. 
'''

DB_USER = 'athlabs_server'
DB_PASS = 'soopahserver'
DB_HOST = 'mysql.athlabs.com'
DB_NAME = 'doknosis'

class Config( object ):
    DEBUG = False
    TESTING = False
    MONGOALCHEMY_DATABASE = 'doknosis'

    # Secret generated like so:
    # > import os
    # > os.urandom(24)
    SECRET_KEY = 'K\xd8Q\x92\xc6s\xd4\xa5\x94\xce\xbfv\xe0\xb3\x1b\x9e\xc5\x1c\xf4\x9bG/\xbb0'
    
    CACHE_TYPE = 'simple'

class Dev( Config ):
    DEBUG = True
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///../tmp/dev.db'
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://%s:%s@%s/%s?charset=utf8' % ( DB_USER, DB_PASS, DB_HOST, DB_NAME )

class Production( Config ):
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///../tmp/dev.db'
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://%s:%s@%s/%s?charset=utf8' % ( DB_USER, DB_PASS, DB_HOST, DB_NAME )
    
class Testing( Config ):
    TESTING = True

# Session stuff
# SESSION_COOKIE_NAME = ''
# SESSION_COOKIE_DOMAIN = ''
# SESSION_COOKIE_PATH = ''
