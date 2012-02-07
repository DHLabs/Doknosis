import json

from flask import Blueprint, request

from server.cache import cache
from server.db import Finding

findings_api = Blueprint( 'findings_api', __name__ )

@findings_api.route( '/finding/list', methods=['GET'] )
@cache.cached( timeout=60 )
def finding_list():
    findings = Finding.query.all()
    
    # Convert into an JSON object
    json_findings = []
    for finding in findings:
        info = {}
        info[ 'id' ]    = finding.id
        info[ 'name' ]  = finding.name
    
        json_findings.append( info )
    
    return json.dumps( json_findings )

@findings_api.route( '/finding/autocomplete', methods=['GET'] )
def finding_autocomplete():
    term = request.args.get( 'term' )

    findings = Finding.query.filter( {'name': { '$regex': '^%s' % ( term ) } } )\
                .limit( 20 )\
                .ascending( Finding.name )\
                .all()

    # Convert into an JSON object
    json_findings = []
    for finding in findings:
        info = {}
        info[ 'id' ]    = str( finding.mongo_id )
        info[ 'label' ] = finding.name
        info[ 'value' ] = finding.name
        
        json_findings.append( info )
    
    return json.dumps( json_findings )