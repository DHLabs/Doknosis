from flask import Flask, request, render_template

import calc_probabilityv12
import doknosis
import pickle
import time
import parseFile
import json
from constants import age_dict, sex_dict, country_dict

# Import API functions
from server.api.findings import findings_api

from server.algos import run_hybrid_1, run_hybrid_2, run_bayesian
from server.cache import cache
from server.constants import ALGO_BAYESIAN, ALGO_HYBRID_1, ALGO_HYBRID_2
from server.db import db, Disease

# Flask components
MAIN  = Flask( __name__ )

def print_timing(func):
    def wrapper(*arg):
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        print '%s took %0.3f ms' % (func.func_name, (t2-t1)*1000.0)
        return res
    return wrapper
    
def create_app( settings = 'server.settings.Dev' ):
    MAIN.config.from_object( settings )
    
    # Initialize db/cache with app
    db.init_app( MAIN )
    cache.init_app( MAIN )
    
    # Register apis
    MAIN.register_blueprint( findings_api, url_prefix='/api' )
    
    return MAIN

def get_algorithm_results( knowns, findings, num_solutions=10, num_combinations=1, algorithm=ALGO_HYBRID_1 ):
    '''
    Required:
        knowns           - What are demographics or key findings that this disease must be associated with
        findings         - What are demographics that we want to associate with our disease

    Optional:
        num_solutions    - How many solutions (m) to print in our list [ default: 10 ]
        num_combinations - How many disease combinations (n) to account for [ default: 1 ]
        algorithm        - What algorithm to choose to run [ default: ALGO_HYBRID_1 ]
    '''

    results = {}

    # Run the current greedy Staal algorithm    
    if algorithm == ALGO_HYBRID_1:
        #If n_disease_combinations is greater than 1, create multiple tables. 
        #Say user chooses 3, then create tables for 1, 2 and 3.
        for num_combinations in range(1, num_combinations+1):

            greedy, other_sols = run_hybrid_1( knowns, findings, 
                                                num_combinations=num_combinations,
                                                num_solutions=num_solutions )

            results[ 'greedy' ]  = greedy
            results[ 'other' ] = other_sols

    # Run Staal's new code
    elif algorithm == ALGO_HYBRID_2:

        #There can be multiple solutions to this particular query
        greedy, other_sols = run_hybrid_2( knowns, findings,
                                            num_combinations=num_combinations,
                                            num_solutions=num_solutions )

        results[ 'greedy' ]  = greedy
        results[ 'other' ] = other_sols
            
    # Run Eli's algorithm            
    elif algorithm == ALGO_BAYESIAN:

        greedy, other_sols = run_bayesian( knowns, findings,
                                            num_combinations=num_combinations,
                                            num_solutions=num_solutions )

        results[ 'greedy' ]  = greedy
        results[ 'other' ] = other_sols

    return results

@MAIN.route( '/diagnosis_result', methods=[ 'GET' ] )
@print_timing #( index took 793.682 ms )
def get_result():
    # Symptoms are passed in as a comma-separated value list of IDs
    # e.g symptoms=1,2,3,4

    if request.args.get( 'findings' ) is None:
        return json.dumps( { 'success': False } )

    findings         = request.args.get( 'findings' ).split( ',' )
    findings         = [ int( x ) for x in findings ]

    num_solutions    = int( request.args.get( 'num_solutions' ) )
    num_combinations = int( request.args.get( 'num_combinations' ) )
    algorithm        = int( request.args.get( 'algorithm' ) )

    # TODO: Support other algorithms
    algorithm = 1

    results = get_algorithm_results( None, findings, 
                                    num_solutions=num_solutions, 
                                    num_combinations=num_combinations,
                                    algorithm=algorithm )
    results[ 'success' ] = True
    return json.dumps( results )

@MAIN.route( '/' )
@MAIN.route( '/index.html' )
def test():
    return render_template( 'index.html' )