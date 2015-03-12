from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.mongoalchemy import MongoAlchemy

db      = SQLAlchemy()
mongo   = MongoAlchemy()

class FindingWeight( mongo.Document ):
    name    = mongo.StringField()
    weight  = mongo.FloatField()

    def __init__( self, name, weight, **kwargs ):
        mongo.Document.__init__( self, name=name,
                                     weight=float(weight),
                                     **kwargs )

    def to_dict( self ):
        return dict( {'name': self.name, 'weight': self.weight} )


class Explanation( mongo.Document ):
    name        = mongo.StringField()
    type_identifier = mongo.StringField()
    findings    = mongo.ListField( mongo.DocumentField( FindingWeight ) )

    def __init__( self, name, type_identifier, findings=[], **kwargs ):
        mongo.Document.__init__( self, name=name, type_identifier=type_identifier, **kwargs )
        self.findings = findings


class Finding( mongo.Document ):
    name        = mongo.StringField()
