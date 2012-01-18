'''
Created on May 3, 2011

@author: David

This parser is specifically for the doknosis application
'''

import csv
from constants import country_dict

CSV_FILE = "MzbIDListwithSymptoms.csv"

def create_R_dictionary(diseaseList):
    R = {}
    for disease in diseaseList:
        R[disease.name] = disease.findingsList()
    return R

def create_OR_dictionary(diseaseList):
    OR_G = {}
    for disease in diseaseList:
        OR_G[disease.name] = disease.OR_G_dict()
    return OR_G

def create_prevalence_G_dictionary(diseaseList):
    prevalence_G = {}
    for disease in diseaseList:
        prevalence_G[disease.name] = disease.prevalence_G_dict()
    return prevalence_G
    
def createDiseaseList(originalDiseaseCSVTable):
    """
    Returns a list of diseases which eventually can be turned into a database
    """
    table = originalDiseaseCSVTable

    findings = set()
    diseaseList = []
        
    for row in table:
        numCols = len(row)
        curDisease = Disease(row[1])
        #iterate through all findings
        for col in range(2, numCols):
            finding = curDisease.addFinding(row[col])
            
            if finding is not None:
                findings.add( finding[0] )
        
        diseaseList.append(curDisease)
    return ( findings, diseaseList )
    
class Disease():
    def __init__(self, name):
        #self.randCode = code
        self.name = name 
        self.findings = [] #right now keep it simple, and make all findings go in this list
    
    def addFinding(self, finding):
        """
        Need to parse through finding has the format name [val], where [] is optional
        """
        finding = str(finding)
        if len( finding ) == 0:
            return
            
        bracket1 = finding.find("[")
       
        item = ['hi', 0]
         
        if(bracket1 == -1): #Not found
            findingName = finding.strip()
            findingWeight = 1
            item[0] = findingName
            item[1] = findingWeight
        else:
            bracket2 = finding.find("]")
            findingName = finding[0:bracket1].strip()
            findingWeightLetter = finding[bracket1+1:bracket2].strip() 
            item[0] = findingName
            item[1] = self.weightMap(findingWeightLetter)
            if(item[1] == 1):
                pass
        
        self.findings.append(item)
        return item
        
    def findingsList(self):
        """
            Returns the list of names of the findings, without the weights
        """
        ret = []
        for finding in self.findings:
            ret.append(finding[0])
            
        return ret
    
    def OR_G_dict(self):
        """
            Returns the dictionary for the OR_G in the format of the OR_G
        """
        ret = {}
        for finding in self.findings:
            ret[finding[0]] = finding[1]
        
        return ret
    
    def prevalence_G_dict(self):
        """
            Returns the dictionary for the prevalence_G in the format for prevalence_G
        """
        ret = {}
        for finding in self.findings:
            if(self.isCountry(finding[0])):
                ret[finding[0]] = finding[1]
        return ret
    
    def isCountry(self, findingName):
        """
        Returns true or false whether this finding name is a country or not
        """
        countryList = country_dict.keys()
        #countryList = ['mozambique', 'africa', 'asia']
        
        return (findingName in countryList)
    
    def weightMap(self, letter):
        d = {'a': 1.0, 'c': 0.75, 'p': 0.5, 'i': 0.25, 'r': 0.1, 'n' : 0, 'd': 0.95, 'e': 0.65, 'f': 0.5, 'g': 0.25, 'h': 0.1}
        #d = {'a': 100, 'c': 10, 'p': 1, 'i': 0.1, 'r': 0.001, 'n' : 0, 'd': 100, 'e': 10, 'f': 1, 'g': 0.1, 'h': 0.001}
        if(d.has_key(letter)):
            return d[letter]
        else:
            return 0.5
    
    def __repr__( self ):
        return '<Disease ( %s, %s )>' % ( self.name, self.findings )
    
def createCSVTable(csv_file=CSV_FILE):
    """
    Returns a 2D array (table) from the CSV file
    
    csv_table[0] is a list of all the key values that I want
    csv_table[1] ... csv_table[n] is a list for each of the bacteria 
    """
    filestring = open(csv_file, "rb")
    
    return filestring_to_table(filestring)


def filestring_to_table(filestring):
    """
    Turns a string read from a csv file into a 2D array
    """    
    rows = csv.reader(filestring) 
    csv_table = []
    
    for row_line in rows:
    
        #Each row is a list
        row_list = []
        for column_item in row_line:
            #if the item is non-empty
            #if(len(column_item.replace(' ', '')) != 0):
            row_list.append(column_item)
        csv_table.append(row_list)
         
    return csv_table
    
    
def csvTest():
    tbl = createCSVTable()
    diseaseList = createDiseaseList(tbl)
    pass
    
if __name__ == "__main__":
    csvTest()
