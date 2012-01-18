
from flask import Flask, request, render_template

import calc_probabilityv12
import doknosis
import pickle
import time

from constants import age_dict, sex_dict, country_dict

# Import API functions
from server.api.findings import findings_api

from server.cache import cache
from server.db import db

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
    # MAIN.register_blueprint( tag_api,    url_prefix='/api' )
    
    return MAIN

def get_algorithm_results( Knowns, Findings ):
    """
    Has three inputs:
    1. choice_of_algorithms: What algorithm to choose to run
    2. m_solutions: How many solutions (m) to print in our list
    3. n_disease_combinations: How many disease combinations (n) to account for
    4. Knowns: What are demographics or key findings that this disease must be associated with
    5. Findings: What are demographics that we want to associate with our disease
    """

    m_solutions = int( request.args.get(buttons['number_of_solutions']))
    n_disease_combinations = int( request.args.get(buttons['number_of_disease_combinations'] ) )
    choice_of_algorithms = request.args.get( buttons['choice_of_algorithms'] )

    table = [['m solutions ' + str(m_solutions) + ' n_disease_combinations: ' + str(n_disease_combinations)]]
    table = [[]]
    if(choice_of_algorithms == '1'):
     #Run the current greedy Staal algorithm

     #If n_disease_combinations is greater than 1, create multiple tables. 
     #Say user chooses 3, then create tables for 1, 2 and 3.
     for n_disease_combo in range(1, n_disease_combinations+1):

         result = calc_probabilityv12.runDiagnosis2(Knowns, Findings, n_disease_combo, m_solutions)

         row1 = [['Greedy solution', str(result[0])]]
         row2 = [[' - ', '  - ']]
         row3 = [['Ranked solutions for ' + str(n_disease_combo) + " diseases", 'Score']]
         table += row1 + row2 + row3

         solutions = result[1]

         for solution in solutions:
             table = table + [solution]

    elif(choice_of_algorithms == '2'):
     #Run Staal's new code
     table = table + [['Staals new code']]

     #There can be multiple solutions to this particular query
     solution_and_values_list = doknosis.runDiagnosis(Findings)

     row0 = [['', 'Percent Covered Each Finding']]
     row1 = [['New greedy solution'] + Findings]

     table = row0 + row1

     for solution in solution_and_values_list:
         table = table + [solution]

    elif(choice_of_algorithms == '3'):
     #Run Eli's algorithm
     ranked_probs = calc_probabilityv12.runDiagnosis(Knowns, Findings)
     row1 = [['Disease', 'Probability']]
     table = row1

     for ranked_prob in ranked_probs:
         table = table + [ranked_prob]
    else:
     #No idea what the user has inputted somehow
     table = table + [['No algorithm chosen']]

    return table

@MAIN.route( '/diagnosis_result' )
#@print_timing #( index took 793.682 ms )
def result():
    # Get the knowns that the user has inputted
    Knowns = []
    tmp = request.args.get( 'required_textarea' ).split( ',' )
    for known in tmp:
        if( len( known ) != 0 ):
            Knowns.append( str( known ).strip() )
        
    print 'Knowns: %s' % ( Knowns )
    
    Findings = []
    tmp = request.args.get( 'hello' ).split( ',' )
    for finding in tmp:
        if( len( finding ) != 0 ):
            Findings.append( str( finding ).strip() )
    
    print 'Findings: %s' % ( Findings )

    # #Allows this current version of our disease calculator to have the updated dictionaries
    # self.update_dictionaries()
    diseasesBytes = cache.get("diseases")
    r_bytes = cache.get("R")
    or_g_bytes = cache.get("OR_G")
    prevalence_bytes = cache.get("prevalence_G")
        
    if(diseasesBytes is not None):
        useDiseases = pickle.loads(diseasesBytes)
        R = pickle.loads(r_bytes)
        OR_G = pickle.loads(or_g_bytes)
        prevalence_G = pickle.loads(prevalence_bytes) 
        calc_probabilityv12.setDictionaries(R, OR_G, prevalence_G)
        doknosis.setDictionaries(OR_G)
        
    # Use a switch on which algorithm to use
    # Each algorithm should return a ranked set of solutions and that is all
    ranked_m_solutions_table = get_algorithm_results(Knowns, Findings)
    
    template_values = {
        'findings': "".join([finding + ", " for finding in Findings]),
        'knowns' : "".join([known + ", " for known in Knowns]),
        'ranked_m_solutions_table' : ranked_m_solutions_table
    }
    
    #self.response.headers['Content-Type'] = "text/html; charset=utf-8"
    return render_template( 'result.html', **template_values )
    # return '<html>boom</html>'

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
    
    # tbl = parseFile.createCSVTable()
    # diseasesList = parseFile.createDiseaseList(tbl)
    # R_dict = parseFile.create_R_dictionary(diseasesList)
    # OR_G_dict = parseFile.create_OR_dictionary(diseasesList)
    # prevalence_G_dict = parseFile.create_prevalence_G_dictionary(diseasesList)
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
    
