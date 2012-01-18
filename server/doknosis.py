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

import sys
from lcs import strdiff, lenLCS
    
OR_G = {}

def value(expl, target, r, tau=0.7, eprev = lambda s: 1, gamma = lambda s: 1):
    coverage = map(lambda o: sum(map(lambda e: r(o,e)*eprev(e), expl)), target)
    covered = len(filter(lambda v : v >= tau, coverage))
    cratio = covered/float(len(target))
    return (cratio*gamma(expl), coverage)

def ddtor(dd):
    return lambda o,e: dd[e][o] if dd[e].has_key(o) else 0

def greedy(target, E, r,
           taus=[0.7, 0.5, 0.3, 0.05],
           eprev = lambda s: 1, gamma = lambda s: 1):
    avail = set(E) # still available to try
    # force any explanations that are also targets
    sol = list(set(E) & set(target))       # solution
    cval = 0
    for tau in taus:
        cval = value(sol, target, r, tau, eprev, gamma)[0]
        if cval > 0:
            break
    while avail:
        # try adding all available explanations
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
    
    #Have a list of findings inputted by the user define what is given to this algorithm
    for finding in Findings:
        word = finding.lstrip().rstrip()
        if len(word) == 0:
            break
        (s,o) = max(map(lambda w : (strdiff(word, w), w), OE))
        #print('using ' + str(o) + ' for ' + word + ' (match: ' + str(s) + ')')
        if o in E:
            Es.append(o) 
        target.append(o)
    
    for e in Es:
        missed = set(testG[e].keys()) - set(target)
        if len(missed) > 0:
            #print('for ' + e + ', symptoms not entered:')
            #print('>' + ', '.join(str(t) for t in missed))
            pass
            
    
    #print('Observed :\n  ' + '\n  '.join(str(t) for t in target))
    
    #print('Explained to degree:')
    
    rfunc = ddtor(testG)
    
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

    
