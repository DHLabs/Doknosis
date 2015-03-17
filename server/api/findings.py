'''
    server.api.findings

    Handles API calls to manipulate/list findings.
'''
import json

from flask import Blueprint, request

from server.cache import cache
from server.db import Finding

findings_api = Blueprint( 'findings_api', __name__ )

AUTOCOMPLETE_MAX_LENGTH = 25

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

    # Query the database for matching strings
    findings = Finding.query.filter( {'name': { '$regex': '%s' % (term) } } )\
                .ascending( Finding.name )\
                .all()

    # Next, we sort the output by how close they are to just the string we found.
    # Do this by removing the match and sorting the rest (with right justificatoin to give precidence to shorter mismatches.
    maxl = max([len(xx.name) for xx in findings])
    json_findings = [{'id':str(finding.mongo_id),
                      'label':finding.name,
                      'value':finding.name} 
                     for finding in sorted(findings,key=lambda xx:xx.name.rjust(maxl).replace(term,''))]

    # Have to cut off to max length here instead of in query because the perfect match might be the last one in the list.
    return json.dumps( json_findings[0:AUTOCOMPLETE_MAX_LENGTH-1] )
