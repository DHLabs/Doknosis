# -*-Python-*-
################################################################################
#
# File:         evals.py
# RCS:          $Header: $
# Description:  
# Author:       Staal Vinterbo
# Created:      Wed Jun  8 15:58:33 2011
# Modified:     Thu Jun  9 01:07:31 2011 (Staal Vinterbo) staal@ball
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2011, Staal Vinterbo, all rights reserved.
#
################################################################################


# In attempting to modify this, I had to do a bunch of commenting so that I understand the code.  In the process,
# I came up with lots of Questions.  Here are a few of them, by method:
#
#   in greedy method:
# 1) How does this work if set(E) and set(target) have no intersection?  Then sol is empty, right?
# 2) Why all the redundant calculations (e.g., re-calculating coverage for every value of tau)?
# 3) Why does avail also include the initial elements of sol?  Shouldn't it be avail = list(set(E) - set(target))?
# 4) Have to think about this more, but does it really make sense to compare the coverage threshold from one round with a given value of
#    tau against that from the next round with a different value?
# 5) What is the purpose of eprev and gamma methods, which are fixed at 1 in this script?
#
#   in runDiagnosis method:
# 1) Is longest common substring better than something like damerau_levenshtein_distance?  I haven't compared.

import sys
from lcs import strdiff, lenLCS
    
OR_G = {}

def value(expl, target, r, tau=0.7, eprev = lambda s: 1, gamma = lambda s: 1):
    """ Calculate explanitory coverage for target observations.

    Given a vector of explanations and target observations,
    generate a "coverage" vector, which is the sum over all
    explanations of the explanitory weight for each observation.  Also
    returns the ratio of observations which exceed a coverage
    threshold.

    @param expl vector of explanations
    @param target vector of targeted observations
    @param r function that maps observations and explanations to weights
    @param tau coverage threshold (how much of a factor does an observation have to be to consider it?)
    @param eprev function that maps an explanation to a weight multiplier
    @param gamma function that generates a multiplier for the coverage ratio from the explanations
    """
    # coverage[i] gets the sum (across explanations in expl) of weights for target[i]
    coverage = map(lambda o: sum(map(lambda e: r(o,e)*eprev(e), expl)), target)
    # covered gets the number of targets which exceed the coverage threshold
    covered = len(filter(lambda v : v >= tau, coverage))
    # fraction of targets covered
    cratio = covered/float(len(target))
    return (cratio*gamma(expl), coverage)

def ddtor(dd):
    """ Generate a function to map observations and explanations to weights.

    Given a dictionary, dd, such that dd[explanation][observation] is a weight (if defined),
    generate a function that returns that weight (or zero if undefined).

    @param dd dictionary of explanitory weights
    """
    return lambda o,e: dd[e][o] if dd[e].has_key(o) else 0

def greedy(target, E, r,
           taus=[0.7, 0.5, 0.3, 0.05],
           eprev = lambda s: 1, gamma = lambda s: 1):
    """ Generate a list of minimal explanations which provide the best coverage of the observations using a greedy method.

    @param target list of target observations
    @param E list of possible (expected?) explanations
    @param r function that maps observations and explanations to weights
    @param tau list of coverage thresholds (how much of a factor does an observation have to be to consider it?)
    @param eprev function that maps an explanation to a weight multiplier
    @param gamma function that generates a multiplier for the coverage ratio from the explanations
    """

    avail = set(E) # still available to try
    # force any explanations that are also targets
    sol = list(set(E) & set(target))       # solution
    cval = 0
    # Find the largest coverage threshold exceeded if we take all initial explanations (those that are also targets) into account.
    for tau in taus:
        cval = value(sol, target, r, tau, eprev, gamma)[0]
        if cval > 0:
            break

    while avail:
        # Starting with the explanations which are also targets, one by one add the additional explanations in 
        # the given list.  Each time, add the explanation which creates the biggest improvement in coverage.
        beste = None
        bestv = cval
        for tau in taus:
            for e in avail:
                #print('trying ' + str(e) + ' at ' + str(tau))
                tmpv = value(sol + [e], target, r, tau, eprev, gamma)[0]
                if tmpv > bestv:
                    bestv = tmpv
                    beste = e
            if beste != None: # improvement
                #print('exiting tau' + str(tau) + ' best e ' + str(beste))
                break
        # If we come to a point where adding another explanation cannot improve coverage, return.
        if beste == None: # no improvement
            return (sol, cval, value(sol, target, r, 0.9, eprev, gamma)[1])
        cval = bestv
        sol.append(beste)
        avail.remove(beste)
    return (sol, cval, value(sol, target, r, 0.9, eprev, gamma)[1])
    
    
def setDictionaries(newest_OR_G):
    """
    Update the OR_G dictionary this file uses
    """
    global OR_G
    OR_G = newest_OR_G
    
def runDiagnosis(Findings=[]):
    
    testG = OR_G 
    O = reduce(lambda x,y : x | set(testG[y].keys()), testG.keys(), set())
    E = set(testG.keys())
    OE = list(O | set(testG.keys()))
    #print('Input Symptoms, end with empty line:')
    target = []
    Es = []
    
    # Have a list of findings input by the user define what is given to this algorithm.
    for finding in Findings:
        word = finding.lstrip().rstrip()
        if len(word) == 0:
            break
        # Find the closest match to the current finding in either explanations or observations in terms of longest common substring.
        (s,o) = max(map(lambda w : (strdiff(word, w), w), OE))
        #print('using ' + str(o) + ' for ' + word + ' (match: ' + str(s) + ')')
        if o in E:
            Es.append(o) 
        target.append(o)

    # target now contains explanations or observations which are closest to the requested findings.  Es contains
    # the subset of those which are explanations
    
    for e in Es:
        missed = set(testG[e].keys()) - set(target)
        if len(missed) > 0:
            #print('for ' + e + ', symptoms not entered:')
            #print('>' + ', '.join(str(t) for t in missed))
            pass
            
    
    #print('Observed :\n  ' + '\n  '.join(str(t) for t in target))
    
    #print('Explained to degree:')
    
    # Set up the weight mapping function
    rfunc = ddtor(testG)

    # call the greedy algorithm
    solutions, cf, cov = greedy(target, testG.keys(), rfunc)
    
    #print('  ' + str(cov))
    
    solutions_and_values = []
    
    for solution in solutions:
        disease = str(solution)
        list_explained_to_degree_each_finding = [str(a_value) for a_value in value([solution], target, rfunc)[1]]
        
        solutions_and_values += [[disease] + list_explained_to_degree_each_finding]
        
        
    #print solutions_and_values

    return solutions_and_values
    #printGraphics(target, testG, sol)   
    
def printGraphics(target, testG, sol):
    from random import random, sample, randint
    from collections import defaultdict
    from pprint import pprint
    try:
        from Gplt import mpG
        print('plot explanation? (y/[n])')
        if sys.stdin.readline().lstrip().rstrip() == 'y':
            mpG(
                dict(
                    map(lambda (e,_):
                        (e,
                         dict((s,v) for (s,v) in testG[e].items()
                              if s in target)),
                        filter(lambda (e, s) : e in sol, testG.items())
                        )
                    )
                )
    except:
        print('Sorry, plotting failed. Are needed packages installed?')
        pass
    
    
if __name__ == '__main__':
    
    global OR_G
    OR_G = eval(open('OR_G.txt').read())
    runDiagnosis(['fever', 'cough'])    

    
