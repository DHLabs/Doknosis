# -*-Python-*-
################################################################################
#
# File:         lcs.py
# RCS:          $Header: $
# Description:  strdiff by LCS
# Author:       Staal Vinterbo
# Created:      Wed Jun  8 23:39:12 2011
# Modified:     Wed Jun  8 23:39:25 2011 (Staal Vinterbo) staal@ball
# Language:     Python
# Package:      N/A
# Status:       Experimental
#
# (c) Copyright 2011, Staal Vinterbo, all rights reserved.
#
################################################################################

def LCS(X, Y):
    m = len(X)
    n = len(Y)
    # An (m+1) times (n+1) matrix
    C = [[0] * (n+1) for i in range(m+1)]
    for i in range(1, m+1):
        for j in range(1, n+1):
            if X[i-1] == Y[j-1]: 
                C[i][j] = C[i-1][j-1] + 1
            else:
                C[i][j] = max(C[i][j-1], C[i-1][j])
    return C

def backTrack(C, X, Y, i, j):
    if i == 0 or j == 0:
        return []
    elif X[i-1] == Y[j-1]:
        return backTrack(C, X, Y, i-1, j-1) + [(i-1,j-1)]
    else:
        if C[i][j-1] > C[i-1][j]:
            return backTrack(C, X, Y, i, j-1)
        else:
            return backTrack(C, X, Y, i-1, j)

def compLCS(X,Y):
    m = len(X)
    n = len(Y)
    C = LCS(X, Y)
    return backTrack(C, X, Y, m, n)

def lenLCS(X,Y):
    return len(compLCS(X,Y))

def strdiff(a, b):
    return 2*len(compLCS(a,b))/float(len(a)+len(b))
