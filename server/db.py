from mongoalchemy.document import Index
from flask.ext.mongoalchemy import MongoAlchemy
from pymongo import Connection
from pymongo.errors import BulkWriteError
from server.constants import EXPLANATION_REGIONS

# For debugging:
# from flask import flash

mongo   = MongoAlchemy()

# TODO: down the road, maybe more generic demographics class or something?
# TODO: modify manual edit method to incorporate regions


class DBError(Exception):
    """ Exception generated when database access classes are misused. """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return 'Database Access Error -- \"{}\"!'.format(self.msg)


class DocumentBase(mongo.Document):
    '''  Common code for my own mongo documents.    
    '''
    name = mongo.StringField()
    # This should just ensure that names stay unique:
    name_index  = Index().ascending('name').unique()

    # Use self.__class__.__name__
    @classmethod
    def get_count(cls):
        return getattr(Connection().doknosis,cls.__name__).count()

    @classmethod
    def bulk_upsert_find_dict(cls,update_row):
        ''' Overload this guy to return a dictionary for searching the database in bulk update.

        Elements of the dictionary should have the form {database_name:search_term}.
        '''
        pass

    @classmethod
    def bulk_upsert_set_dict(cls,update_row):
        ''' Overload this guy to return a dictionary for replacement in bulk update.

        Elements of the dictionary should have the form {database_name:replacement_value}.
        '''
        pass

    @classmethod
    def bulk_upsert_preprocess(cls,update_list):
        ''' Overload if you want to do any preprocessing of the update_list before the bulk update.
        '''
        return update_list

    @classmethod
    def bulk_upsert_postprocess(cls,update_list):
        ''' Overload if you want to do any post processing after the bulk update.
        '''
        pass

    @classmethod
    def bulk_upsert(cls, update_list):
        ''' Class method for handling a list of updates all at once

        Each element of update_list, call the superclass methods to get database serch terms and replace
        terms.  Then we run the bulk operations.

        @param update_list List of terms passed into superclass methods for each bulk op.
        @exception DBError Raised if BulkWriteError is raised when we try to execute.
        '''
        update_list = cls.bulk_upsert_preprocess(update_list)
        if len(update_list) == 0:
            return

        # Google sheet parsed successfully (processing took 19.967015028 seconds)!

        bulk = getattr(Connection().doknosis,cls.__name__).initialize_unordered_bulk_op()
        for upd in update_list:
            bulk.find(cls.bulk_upsert_find_dict(upd)).upsert().update({'$set':cls.bulk_upsert_set_dict(upd)})

        try:
            res = bulk.execute()
        except BulkWriteError as bwe:
            if len(bwe.details['writeConcernErrors']):
                for one_err in bwe.details['writeConcernErrors']:
                    raise DBError(cls.__name__+' bulk_upsert writeConcernError:'+one_err['errmsg'])
            if len(bwe.details['writeErrors']):
                for one_err in bwe.details['writeErrors']:
                    raise DBError(cls.__name__+' bulk_upsert writeError:'+one_err['errmsg'])

            raise DBError(cls.__name__+' bulk_upsert Unknown Error')

        cls.bulk_upsert_postprocess(update_list)

    @classmethod
    def remove_all(cls):
        getattr(Connection().doknosis,cls.__name__).remove({})


    
class FindingWeight( mongo.Document ):
    ''' FindingWeight objects are instantiated for every edge between explanation and finding.

    Weight should be in [0,1], finding should match a unique element in the database of the Finding
    class.  Note that this is kind of a dummy document.  We don't need the extra code from DocumentBase
    because FindingWeights are never directly manipulated.
    '''
    name    = mongo.StringField()
    weight  = mongo.FloatField()

    def __init__( self, name, weight, **kwargs ):
        mongo.Document.__init__( self, name=name,
                                     weight=float(weight),
                                     **kwargs )

    def to_dict( self ):
        return dict( {'name': self.name, 'weight': self.weight} )


class Explanation( DocumentBase ):
    type_identifier = mongo.StringField()
    findings = mongo.ListField(mongo.DocumentField(FindingWeight))
    regions = mongo.ListField(mongo.StringField())


    @classmethod
    def bulk_upsert_find_dict(cls,update_row):
        ''' Explanation bulk updates use an upsert on the name and type_identifier keys.
        '''
        return {'name':update_row['name'], 'type_identifier':update_row['type_identifier']}

    @classmethod
    def bulk_upsert_set_dict(cls,update_row):
        ''' In addition to name and type_identifier, we also may replace the findings and regions fields during Explanation bulk updates.
        '''
        rd = {}
        if 'findings' in update_row:
            bad_finding = next((fd for fd in update_row['findings'] if 'name' not in fd or 'weight' not in fd),None)
            if bad_finding is not None:
                raise DBError('Bad finding \"{}\" (must contain a name and a weight)!'.format(bad_finding))
            rd['findings']=update_row['findings']

        if 'regions' in update_row:
            bad_region = next((rg for rg in update_row['regions'] if rg not in EXPLANATION_REGIONS),None)
            if bad_region is not None:
                raise DBError('Bad region \"{}\" (must be one of {})!'.format(bad_finding, EXPLANATION_REGIONS))
            rd['regions']=update_row['regions']

        return rd

    @classmethod
    def bulk_upsert_preprocess(cls,update_list):
        ''' Remove redundant elements from update_list.

        Bulk update will overwrite elements of update_list with matching name and type.  Here we remove redundant guys
        so as to avoid issues with zombie findings.
        '''
        return {upd['name']+upd['type_identifier']:upd for upd in update_list}.values()
            

    @classmethod
    def bulk_upsert_postprocess(cls,update_list):
        ''' When we do a bulk update of explanations, trigger a bulk update of associated Findings after.
        '''
        finding_list = list(set([fd['name'] for fdl in update_list for fd in fdl['findings']]))
        Finding.cleanup_list(findings_added=finding_list)


    def __init__( self, name, type_identifier, finding_dicts=None, **kwargs ):
        ''' Initialize an explanation object with name, type, and findings.

        Findings might be entered as a list of FindingWeight objects if unwrapped by MongoAlchemy (when querying) or
        a list of dictionaries if initialized by us.  If finding_dicts is specified, overwrites any previous guys.
        '''
        DocumentBase.__init__( self, name=name, type_identifier=type_identifier, **kwargs )

        if finding_dicts is not None:
            bad_finding = next((fd for fd in finding_dicts if 'name' not in fd or 'weight' not in fd),None)
            if bad_finding is not None:
                raise DBError('Bad finding \"{}\" (must contain a name and a weight)!'.format(bad_finding))
            self.findings = [FindingWeight(fd['name'],fd['weight']) for fd in finding_dicts]


    # The rest of these methods are passed a mongo_id and may perform a query first to pull the object
    # from the database.  I just put them here to combine all the mongo-specific code.
    @staticmethod
    def upsert(mongo_id,name,type_identifier,finding_dicts):
        ''' Emulate a mongo upsert which searches by id (if id matches), or by name/type if not.

        '''
        rem_finding_names = []
        if mongo_id is None:
            
            mongo_obj = Explanation(name=name,type_identifier=type_identifier,finding_dicts=finding_dicts)
        else:
            try:
                mongo_obj = Explanation.query.filter(Explanation.mongo_id == mongo_id).limit(1).first()
            except Exception as e:
                raise DBError( 'Explanation.upsert -- Exception querying database for explanation : {}'.format(e) )

            if mongo_obj is None:
                raise DBError( 'Explanation.upsert -- Failed to find explanation with id {} in database'.format(mongo_id) )
        
            if mongo_obj.name != name:
                # flash('Changed Explanation Name from {} To {}'.format(mongo_obj.name,name),'error')
                mongo_obj.name = name
            if mongo_obj.type_identifier != type_identifier:
                # flash('Changed Explanation Type To {}'.format(type_identifier),'error')
                mongo_obj.type_identifier = type_identifier

            rem_finding_names = list(set([fd.name for fd in mongo_obj.findings]) - set([fd['name'] for fd in finding_dicts]))
            add_finding_names = list(set([fd['name'] for fd in finding_dicts]) - set([fd.name for fd in mongo_obj.findings]))

            # Next, overwrite the previous findings with the new ones
            bad_finding = next((fd for fd in finding_dicts if 'name' not in fd or 'weight' not in fd),None)
            if bad_finding is not None:
                raise DBError('Explanation.upsert -- Bad finding \"{}\" (must contain a name and a weight)!'.format(bad_finding))
            mongo_obj.findings = [FindingWeight(fd['name'],fd['weight']) for fd in finding_dicts]

        mongo_obj.save()
        # flash('try removing findings: {}, (new findings: {})'.format(rem_finding_names,[fd['name'] for fd in finding_dicts]),'error')
        Finding.cleanup_list(findings_removed=rem_finding_names,findings_added=add_finding_names)


    @staticmethod
    def delete(mongo_id):
        if mongo_id is not None:
            try:
                explanation = Explanation.query.filter(Explanation.mongo_id == mongo_id).limit(1).first()
            except Exception as e:
                raise DBError('Tried to delete explanation with id {}, but failed to find it in database: {}'.format(mongo_id,e))

            if explanation is not None:
                finding_names = [fw.name for fw in explanation.findings]
                explanation.remove()
                Finding.cleanup_list(findings_removed=finding_names)


class Finding( DocumentBase ):
    @classmethod
    def bulk_upsert_find_dict(cls,update_row):
        ''' Finding bulk update is very simple, just upsert unique name attributes.
        '''
        return {'name':update_row}

    @classmethod
    def bulk_upsert_set_dict(cls,update_row):
        ''' Finding bulk update is very simple, just upsert unique name attributes.
        '''
        return {'name':update_row}

    @staticmethod
    def cleanup_list(findings_removed=[],findings_added=[]):
        ''' Add given findings (if not already there).  Delete the given findings if they are no longer in any explanation dictionaries.
        '''
        # Uniquification should be handled internally...
        Finding.bulk_upsert(findings_added)

        # There has got to be a better way, but this is not used too often so...
        for fn in findings_removed:
            count = Explanation.query.filter({'findings.name': fn}).count()
            # flash('cleanup_list -- Finding {} used in {} Explanations.'.format(fn,count),'error')
            if count == 0:
                finding = Finding.query.filter( Finding.name == fn ).limit(1).first()
                if finding is not None:
                    finding.remove()
