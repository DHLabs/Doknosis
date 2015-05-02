import sys
import time

from operator import mul,or_,itemgetter
from heapq import nlargest
from server.db import Explanation
from server.constants import EXPLANATION_TYPE_IDENTIFIERS, EXPLANATION_TYPE_CATEGORIES, EXPLANATION_REGIONS

DEFAULT_TYPE_IDENTIFIER = 'infectious disease'

class AlgoError(Exception):
    """ Exception generated when something precludes algorithms from returning an acceptable result """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return 'Error Running Diagnosis -- \"{}\"!'.format(self.msg)

def fetch_exp_for_findings(type_identifier,findings,regions=EXPLANATION_REGIONS):
    """ For a type identifier and given set of findings, fetch all of the correctly typed explanations which name the findings.

    @param type_identifier String identifying the type of explanatory variable, or "All" for all types.
    @param findings List of finding names to use in query filter.
    """
    try:
        explanations_list = Explanation.query.filter({ 'type_identifier': {'$in': EXPLANATION_TYPE_CATEGORIES[type_identifier]}, 
                                                       'findings.name': {'$in': findings }}).all()
    except Exception as e:
        raise AlgoError('Database error in query for explanations of type {} (list form: {}) with findings in {}: {}'
                        .format(type_identifier,EXPLANATION_TYPE_CATEGORIES[type_identifier],findings,e))

    # Weed out any explanations which have 0 weight associated with a finding we are looking for
    ffunc = lambda expl: not(any([xx.weight == 0 and xx.name in findings for xx in expl.findings]))
    filtered_list = filter(ffunc,explanations_list)

    # Weed out any explanations which do not have overlapping regions with target
    ffunc = lambda expl: (not hasattr(expl,'regions')) or (len(expl.regions) == 0) or (len(set(expl.regions).intersection(set(regions))) > 0)
    filtered_list = filter(ffunc,filtered_list)

    if len(filtered_list) == 0:
        raise AlgoError('Empty findings list!  Before filtering by weights, database query with type {} (list form: {}), findings in {} found: {}.'
                        .format(type_identifier,EXPLANATION_TYPE_CATEGORIES[type_identifier],findings,explanations_list))

    return filtered_list


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

    # Returns all findings - uncovered findings(covered findings = union of findings that the set of explanations cover)
    # the bigger the number the better here
    
    # List of findings covered (with edges to) explanations = reduce(or_,[set(G[e]) for e in explanations],set()
    # len(findings - list_of_findings) = list of all findings not covered by explanations = not_covered
    # so len(findings) - len(not_covered)) = length of covered findings
    a = 1
    b = 1

    # measure: a * (n - n_nc) + b*strength()

    lambdaFunc = (lambda explanations: 
                  a * (len(findings) - len(findings - reduce(or_,[set( explanation_map[ e ].keys() ) for e in explanations],set())))
                  + b * (strengthFunc( explanation_map, explanations, findings))
                  )
    return lambdaFunc


def strengthFunc( explanation_map, explanations, findings):
    """ This seems to be where the probability part of the score comes in.

    For each explanation e, let w_e+ denote the maximum finding weight (over the given set of findings).  Return Prod_e w_e+.
    """
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

        # What the heck ... Pretty sure I have not changed this, but it looks like this greedy algo is returning in a pretty wierd place!!!
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

def run_hybrid_1( knowns, findings, num_solutions=10, num_combinations=1, type_identifier=DEFAULT_TYPE_IDENTIFIER, regions=EXPLANATION_REGIONS):
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

    explanations_list = fetch_exp_for_findings(type_identifier,findings,regions)

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

def run_hybrid_2( knowns, findings, num_solutions=10, num_combinations=1, type_identifier=DEFAULT_TYPE_IDENTIFIER, regions=EXPLANATION_REGIONS ):
    # Filter by knowns

    t1 = time.time()
    explanations_list = fetch_exp_for_findings(type_identifier,findings,regions)

    query_time = ( time.time() - t1 ) * 1000.0

    # Convert from list to hashmap
    for explanation in explanations_list:
        explanation_map[ explanation.name ] = {}

        for finding in explanation.findings:
            explanation_map[ explanation.name ].update( {finding.finding_id: finding.weight} )
    
    # explanations = set( explanations_all.keys() )

    return None
        

def run_bayesian( knowns, findings, num_solutions=10, num_combinations=1, type_identifier=DEFAULT_TYPE_IDENTIFIER, regions=EXPLANATION_REGIONS ):
    """ Simple Naive Bayes approach.

    Probably an oversimplification, but the basic Naive Bayes strategy is to just multiply all the conditionals and
    the prior.  The prior should probably be the probability of the explanation given the demographics.  Conditionals
    are given by edge weights, or assumed to be .5 if not given.

    This does not seem to work very well.  I think it is because it gives far too much weight to the missing edges.
    I don't think the conditional estimates in the database really represent what we think they do, or maybe it is
    just that the missing data is not what we think it is.

    """

    t1 = time.time()
    explanations_list = fetch_exp_for_findings(type_identifier,findings,regions)

    query_time = ( time.time() - t1 ) * 1000.0

    if num_solutions < len(explanations_list):
        num_solutions = len(explanations_list)

    # At some point, this prior should be generated from demographic data:
    prior = {expl.name:.5 for expl in explanations_list}
    posteriors = {expl.name:prior[expl.name]*reduce(mul,[expl.findings_dict().get(fi,0.5) for fi in findings]) for expl in explanations_list}

    # Next we sort them and take the ones with highest probability
    ranked = rank_probs(posteriors, num_solutions)

    # Ignore the combinations for now.
    return (query_time, (ranked[0][0],ranked))
