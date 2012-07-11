'''
    clean_data.py
    Author: Andrew Huynh

    Go through the entire list of diseases and findings cleaning up the names.
    - For diseases we trim and capitalize the disease name.
    - For findings we trim and lower the finding name.
'''
from pymongo import Connection


def main():
    connection = Connection()
    db = connection.doknosis

    findings = set()

    # Go through each disease and strip/capitalize the disease name
    print 'Trimming Disease/Finding Names...'
    for disease in db.Disease.find():
        disease[ 'name' ] = disease[ 'name' ].strip().capitalize()

        # Go through each finding ( for each disease ), strip/lower the finding
        # name.
        #
        # We also create a set from the names to be the final findings list
        # later on.
        for find in disease[ 'findings' ]:
            find[ 'name' ] = find[ 'name' ].strip().lower()
            findings.add( find[ 'name' ] )

        db.Disease.update( { '_id': disease['_id'] }, disease )

    # Create maps for each finding to be inserted into the database
    print 'Rebuiling Findings List...'
    updated_findings = []
    for find in findings:
        updated_findings.append( { 'name': find } )

    # Remove all the old findings and all the updated findings
    print '%d findings found' % ( len( findings ) )
    db.Finding.remove()
    db.Finding.insert( updated_findings )

    print 'Done!'

if __name__ == '__main__':
    main()
