from flask.ext.sqlalchemy import SQLAlchemy
from flaskext.mongoalchemy import MongoAlchemy

db      = SQLAlchemy()
mongo   = MongoAlchemy()

class FindingWeight( mongo.Document ):
    name    = mongo.StringField()
    weight  = mongo.FloatField()

    def __init__( self, name, weight, **kwargs ):
        mongo.Document.__init__( self, name=name, weight=float( weight ), **kwargs )

    def to_dict( self ):
        return dict( {'name': self.name, 'weight': self.weight} )

class Disease( mongo.Document ):
    name        = mongo.StringField()
    findings    = mongo.ListField( mongo.DocumentField( FindingWeight ) )

    def __init__( self, name, findings=[], **kwargs ):
        mongo.Document.__init__( self, name=name, **kwargs )
        self.findings = findings


class Finding( mongo.Document ):
    name        = mongo.StringField()