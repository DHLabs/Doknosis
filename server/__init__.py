import json
import time

# import calc_probabilityv12
# import doknosis
# import parseFile

from flask import Flask, request, render_template,flash

# Import API functions
from server.api.admin import admin_api
from server.api.explanations import explanations_api
from server.api.findings import findings_api

from server.algos import run_hybrid_1, run_hybrid_2, run_bayesian, AlgoError
from server.cache import cache
from server.constants import ALGO_BAYESIAN, ALGO_HYBRID_1, ALGO_HYBRID_2
from server.db import mongo, Finding

# Flask components
MAIN  = Flask( __name__, static_folder='../static',
                       template_folder='../templates' )


def create_app( settings='server.settings.Dev' ):
    MAIN.config.from_object( settings )

    # Initialize db/cache with app
    # db.init_app( MAIN )
    cache.init_app( MAIN )
    mongo.init_app( MAIN )

    # Register apis
    MAIN.register_blueprint( findings_api,  url_prefix='/api/finding' )
    MAIN.register_blueprint( explanations_api,  url_prefix='/api/explanation' )
    MAIN.register_blueprint( admin_api,     url_prefix='/admin' )

    return MAIN


def get_algorithm_results( knowns, findings, 
                           num_solutions=10,
                           num_combinations=1,
                           type_identifier="Disease",
                           algorithm=ALGO_HYBRID_1 ):
    '''
    Required:
        knowns           - What are demographics or key findings that this
                            explanatory variable must be associated with
        findings         - What are demographics that we want to associate
                            with our explanatory variable

    Optional:
        num_solutions    - How many solutions (m) to print in our list
                            [ default: 10 ]
        num_combinations - How many explanatory variable combinations (n) to account for
                            [ default: 1 ]
        type_identifier  - Which explanations to take into account (Drug, Disease, any other?)
                            [ default: Disease ]
        algorithm        - What algorithm to choose to run
                            [ default: ALGO_HYBRID_1 ]
    '''

    results = {}

    # Run the current greedy Staal algorithm
    if algorithm == ALGO_HYBRID_1:
        # If n_combinations is greater than 1, create multiple tables.
        # Say user chooses 3, then create tables for 1, 2 and 3.
        results[ 'greedy' ] = []
        results[ 'other' ]  = []

        for combinations in range(1, num_combinations + 1):

            query_time, solutions = run_hybrid_1( knowns, findings,
                                                num_combinations=combinations,
                                                type_identifier=type_identifier,
                                                num_solutions=num_solutions )
            greedy, other_sols = solutions
            results[ 'query_time' ] = ' %0.3f' % ( query_time )
            results[ 'greedy' ].append( greedy )
            results[ 'other' ].extend( other_sols )

    # Run Staal's new code
    elif algorithm == ALGO_HYBRID_2:

        #There can be multiple solutions to this particular query
        greedy, other_sols = run_hybrid_2( knowns, findings,
                                           num_combinations=num_combinations,
                                           type_identifier=type_identifier,
                                           num_solutions=num_solutions )

        results[ 'greedy' ]  = greedy
        results[ 'other' ] = other_sols

    # Run Eli's algorithm
    elif algorithm == ALGO_BAYESIAN:

        query_time, solutions = run_bayesian( knowns, findings,
                                              num_combinations=num_combinations,
                                              type_identifier=type_identifier,
                                              num_solutions=num_solutions )

        greedy, other_sols = solutions
        results[ 'query_time'] = ' %0.3f' % (query_time)
        results[ 'greedy' ]  = greedy
        results[ 'other' ] = other_sols

    return results


@MAIN.route( '/diagnosis_result', methods=[ 'GET' ] )
def get_result():
    # Symptoms are passed in as a comma-separated value list of IDs
    # e.g symptoms=1,2,3,4

    if request.args.get( 'findings' ) is None:
        return json.dumps( { 'success': False, 'error':'Failed to load findings.' } )

    findings = request.args.get( 'findings' ).split( ',' )

    # We were previously checking for these guys in the database, but since the autocomplete comes
    # from there, this should be unnecessary.
    # try:
    #     db_findings = Finding.query.filter({ 'name': {'$in': request.args.get( 'findings' ).split( ',' ) }}).all()
    # except Exception as e:
    #     raise AlgoError('Database error trying to match findings: {}'.format(e))

    # findings = [dbf.name for dbf in db_findings]

    # if len(findings) != len(finding_list):
    #     flash('Findings not in database: {}'.format(set(findings_list)-set(findings)),'error')

    num_solutions    = int( request.args.get( 'num_solutions' ) )
    num_combinations = int( request.args.get( 'num_combinations' ) )
    type_identifier = request.args.get( 'type_identifier' )
    algorithm        = int( request.args.get( 'algorithm' ) )

    algorithm = ALGO_HYBRID_1

    try:
        results = get_algorithm_results( None, findings,
                                         num_solutions=num_solutions,
                                         num_combinations=num_combinations,
                                         type_identifier=type_identifier,
                                         algorithm=algorithm )
        results[ 'success' ] = True

    except AlgoError as er:
        flash('Error!  {}'.format(er.msg),'error')
        results = {'success':False,'error':er.msg}

    return json.dumps( results )


@MAIN.route( '/' )
@MAIN.route( '/index.html' )
def index():
    '''
        Render the main page
    '''
    return render_template( 'index.html' )
