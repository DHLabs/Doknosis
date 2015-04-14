# Legal type identifiers for explanations
EXPLANATION_TYPE_IDENTIFIERS = ['Drug','Disease','Sporadic Disease','Infectious Disease']
# Map categories (for UI) to a list of possible type_identifiers
EXPLANATION_TYPE_CATEGORIES = {'Drug':['Drug'],
                               'All Disease':['Sporadic Disease','Infectious Disease','Disease'],
                               'Sporadic Disease':['Sporadic Disease'],
                               'Infectious Disease':['Infectious Disease'],
                               'All':EXPLANATION_TYPE_IDENTIFIERS}

# All geographic regions used
EXPLANATION_REGIONS = ['North America','South America','Central America','Carribean','Europe',
                       'Middle East','East Asia','South Asia','Australia','Africa']

# Algorithm choice constants
DIAGNOSIS_ALGORITHMS = ['Hybrid 1','Hybrid 2','Naive Bayes']
DIAGNOSIS_ALGORITHM_DEFAULT = 'Hybrid 1'

