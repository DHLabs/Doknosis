'''
    server.api.diseases

    Handles API calls to manipulate/list diseases.
'''
import json

from flask import Blueprint, request

from server.db import Disease

diseases_api = Blueprint( 'diseases_api', __name__ )


@diseases_api.route( '/list', methods=['GET'] )
def disease_list():
    '''
        Return a list of diseases in the system.

        @params
        page        Page of results to return

        @returns
        A JSON list of diseases in the system.
    '''
    page = int( request.args.get( 'page', '1' ) )

    pagination = Disease.query.ascending( Disease.name )\
                            .paginate( page=page, per_page=100 )

    results = []
    for disease in pagination.items:
        results.append( { 'id': Disease.id, 'name': Disease.name } )
    return json.dumps( results )


@diseases_api.route( '/findings', methods=['GET'] )
def disease_findings():
    pass
