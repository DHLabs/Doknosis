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
from server.db import db, Disease

# Algorithm choice constants
ALGO_HYBRID_1 = 1
ALGO_HYBRID_2 = 2
ALGO_BAYESIAN = 3

# Flask components
MAIN  = Flask( __name__ )

buttons = {'age': 'AgeGroup_DropDownMenu', 
           'country':'CountryGroup_DropDownMenu', 
           'sex' : 'Sex_DropDownMenu',
           'findings' : 'Findings_TextArea',
           'number_of_solutions' : 'NumberOfSolutions_DropDownMenu', #Top "m" of solutions that the algorithm prints out
           'number_of_disease_combinations' : 'number_of_disease_combinations_DropDownMenu', #Number of "n" diseases the greedy algorithm takes into account
           'choice_of_algorithms' : 'choice_of_algorithms_dropdownmenu' #what algorithm do we want to use to rank the diseases
           }

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
#@print_timing #( index took 793.682 ms )
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

@MAIN.route( '/test' )
def test():
    return render_template( 'index.html' )
    
@MAIN.route( '/' )
@MAIN.route( '/index.html' )
# @print_timing # ( index took 831.225 ms )
# 156.549 ms
def index():
    '''
        On the main page allow the user the following capabilities.

        The required findings (set as a known, so delete any disease which does not have this finding)

        Select which set covering method they want to employ for calculation.

        (If you don't want to report a finding, don't enter it.
    '''    
    diagnosis_result_path = "/diagnosis_result"
    
    diseases = Disease.query.limit(1).one()
    print set( diseases.findings )
    #tbl = parseFile.createCSVTable()
    #findings,diseasesList = parseFile.createDiseaseList(tbl)
    #R_dict = parseFile.create_R_dictionary(diseasesList)
    #print R_dict[ 'Leprosy' ]
    # OR_G_dict = parseFile.create_OR_dictionary(diseasesList)
    # print OR_G_dict['Leprosy']
    # prevalence_G_dict = parseFile.create_prevalence_G_dictionary(diseasesList)
    # print prevalence_G_dict[ 'Leprosy' ]
    # 
    # #Cache all these results
    # cache.set( 'diseases', pickle.dumps(diseasesList))
    # cache.set("R", pickle.dumps(R_dict))
    # cache.set("OR_G", pickle.dumps(OR_G_dict))
    # cache.set("prevalence_G", pickle.dumps(prevalence_G_dict))    
    # calc_probabilityv12.setDictionaries(R_dict, OR_G_dict, prevalence_G_dict)
    # 
    # findings_list = calc_probabilityv12.findings_dict()
    
    # Strings delimited by a comma that allow the user to choose which are "required" demographics
    requiredDemographicsString = ""
    for keys in age_dict.keys():
      requiredDemographicsString += keys + ","
    for keys in sex_dict.keys():
      requiredDemographicsString += keys + ","
    for keys in country_dict.keys():
      requiredDemographicsString += keys + ","

    #Number of solutions that we shall print out in our table
    number_of_solutions = [(10, 10), (1, 1), (5, 5), (20, 20)]

    #Number of disease combinations that we shall solve for greedily
    number_of_disease_combinations = [(1, 1), (2, 2), (3, 3), (4, 4)]

    choice_of_algorithms = [(1, 'Hybrid 1') , (2, 'Hybrid 2'), (3, 'Bayesian')]

    template_values = {
      'country_dict' : country_dict,
      'diagnosis_result_path': diagnosis_result_path,
      'age_dict' : age_dict,
      'sex_dict' : sex_dict,
      'buttons' : buttons,
      'number_of_solutions' : number_of_solutions,
      'choice_of_algorithms' : choice_of_algorithms,
      'number_of_disease_combinations' : number_of_disease_combinations,
      'requiredDemographicsString' : requiredDemographicsString,
      }

    return render_template( 'diagnosis_simple.html', **template_values )
    
