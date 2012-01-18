#!/usr/bin/env python
# encoding: utf-8
"""
calc_probability1.1.py

Modified and maintained by David Lluncor 2010-1-25

Created by Eliah aronoff spencer on 2010-12-27, also defs by Staal A. Vinterbo, from sometime in december.
Copyright (c) 2010 EAS/SAV. All rights reserved.

DxTer/DokBot/GuruDok: Working Names
Differential Diagnosis Calculator.

Contains a primary dictionary R with keys = disease, values = set(knowns, findings), where knowns are high edge-weight findings (neccessary)
by which a new dictionary G is created by deleting k:v pairs for which knowns not in R.  Initially populated from WHO GBD site. Knowns can be ages, race,
sex, location, comorbidities, medications etc. Currently limited to ages group and location.

Sub dictionaries for prevalence and odds ratios: Prevalence data drawn from WHO and CDC sites initially and represents the disease
node weight with prevalence = prior odds. Odds ratios  map findings to disease in G, and are represented as an arc weight from finding node to disease node.

Likelyhood of disease is then node weight * prod(arc weight(findings)) for findings in disease in G. Can represent the likelyhood as an energy function
where the probability of the ith disease in n diseases is the partition function: p_i= E_i/Sum_n(E_n). Giving a baysian belief network for
a bipartite disease:finding dictionary. Given accurate prevalence and O.R. data this approach should yeild accurate disease sets with internally
consistant probabilities. However, data may be either sparse or innacurate and patient findings may not be representative for multiple reasons.

Can alleviate some of these issues by taking network approach on reduced dictionary, using cutoff function to  preferentially map high arc-weight
findings to disease. Additionally by allowing for concomitant diseases to explain findings we introduce additional explanation-space covering.
Can introduce dependent diseases (eg AIDS defining illnesses, diabetic complications, etc, by placing necessary variable in R so that it is deleted
in G in the absence of the required parent finding/known.). Currently have separated two functionalities. First is a simple baysian network which uses
the dictionary and partition function literally. The second contains the Norwegian approach. Now need to blend these into perfection....

"""
import sys
import os
from operator import add, mul, itemgetter, or_
#from itertools import *
#from itertools import combinations
#from itertools import product, combinations
from collections import defaultdict
from heapq import nlargest
from pprint import pprint

""" Added because Python 2.5 does not have product or combinations """
def product(*args, **kwds):
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x+[y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)

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

def reduce_dictionary2(D, knowns):
    """Takes dictionary D with all possible explanations and deletes entries not containing knowns
        as one of the items in their list of values
        D - Original dictionary
        knowns - values that we will look for in the list of values in an entry of D 
    """
    reducedDict = D
    
    #The disease has to have all knowns so known1 is value AND known2 is value AND known3 is value
    
    len_knowns = len(knowns)
    
    for key in D.keys():
        matching = 0
        value_list = D[key]
        #Assume there is no match until seen otherwise
        for known in knowns:
            if(known in value_list):
                matching = matching + 1
        if(matching != len_knowns):
            del reducedDict[key]
            
    return reducedDict

#def reduce_dictionary(R, d, knowns):
#    """Takes dictionary R with all possible explanations and deletes entries not containing knowns
#        R - Original dictionary
#        d - 
#    """
#    G = R
#    j=1
#    i = j - 1
#    while (i < len(d)):
#        for k in R:
#            v =  d[i]
#            G[v] = R[v]
#        if (knowns[0] or knowns[1]) not in R[v]:
#            del(G[v])
#            i = (i + 1)
#        else:
#            i = (i + 1)
#    return G

class CalculateProbability:
    R = {}
    OR_G = {}
    prevalence_G = {}
    
    def __init__(self, R_dict, OR_G_dict, prevalence_G_dict):
        self.R = R_dict
        self.OR_G = OR_G_dict
        self.prevalence_G = prevalence_G_dict
        
     
    
    
def calc_prior(prevalence_G, country):
    """
    Given a country and diseases, create a smaller dictionary from
    prevalence_G that just contains prevalence_G[disease] = (probability for that country of having that disease)
    """
    
    #prior_odds will be our smaller dictionary containing only values we find relevant
    prior_odds = {}
    
    diseases = prevalence_G.keys()
    
    for disease in diseases:
        prevalence_dict_disease = prevalence_G[disease]
        prior_odds[disease] = prevalence_dict_disease[country]
    
    return prior_odds 
    
#def calc_prior(prevalence_G, diseases, country):
#	"""Lookup up prevalence as a function of location for disease in G from prevalence dictionary."""
#	j=1
#	i = j-1
#	h = j-1
#	prior_odds_i = {}
#	prevalence_dict_i = {}
#	prevalence_disease_i = {}
#	while i < len(diseases):
#		for k, v in prevalence_G.items():
#			disease_i = diseases[i]
#			prevalence_dict = prevalence_G[disease_i]
#			prevalence_disease_i[disease_i] = prevalence_dict[country]
#			prior_odds_i = prevalence_disease_i
#		i += 1
#	return prior_odds_i

def calc_likelyhood_f(OR_G, findings):
    """
        OR_G[disease] = dictionary of finding -> probability finding has to do with disease
        
        we want a dictionary for each disease that gets each probability for the finding corresponding to the disease
        and multiply all those values so
        
        LIKELIHOOD_GIVEN_FINDINGS[disease] = P(disease|finding1) * P(disease|finding2) ...
    """
    
    diseases = OR_G.keys()
    
    likelihood_given_findings = {}
    
    for disease in diseases:
        OR_disease = OR_G[disease]
        #for each finding get the probability it corresponds to a particular disease (by getting its "odds ratio"
        existsFinding = False #if none of the findings are in this disease's odd ratio then = 0
        union_probability = 1 #probability we get by multiplying everything
        
        for finding in findings:
            if(finding in OR_disease.keys()):
                existsFinding = True
                union_probability = union_probability * OR_disease[finding]
        
        #Now here we should have calculated the multiplied probability for all findings for the particular disease
        if(existsFinding):
            likelihood_given_findings[disease] = union_probability
        else:
            likelihood_given_findings[disease] = 0
                
    return likelihood_given_findings    

#def calc_likelyhood_f(OR_G, diseases, findings):
#	"""Calculate likelyhood of findings mapping to disease by multlying odds ratios of findings for a given disease in dictionary OR_G"""
#	j=1
#	i = j-1
#	likelyhood_i= {}
#	while i < len(diseases):
#		disease_i = diseases[i]
#		h = j-1
#		l = OR_t = []
#		stalled = False
#		while (h < len(findings)) and not stalled:
#			finding = findings[h]
#			OR_i = OR_G[disease_i]
#			if finding not in OR_i.keys():
#				h += 1
#			else:
#				OR_n = OR_i[finding]
#				if OR_n not in OR_t and not stalled:
#					l.append(OR_n)
#					likelyhood_i[disease_i] = (reduce(mul,l))
#			h += 1
#		i += 1
#	return likelyhood_i

def calc_odds(G, prior_odds, likelyhoods):
    """Calculate odds of ith disease in G as prior odds * likelyhood"""
    #should be a dictionary
    post_odds = {}
     
    for disease in G.keys():
        #if we did not calculate values for these particular diseases, then their probabilities are assumed to be 0
        if(not(disease in prior_odds.keys()) or not(disease in likelyhoods.keys())):
            post_odds[disease] = 0
        else:
            prior_odd = prior_odds[disease]
            likelyhood = likelyhoods[disease]
            post_odds[disease] = prior_odd * likelyhood
    
    return post_odds

#def calc_odds(G, prior_odds_n, likelyhood_n):
#	"""Calculate odds of ith disease in G as prior odds * likelyhood"""
#	prior_odds = prior_odds_n.values()
#	likelyhood = likelyhood_n.values()
#	post_odds = [i*j for i,j in zip(prior_odds,likelyhood)]
#
#	return post_odds

def normalize_probs(odds_of_diseases_dict):
    """Normalize odds using partition function to give probabilities"""
    normalized_probs = {}
    
    sumOfOdds = sum(odds_of_diseases_dict.values())
    
    for disease in odds_of_diseases_dict:
        if(sumOfOdds != 0):
            normalized_probs[disease] = odds_of_diseases_dict[disease] / float(sumOfOdds)
        else:
            normalized_probs[disease] = 0
            
    return normalized_probs

#def calc_prob(G, odds_n):
#	"""Normalize odds using partition function to give probabilities"""
#	odds = odds_n
#	prob_i = [i/sum(odds) for i in odds]
#	return prob_i

def rank_probs(prob_disease, m_largest=10):
    """Rank probabilities from largest to smallest
    And get m_largest amount
    """
    return nlargest(m_largest, prob_disease.iteritems(), itemgetter(1))

#SAV defs
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

def calc_prevalence(prevalence_G):
    return prevalence_G

def strengthFunc(explanations, findings):
    #explanation is a disease
    explanations_to_finding_weight = []
    
    for explanation in explanations:
        findingToDiseaseWeight = OR_G[explanation]
        list_of_weights = []
        for finding in findings:
            if(findingToDiseaseWeight.has_key(finding)):
                weight = findingToDiseaseWeight[finding]
            else:
                weight = 0
            list_of_weights.append(weight)
        bestToWorstWeights = sorted(list_of_weights, reverse = True)
        
        explanations_to_finding_weight.append(bestToWorstWeights[0]) #lets use the best weight
    
    strength = 1
    for weight in explanations_to_finding_weight:
        strength = strength * weight
        
    return strength

def createMeasure(G, findings, w = lambda x: 1, f = lambda x: 1, d = lambda x: 1):
    #Potentially add a fourth parameter that uses the relationship between the explanations
    #How likely a set of explanations are able to explain a particular disease(finding)
    #Binary, full graph, for example the edge is 0 if two explanations cannot coexist together
    #And edge weight 1 if one explanation is necessary for the other. Ex. HIV -> PCP (pneuomocystis carinii  pneumonia). Diabetes-> Diabetes retinopathy. Directed graph
    #Diabetes can exist without diabetes retinopathy, but diabetes retinopathy cannot exist without diabetes
    #The greater the number the better

    #Returns all findings - uncovered findings(covered findings = union of findings that the set of explanations cover)
    #the bigger the number the better here
    
    #List of findings covered (with edges to) explanations = reduce(or_,[set(G[e]) for e in explanations],set()
    #len(findings - list_of_findings) = list of all findings not covered by explanations = not_covered
    #so len(findings) - len(not_covered)) = length of covered findings
    a = 1
    b = 1
    lambdaFunc = (lambda explanations: a * (len(findings) - len(findings - reduce(or_,[set(G[e]) for e in explanations],set())))
                  + b * (strengthFunc(explanations, findings)) 
                  )
    return lambdaFunc
    
    
def createMeasureBad(G, knowns, findings,
	w = lambda x: calc_odds(OR_G), f = lambda x: 1, d = lambda x: calc_prevalence(prevalence_G)):
    
    '''
    needs to return comparables

    Assumptions:
    G[explanation] = iterable of observations for this explanation
    G is iterable over explanations
    observations is a set of observations to be explained
    w((observation, explanation) -> R
    f(observation) -> R
    d(explanation) -> R

    Return value: a function that takes a set of explanations and returns
      a real value.

    Here standard set covering
    '''
    #Potentially add a fourth parameter that uses the relationship between the explanations
    #How likely a set of explanations are able to explain a particular disease(finding)
    #Binary, full graph, for example the edge is 0 if two explanations cannot coexist together
    #And edge weight 1 if one explanation is necessary for the other. Ex. HIV -> PCP (pneuomocystis carinii  pneumonia). Diabetes-> Diabetes retinopathy. Directed graph
    #Diabetes can exist without diabetes retinopathy, but diabetes retinopathy cannot exist without diabetes
    #The greater the number the better

    #Returns all findings - uncovered findings(covered findings = union of findings that the set of explanations cover)
    #the bigger the number the better here
    
    #List of findings covered (with edges to) explanations = reduce(or_,[set(G[e]) for e in explanations],set()
    #len(findings - list_of_findings) = list of all findings not covered by explanations = not_covered
    #so len(findings) - len(not_covered)) = length of covered findings
     
    
                                          
    origFunc = (lambda explanations: prob_diseases_given_findings(knowns, findings, explanations) + len(findings) - len(findings - reduce(or_,[set(G[e]) for e in explanations],set())))
    return origFunc

def tupleToDict(list_of_tuples):
    """
    We want to convert from a list of tuples to a dictionary structure
    
    so we have [(val, (string1, string2), etc]
    
    to
    a dictionary structure
    D[string1_string2] = val
    """
    
    diseases_to_prob_dict = {}
    
    for tuple in list_of_tuples:
        val = tuple[0]
        tupleDiseaseNames = tuple[1]
        name = ""
        for diseaseName in tupleDiseaseNames:
            name = name + " " + diseaseName + ", " #more like a string to string method, will need to be changed when want to pretty up printing of diseases in table
        
        diseases_to_prob_dict[name] = val
         
    return diseases_to_prob_dict

# http://code.activestate.com/recipes/498130-create-sql-tables-from-csv-files/
R = {}
OR_G = {}
prevalence_G = {}

def runDiagnosis(Knowns, Findings):
    """
    Use prevalence information only if you have NO finding for a specific class.
    
    Otherwise, only use information from the OR_G dictionary, which is really the conditional probability table
    """
    ######################Some basic  input   ###########################################
    knowns = Knowns
    findings = Findings

    #Potentially add filters here so the person can specify exactly what they are looking for
    
    #For now ignore knowns, treat everything as findings
    if(len(findings) == 0):
        country = knowns[1]
        prior_odds_n = calc_prior(prevalence_G, country)
        #that's it only use prior odds
        odds_n = prior_odds_n
    else:
        #only use likelihood
        likelyhood_n = calc_likelyhood_f(OR_G, findings)
        #that's it only use likelihood 
        odds_n = likelyhood_n
        
    #TODO: make sure that this outputs a non-zero 0, that when you have findings that are in a disease, that it gives you non-zero values
    #TODO: make a list of the findings that we have in our dictionary, each are a button
    # a square matrix of buttons
    # auto-complete: for dictionaries
    #TODO: change significant figures
    
    normalized_probs = normalize_probs(odds_n)
    ranked_probs = rank_probs(normalized_probs)
    
#    prob_n = calc_prob(G, odds_n)
#    prob_disease=dict(zip(diseases,prob_n))
#    ranked_probs = rank_probs(prob_disease)
#    print("A",  knowns[0],  "patient in ",  knowns[1],  "presenting with",  findings,  "most likely has:")
    return ranked_probs


#We want to know what is the probability that P(explanations|findings), maximize
def prob_diseases_given_findings(knowns, findings, diseases):
    #only uses diseases or explanations in calculating probabilities
    """
        result = the P(disease1|findings,knowns) + P(disease2|findings,knowns) + ...P(diseaseN|findings,knowns)
    """
    G = reduce_dictionary2(R, knowns)
    
    #diseases= G.keys()
    
    #country = knowns[1]
    
    #prior_odds_n = calc_prior(prevalence_G, country)
    likelyhood_n = calc_likelyhood_f(OR_G, findings)
    odds_n = likelyhood_n #assume that our location is a finding and just use that as an odds ratio
    
    #diseases = likelyhood_n.keys()
    
    #dictionary of keys: diseases, values: their posterior odds
    #odds_n = calc_odds(G, prior_odds_n, likelyhood_n)
    #normalized_probs = normalize_probs(odds_n) #we can't normalize odds b/c if we have one disease, then that "normalized prob" is always 1
    
    retVal = 0
    
    for disease in odds_n.keys():
        retVal = retVal + odds_n[disease]
    
    return retVal
    
    
def setDictionaries(R_dict, OR_G_dict, prevalence_G_dict):
    """
    Sets what the global dictionaries that we are using are for R_dict, OR_G, and prevalence_G
    """
    global R, OR_G, prevalence_G
    R = R_dict
    OR_G = OR_G_dict
    prevalence_G = prevalence_G_dict
    
##########################Vinterbo Country, find best solution for findings in G using Greedy and Measure #########################################
def runDiagnosis2(Knowns, Findings, number_of_disease_combinations, m_solutions):
    #Using Vinterbo solution
    findings = Findings
    knowns = Knowns

    findings = set(findings)
    #TODO maybe don't reduce
    G = R
    G = reduce_dictionary2(R, knowns)
    measure = createMeasure(G, findings)
#print('target observations: ' + str(findings))
#print('Doing standard set covering:')

    greedy_solution = greedy(G, findings, measure)
    
    if(greedy_solution):
        greedy_sol = str(greedy_solution[0])
    else:
        greedy_sol = "No greedy solution"
        
    sizeN_sol = bruteN(G, measure, number_of_disease_combinations)
    
    sizeN_sol_dict = tupleToDict(sizeN_sol)
    
    ranked_sizeN_m_sol = rank_probs(sizeN_sol_dict, m_solutions)
    
    return [greedy_sol, ranked_sizeN_m_sol]
#print('Greedy solution: ' + str(greedy(G, findings, measure)))
#print('Ranking of all size 1 solutions: ')
#pprint(bruteN(G, measure, 1))
#print('Ranking of all size 2 solutions: ')
#pprint(bruteN(G, measure, 2))

"""


Edge weight = where each edge weight is the odds ratio


if you have this finding, you probably don't have this disease  

Syphillis - have 2 different findings typically 

Maximize (covered explanations) + maximize (P(explanations|findings)) * (compatability graph of explanations)

One disorder that explains the 


(add those numbers) and multiply by 

Does it matter what the patient does not have? Do pre-processing? Do we have to address a lack of negative findings

Initially all combinations of diseases are OK

Then, you can't have two diseases together, put the weight to zero (at the end of the createMeasure function by the 0 -1 edge weight
map between explanations. Could potentially use it as a penalizer for size (put 0.75 default, greater than that good, less than 0.75 severely decrease, 0 means impossible
"""



###########New file######
"""

Purpose of this class is to dynamically update the input values of the main page
in order to match the values that we will be sending into the dictionary lookups in our calc_probability class

"""

"""
    Will return a dictionary mapping our prevalence values 
    Currently: africa, south america, asia, europe, north america
"""
def known1_dict():
    #should return the values we use as keys for our prevalence data lookups
    countries_in_dict = prevalence_G.values()[0].keys()
    
    country_dict = {}
    
    for country in countries_in_dict:
        cap_country = ""
        for part in str.split(country):
            cap_country = cap_country + " " + part.capitalize()
        country_dict[country] = cap_country
    
    #Should be {'africa': 'Africa', 'north america': 'North America' ....}    
    return country_dict

"""
    Will return a dictionary mapping our ages groups
    Currently: child, adult, whatever will come from the csv file
"""

def known2_dict(keys_known2):
    #Will eventually get this from a column, or somewhere in a csv file
    known2keys = ['infant','child','adult', 'elderly']
    known2keys = keys_known2
    
    known2_dict = {}
     
    for known2 in known2keys:
        cap_known2 = ""
        for part in str.split(known2):
            cap_known2 = cap_known2 + " " + part.capitalize()
        known2_dict[known2] = cap_known2
    
    #Should be {'infant': 'Infant', 'child': 'Child', ...}
    return known2_dict

"""
    Will return a list of findings that could be present in the form of a list
    
"""

def findings_dict():
    diseases = OR_G.keys()
    
    findings = []
    
    #Create a list of unique findings
    for disease in diseases:
        findings_for_disease = OR_G[disease].keys()
        for finding_for_disease in findings_for_disease:
            if(finding_for_disease not in findings):
                findings.append(finding_for_disease)
    #explanation = R.keys()
    findings = sorted([finding.lower() for finding in findings])
    return findings

def checkDictionaries():
    """
        Are the dictionaries set properly?
    """
    global R, OR_G, prevalence_G
    if(len(R) == 0 or len(OR_G) == 0 or len(prevalence_G) == 0):
        return False
    else:
        return True
    