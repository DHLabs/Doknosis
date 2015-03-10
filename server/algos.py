import sys
import time

from operator import or_,itemgetter
from heapq import nlargest

from server.db import Explanation

def combinations(iterable, r):
    # combinations('ABCD', 2) --> AB AC AD BC BD CD
    # combinations(range(4), 3) --> 012 013 023 123
    pool = tuple(iterable)
    n = len(pool)
    if r > n:
        return
    indices = range(r)
    yield tuple(pool[i] for i in indices)
    while True:
        for i in reversed(range(r)):
            if indices[i] != i + n - r:
                break
        else:
            return
        indices[i] += 1
        for j in range(i+1, r):
            indices[j] = indices[j-1] + 1
        yield tuple(pool[i] for i in indices)

def bruteN(explanations, measure, n = 1):
    """
    rank all size n explanations according to measure.
    
    returns [(value, set)] list.
    """
    #For all sets of size n, finds the greatest measure function given certain explanations
    #Returns every computed set with ranked by score from greatest to least
    #Returns a tuple with the (score, the set of explanations(input))
    return sorted(map(lambda x: (measure(x), x), combinations(explanations, n)), reverse = True)
    #TODO this is not anything useful right here


def createMeasure( explanation_map, findings, w = lambda x: 1, f = lambda x: 1, d = lambda x: 1):
    '''
    Potentially add a fourth parameter that uses the relationship between the explanations
    How likely a set of explanations are able to explain a particular finding
    Binary, full graph, for example the edge is 0 if two explanations cannot coexist together
    And edge weight 1 if one explanation is necessary for the other. Ex. HIV -> PCP (pneuomocystis carinii  pneumonia). Diabetes-> Diabetes retinopathy. Directed graph
    Diabetes can exist without diabetes retinopathy, but diabetes retinopathy cannot exist without diabetes
    The greater the number the better
    '''

    #Returns all findings - uncovered findings(covered findings = union of findings that the set of explanations cover)
    #the bigger the number the better here
    
    #List of findings covered (with edges to) explanations = reduce(or_,[set(G[e]) for e in explanations],set()
    #len(findings - list_of_findings) = list of all findings not covered by explanations = not_covered
    #so len(findings) - len(not_covered)) = length of covered findings
    a = 1
    b = 1

    lambdaFunc = (lambda explanations: a * (len(findings) - len(findings - reduce(or_,[set( explanation_map[ e ].keys() ) for e in explanations],set())))
                  + b * (strengthFunc( explanation_map, explanations, findings)) 
                  )
    return lambdaFunc


def strengthFunc( explanation_map, explanations, findings):
    explanations_to_finding_weight = []
    
    for explanation in explanations:
        findingToExplanationWeight = explanation_map[explanation]
        list_of_weights = []

        for finding in findings:
            weight = 0
            if finding in findingToExplanationWeight:
                weight = findingToExplanationWeight[finding]

            list_of_weights.append( weight )

        bestToWorstWeights = sorted(list_of_weights, reverse = True)
        
        explanations_to_finding_weight.append(bestToWorstWeights[0]) #lets use the best weight
    
    strength = 1
    for weight in explanations_to_finding_weight:
        strength = strength * weight

    return strength

def greedy(G, findings, measure):
    '''
    find set of explanations for a set of observations/findings greedily.

        Assumptions:
      G[explanation] = iterable of observations for this explanation
      G is iterable over explanations
      observations/findings is a set of observations to be explained
      measure(set of explanations) = quality of solution
    '''
    findings = findings.copy()
    sol = []
    explanations = set(G)

    bestQuality = -sys.maxint
    stalled = False
    while findings and explanations and not stalled:
        candidates = sorted(map(lambda x : (measure(sol + [x]), x), explanations), reverse=True)

        value, best = candidates[0]
        if value <= bestQuality:
            stalled = True
        else:
            covered = findings & set(G[best])
            findings -= covered
            explanations.remove(best)
            sol += [best]
            bestQuality = value
        return sol


def rank_probs(prob_explanation, m_largest=10):
    """Rank probabilities from largest to smallest
    And get m_largest amount
    """
    return nlargest(m_largest, prob_explanation.iteritems(), itemgetter(1))

def tupleToDict(list_of_tuples):
    """
    We want to convert from a list of tuples to a dictionary structure
    
    so we have [(val, (string1, string2), etc]
    
    to
    a dictionary structure
    D[string1_string2] = val
    """
    
    explanations_to_prob_dict = {}
    for tuple in list_of_tuples:
        val = tuple[0]
        explanation_names = ', '.join( tuple[1] )
        explanations_to_prob_dict[ explanation_names ] = val

    return explanations_to_prob_dict

def run_hybrid_1( knowns, findings, num_solutions=10, num_combinations=1, type_identifier="Disease" ):
    '''
    Vinterbo Country, find best solution for findings in G using Greedy and Measure

    Parameters:
        knowns      - List of knowns about the patient ( age, sex, country of origin )
        findings    - List of symptoms
    '''

    # Using Vinterbo solution
    explanations_list = None

    # Filter by knowns
    t1 = time.time()
    if type_identifier == "All":
        explanations_list = Explanation.query.filter({ 'findings.name': {'$in': findings }}).all()    
    else:
        explanations_list = Explanation.query.filter({'type_identifier': {'==':type_identifier}}, { 'findings.name': {'$in': findings }}).all()

    query_time = ( time.time() - t1 ) * 1000.0

    findings = set( findings )

    # Convert from list to hashmap
    explanation_map = {}
    for explanation in explanations_list:
        explanation_map[ explanation.name ] = {}

        for finding in explanation.findings:
            explanation_map[ explanation.name ].update( {finding.name: finding.weight} )

    measure = createMeasure( explanation_map, findings )
    greedy_solution = greedy( explanation_map, findings, measure )
    
    if greedy_solution is not None:
        greedy_sol = str(greedy_solution[0])
    else:
        greedy_sol = "No greedy solution"
        
    sizeN_sol = bruteN( explanation_map, measure, num_combinations )

    sizeN_sol_dict = tupleToDict( sizeN_sol )

    ranked_sizeN_m_sol = rank_probs( sizeN_sol_dict, num_solutions )
    
    results =  ( greedy_sol, ranked_sizeN_m_sol )

    return ( query_time, results )

def run_hybrid_2( knowns, findings, num_solutions=10, num_combinations=1, type_identifier="Disease" ):
    # Filter by knowns
    # explanations_all  = Explanation.query.all()
    if type_identifier == "Any":
        explanations_list = Explanation.query.filter({ 'findings.name': {'$in': findings }}).all()
    else:
        # I think there's a cleaner way to do this, but trying not to mess with what's already here.
        explanations_list = Explanation.query.filter({'type_identifier': {'==':type_identifier}}, { 'findings.name': {'$in': findings }}).all()

    # Convert from list to hashmap
    for explanation in explanations_list:
        explanation_map[ explanation.name ] = {}

        for finding in explanation.findings:
            explanation_map[ explanation.name ].update( {finding.finding_id: finding.weight} )
    
    # explanations = set( explanations_all.keys() )

    return None
        

def run_bayesian( knowns, findings, num_solutions=10, num_combinations=1, type_identifier="Disease" ):
    pass
