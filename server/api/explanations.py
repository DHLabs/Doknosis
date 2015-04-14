'''
    server.api.explanations

    Handles API calls to manipulate/list explanations.
'''
import json

from flask import Blueprint, request

from server.db import Explanation

explanations_api = Blueprint( 'explanations_api', __name__ )

@explanations_api.route( '/list', methods=['GET'] )
def explanation_list():
    '''
        Return a list of explanations in the system.

        @params
        page        Page of results to return

        @returns
        A JSON list of explanations in the system.
    '''
    page = int( request.args.get( 'page', '1' ) )

    pagination = Explanation.query.ascending( Explanation.name )\
                            .paginate( page=page, per_page=100 )

    results = []
    for explanation in pagination.items:
        results.append( { 'id': Explanation.id, 'name': Explanation.name, 'type_identifier': Explanation.type_identifier } )
    return json.dumps( results )


@explanations_api.route( '/findings', methods=['GET'] )
def explanation_findings():
    pass


@explanations_api.route( '/autocomplete', methods=['GET'] )
def explanation_autocomplete():
    '''
        explanation_autocomplete

        Handles autocomplete queries for explanations

        @param term - Substring of explanation name we're searching for.
    '''
    term = request.args.get( 'term', '' )

    explanations = Explanation.query.filter( {'name': {'$regex': '{}'.format(term), '$options':'i'}} )\
                    .limit( 20 )\
                    .ascending( Explanation.name )\
                    .all()

    # Convert into an JSON object
    json_findings = []
    for finding in explanations:
        json_findings.append( { 'id': str( finding.mongo_id ),\
                                'label': finding.name,\
                                'value': finding.name } )
    return json.dumps( json_findings )
