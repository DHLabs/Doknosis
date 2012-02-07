from flaskext.sqlalchemy import SQLAlchemy
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

# class DiseaseFindings( db.Model ):
#     '''
#     Helper table to relate Diseases to Findings.
#     Uses the Association Object pattern.
#     See: http://www.sqlalchemy.org/docs/orm/relationships.html#many-to-many
#     '''
#     __tablename__ = 'disease_to_findings'
    
#     id          = db.Column( 'id', db.Integer, primary_key=True )
#     finding_id  = db.Column( 'finding_id', db.Integer, db.ForeignKey( 'finding.id' ) )
#     disease_id  = db.Column( 'disease_id', db.Integer, db.ForeignKey( 'disease.id' ) )
#     weight      = db.Column( db.Float() )
    
#     finding = db.relationship( 'Finding' )
    
#     def __init__( self, weight ):
#         self.weight = weight

# class Disease( db.Model ):
#     id          = db.Column( db.Integer, primary_key=True )
#     name        = db.Column( db.String( 256 ), unique=True )
    
#     findings    = db.relationship( DiseaseFindings )
    
#     def __init__( self, name ):
#         '''
#         Create a new Disease object. Must be added and commited before it is 
#         actually added to the database.
#         '''
#         self.name = name
    
#     def __repr__( self ):
#         '''
#         String representation of the Disease object
#         '''
#         return '<Disease ( %s )>' % ( self.name )

# class Finding( db.Model ):
#     id          = db.Column( db.Integer, primary_key=True )
#     name        = db.Column( db.String( 256 ), unique=True )
    
#     def __init__( self, name ):
#         '''
#         Create a new Finding object. Must be added and commited before it is 
#         actually added to the database.
#         '''        
#         self.name = name
    
#     def __repr__( self ):
#         '''
#         String representation of the Finding object
#         '''        
#         return '<Finding ( %s )>' % ( self.name )        