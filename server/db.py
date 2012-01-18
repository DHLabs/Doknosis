from flaskext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class DiseaseFindings( db.Model ):
    '''
    Helper table to relate Diseases to Findings.

    Uses the Association Object pattern.
    See: http://www.sqlalchemy.org/docs/orm/relationships.html#many-to-many
    '''
    __tablename__ = 'disease_to_findings'
    
    id          = db.Column( 'id', db.Integer, primary_key=True )
    finding_id  = db.Column( 'finding_id', db.Integer, db.ForeignKey( 'finding.id' ) )
    disease_id  = db.Column( 'disease_id', db.Integer, db.ForeignKey( 'disease.id' ) )
    weight      = db.Column( db.Float() )
    
    finding = db.relationship( 'Finding' )
    
    def __init__( self, weight ):
        self.weight = weight

class Disease( db.Model ):
    id          = db.Column( db.Integer, primary_key=True )
    name        = db.Column( db.String( 256 ), unique=True )
    
    findings    = db.relationship( DiseaseFindings )
    
    def __init__( self, name ):
        '''
        Create a new Disease object. Must be added and commited before it is 
        actually added to the database.
        '''
        self.name = name
    
    def __repr__( self ):
        '''
        String representation of the Disease object
        '''
        return '<Disease ( %s )>' % ( self.name )

class Finding( db.Model ):
    id          = db.Column( db.Integer, primary_key=True )
    name        = db.Column( db.String( 256 ), unique=True )
    
    def __init__( self, name ):
        '''
        Create a new Finding object. Must be added and commited before it is 
        actually added to the database.
        '''        
        self.name = name
    
    def __repr__( self ):
        '''
        String representation of the Finding object
        '''        
        return '<Finding ( %s )>' % ( self.name )        