import csv

from server.db import Explanation, FindingWeight, Finding
from server.constants import EXPLANATION_TYPE_IDENTIFIERS


def _parse_findings( raw_finding_strings, errors, line_no ):
    ''' Parse a list of findings from csv input.

    Make sure that the formats are all correct, translate into FindingWeight objects for database.
    
    @param raw_finding_strings List of entries in the csv file, each of which has the form name_string:weight, with weight a number in [0,1].
    @param errors List of errors thus far (if we get an error, we append to list and return).
    @param line_no Line in the csv file, not currently used.

    @returns List of FindingWeight objects for database.
    '''
    finding_weights = []

    finding_parse_error = False

    # Parse the findings
    for finding_string in raw_finding_strings:
        finding_components=finding_string.split(':')
        if len(finding_components) < 2:
            # Ignore any finding which does not have an associated prevalence.  Assume these are just comments, so we will not return an error.
            continue
        else:
            finding_name = ':'.join(finding_components[:-1]).lower()
            try:
                weight = float(finding_components[-1])
                if weight > 1 or weight < 0:
                    # If a finding has an invalid prevalence number, spit out a warning and ignore it.
                    errors.append('Finding \"{}\", prevalence weight ({}) not in [0,1].'.format(finding_name,weight))
                    finding_parse_error = True
                    break

            except ValueError:
                # If prevalence value is not a probability, skip this finding!
                errors.append('Finding \"{}\", prevalence weight ({}) not a number.'.format(finding_name,finding_components[-1]))
                finding_parse_error = True
                break

        finding_weights.append( FindingWeight( name=finding_name, weight=weight ) )

    return ( finding_parse_error, finding_weights )


def parse_csv( file ):
    ''' Parse a csv file for weighted Explanation/Observation mappings.

    The input file has rows which correspond to explanatory variables.  Each row has the form [id,name,type,[findings]], where
    id is either blank or the database id associated with existing entry, name is a string describing the explanatory variable,
    and [findings] is a list of zero or more findings with the form [name:weight].  Some notes about the flow:
    1) In the case of most parsing errors, the row is skipped and message is appended to the return list, but parsing moves on.
    2) If the id field is empty, an attempt is made to match the explanation name and type to a variable in the database.  If
       a match is found then that element is updated, otherwise a new entry is generated.  If name matches but type does not, 
       an error is flagged and the row is skipped.
    3) If the id field is not empty, id is matched to id's in the database.  If not found, ignore id field and treat as blank.
       If found, match name and type to entry in database.  If all match, update entry.  If no match, flag error and skip row.

    @param file String path to the input file.

    @returns List of parse errors encountered along the way.
    '''
    errors = []

    reader = csv.reader( open( file, 'rb' ) )

    line_no = 0
    for csv_entry in reader:
        line_no += 1

        # First thing is to make sure that the line contains only ascii characters.  Otherwise an exception is
        # thrown by database down the line and I'd rather catch it here.
        ascii_failure = False
        for field in csv_entry:
            try:
                field.decode('ascii')
            except UnicodeDecodeError:
                rep_field = field.decode('ascii','replace').encode('ascii','replace')
                errors.append('Row {}: Non-ascii characters in field \"{}\".  Skipping this row!'.format(line_no,rep_field))
                ascii_failure = True
        if ascii_failure:
            continue

        if len( csv_entry ) < 3:
            errors.append( 'Row %d: Must have an ID ( can be blank ), name, and type identifier (e.g., \"Disease\"). Skipping this row!' % ( line_no ) )
            continue

        csv_entry_id          = csv_entry[0].strip()
        csv_entry_name        = csv_entry[1].strip().capitalize()
        csv_entry_typeid      = csv_entry[2].strip().capitalize()

        if len( csv_entry_name ) == 0:
            errors.append( 'Row %d: Name must NOT be empty!' % ( line_no ) )
            continue

        if csv_entry_typeid not in EXPLANATION_TYPE_IDENTIFIERS:
            errors.append( 'Row {}: Invalid type identifier \"{}\", must be one of {}.  Skipping this row!'.format( line_no, csv_entry_typeid, EXPLANATION_TYPE_IDENTIFIERS) )
            continue


        if len( csv_entry ) > 3:
            csv_entry_findings = csv_entry[2:]
        else:
            csv_entry_findings = [':0.5']

        # Before messing with the database to figure out if we are creating or updating, we first parse the findings because if
        # that fails then we are going to skip this entry anyway.
        finding_parse_error, finding_weights = _parse_findings(csv_entry_findings, errors, line_no)
        if finding_parse_error:
            continue

        db_entry = None

        # Check to see if an id was specified.
        if len( csv_entry_id ) != 0:
            match_error, db_entry = match_db_entry(compare_id=csv_entry_id,compare_name=csv_entry_name,compare_type=csv_entry_typeid)
            # If there was a database error looking for the id, let's just treat it as not found, moving on to search by name.
            if match_error and db_entry is not None:
                errors.append('Row {}: ID {} in database is \"{}\" ({}), but csv has \"{}\" ({})!  Skipping this row!'.format(line_no, csv_entry_id,db_entry.name,db_entry.type_identifier,csv_entry_name,csv_entry_typeid))
                continue


        # If we did not find our entry by ID, we next check to see if it is in there by name.
        if db_entry is None:
            match_error, db_entry = match_db_entry(compare_name=csv_entry_name,compare_type=csv_entry_typeid)
            if match_error:
                if db_entry is None:
                    errors.append('Row {}: Database error while looking for explanatory variable with name {}.  Skipping this row to avoid redundant entries!'.format(line_no, csv_entry_name))
                else:
                    errors.append('Row {}: Database entry \"{}\" has type {}, but type is {} in csv file!  Skipping this row!'.format(line_no,csv_entry_name,db_entry.type_identifier,csv_entry_typeid))
                continue


        # Once we get here, we either have a matching db_entry, or we have to create one.
        if db_entry is None:
            db_entry = Explanation(name=csv_entry_name, type_identifier=csv_entry_typeid)
            if db_entry is None:
                errors.append('Row {}: Failed to create database entry for explanatory variable {} with type {}!  Skipping this row!'.format(line_no,csv_entry_name,csv_entry_typeid))
                continue
        
        db_entry.findings = finding_weights
        db_entry.save()
        add_findings(finding_weights)

    return errors

def match_db_entry(compare_name,compare_type,compare_id=None):
    ''' Query the database for an entry with the given characteristics.

    Query uses only id or name (if id is None), then tests the value of name and type against the result.

    @param compare_id If specified, we use this for the query.
    @param compare_name If compare_id not specified, use this for query.  Test resulting db_entry.name against this.
    @param compare_type Test resulting db_entry.type_identifier against this.

    @returns match_error(boolean),db_entry(what we found).  Note on return conditions:
            match_error    db_entry     description
            True           None         Database error in query
            False          None         Query returned None
            True           not None     Mismatch between input and database entry
            False          not None     Found a matching entry
    '''

    db_entry = None
    if compare_id is not None:
        # Attempt to find this key in the database by id
        try:
            # TODO Should probably abstract "mongo" out of this at some point!
            db_entry = Explanation.query.filter(Explanation.mongo_id == compare_id).first()
        except Exception:
            return True,None
    else:
        # Attempt to find this key in the database by name
        try:
            db_entry = Explanation.query.filter(Explanation.name == compare_name).first()
        except Exception:
            return True,None

    if db_entry is not None:
        if db_entry.name != compare_name or db_entry.type_identifier != compare_type:
            return True,db_entry

    return False,db_entry


def add_findings(finding_weights):
    # After we add an explanation, make sure the finding strings are in the database
    for finding_weight in finding_weights:
        if Finding.query.filter( {'name': finding_weight.name} ).count() == 0:
            finding = Finding(name=finding_weight.name)
            finding.save()
