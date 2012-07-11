'''
    settings.py

    Contains the settings for the Flask application.
    See http://flask.pocoo.org/docs/config/ for more details.
'''


class Config( object ):
    DEBUG   = False
    TESTING = False
    MONGOALCHEMY_DATABASE = 'doknosis'

    # Secret generated like so:
    SECRET_KEY = 'K\xd8Q\x92\xc6s\xd4\xa5\x94\xce\xbfv\xe0\xb3\x1b\x9e\xc5\x1c\xf4\x9bG/\xbb0'
    CACHE_TYPE = 'simple'


class Dev( Config ):
    DEBUG = True
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///../tmp/dev.db'


class Production( Config ):
    DEBUG   = False
    TESTING = False


class Testing( Config ):
    DEBUG   = True
    TESTING = True
    MONGOALCHEMY_DATABASE = 'doknosis-test'
