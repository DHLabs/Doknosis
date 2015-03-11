import csv

from server.db import Explanation, FindingWeight
from server.constants import EXPLANATION_TYPE_IDENTIFIERS


def _parse_findings( raw_finding_strings, errors, line_no ):
    finding_weights = []

    finding_parse_error = False

    # Parse the findings
    for finding_string in raw_finding_strings:
        print('parsing finding {}'.format(finding_string))
        finding_components=finding_string.split(':')
        if len(finding_components) < 2:
            # Ignore any finding which does not have an associated prevalence.  Assume these are just comments, so we will not return an error.
            continue
        else:
            name = ':'.join(finding_components[:-1]).lower()
            try:
                weight = float(finding_components[-1])
                if weight > 1 or weight < 0:
                    # If a finding has an invalid prevalence number, spit out a warning and ignore it.
                    errors.append('Finding \"{}\", prevalence weight ({}) not in [0,1].'.format(name,weight))
                    finding_parse_error = True
                    break

            except ValueError:
                # If prevalence value is not a probability, skip this finding!
                errors.append('Finding \"{}\", prevalence weight ({}) not a number.'.format(name,finding_components[-1]))
                finding_parse_error = True
                break

        finding_weights.append( FindingWeight( name=name, weight=weight ) )


    return ( finding_parse_error, finding_weights )


def parse_csv( file ):
    errors = []

    reader = csv.reader( open( file, 'rb' ) )

    print "parse_csv -- loading file"

    line_no = 0
    for csv_entry in reader:
        line_no += 1

        print('Loading entry {}'.format(csv_entry))

        if len( csv_entry ) < 3:
            errors.append( 'Line %d: Must have an ID ( can be blank ), name, and type identifier (e.g., \"Disease\")' % ( line_no ) )
            continue

        csv_entry_id          = csv_entry[0].strip()
        csv_entry_name        = csv_entry[1].strip().capitalize()
        csv_entry_typeid      = csv_entry[2].strip().capitalize()

        if len( csv_entry_name ) == 0:
            errors.append( 'Line %d: Name must NOT be empty!' % ( line_no ) )
            continue

        if csv_entry_typeid not in EXPLANATION_TYPE_IDENTIFIERS:
            errors.append( 'Line {}: Invalid type identifier \"{}\", must be one of {}'.format( line_no, csv_entry_typeid, EXPLANATION_TYPE_IDENTIFIERS) )
            continue


        if len( csv_entry ) > 3:
            csv_entry_findings = csv_entry[2:]
        else:
            csv_entry_findings = [':0.5']

        has_id = len( csv_entry_id ) != 0

        if has_id:
            print('Has ID {}'.format(csv_entry_id))
            # Attempt to find this key in the database from id
            mongo_entry = None
            try:
                mongo_entry = Explanation.query.filter(Explanation.mongo_id == csv_entry_id).first()
            except Exception:
                errors.append( 'Line %d: Invalid Explanation ID' % ( line_no ) )
                continue

            # If we have an invalid entry id, log the error and continue
            if mongo_entry == None:
                errors.append( 'Line %d: Failed to find ID %s in the database.  New entries should have blank ID field in csv file!' % ( line_no, csv_entry_id ) )
                continue

            # Parse the findings
            finding_parse_error, finding_weights = _parse_findings( csv_entry_findings,
                                                             errors,
                                                             line_no )

            # Only save finding data if there are no errors parsing the
            # findings
            if not finding_parse_error and len( errors ) == 0:
                mongo_entry.findings = finding_weights
                mongo_entry.save()
        else:
            print('Parsing entry with no id')
            # Parse the findings
            finding_parse_error, finding_weights = _parse_findings( csv_entry_findings,
                                                             errors,
                                                             line_no )

            # Only save the new entry if there are no errors parsing the
            # findings
            if not finding_parse_error and len( errors ) == 0:
                mongo_entry = Explanation( name=csv_entry_name )
                mongo_entry.findings = finding_weights
                mongo_entry.save()

    return errors
