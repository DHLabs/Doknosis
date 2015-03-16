'''
    server.api.findings

    Handles API calls to manipulate/list findings.
'''
import json

from flask import Blueprint, request

from server.cache import cache
from server.db import Finding

findings_api = Blueprint( 'findings_api', __name__ )


@findings_api.route( '/list', methods=['GET'] )
@cache.cached( timeout=60 )
def finding_list():
    '''
        Return a list of findings in the system. This list is cached every hour
        so that the query does not tax the system if hit repeatedly.

        @params
        None

        @returns
        A JSON list of ALL findings in the system.
    '''
    findings = Finding.query.all()

    # Convert into an JSON object
    json_findings = []
    for finding in findings:
        info = { 'id':      finding.id,
                 'name':    finding.name }
        json_findings.append( info )

    return json.dumps( json_findings )


@findings_api.route( '/autocomplete', methods=['GET'] )
def finding_autocomplete():
    '''
        Handles the autocompletion of findings in the search box. We take a
        substring and search the database of finding names that match the
        string. These results are converted into a JSON list and returned.

        @params
        term        A string representing the search term.

        @returns
        A JSON list of the findings that match the query substring.
    '''

    term = request.args.get( 'term', None )

    if term is None:
        return json.dumps( [] )

    findings = Finding.query.filter( {'name': { '$regex': '%s' % (term) } } )\
                .limit( 25 )\
                .ascending( Finding.name )\
                .all()

    # Convert into an JSON object
    json_findings = []
    for finding in findings:
        info = { 'id':       str( finding.mongo_id ),
                 'label':    finding.name,
                 'value':    finding.name }
        json_findings.append( info )

    return json.dumps( json_findings )
