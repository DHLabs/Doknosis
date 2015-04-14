import csv

from server.constants import EXPLANATION_TYPE_IDENTIFIERS, EXPLANATION_REGIONS

def _parse_findings( raw_finding_strings, error_prefix, errors ):
    ''' Parse a list of findings from csv input.

    Make sure that the formats are all correct, translate into FindingWeight objects for database.
    
    @param raw_finding_strings List of entries in the csv file, each of which has the form name_string:weight, with weight a number in [0,1].
    @param error_prefix Name of row so we can locate errors.
    @param errors List of errors thus far (if we get an error, we append to list and return).

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
                    errors.append(error_prefix+'Finding \"{}\", prevalence weight ({}) not in [0,1].'.format(finding_name,weight))
                    finding_parse_error = True
                    break

            except ValueError:
                # If prevalence value is not a probability, skip this finding!
                errors.append(error_prefix+'Finding \"{}\", prevalence weight ({}) not a number.'.format(finding_name,finding_components[-1]))
                finding_parse_error = True
                break

        finding_weights.append( {'name':finding_name, 'weight':weight} )

    return ( finding_parse_error, finding_weights )

def ascii_check(string_list, error_prefix, errors):
    ''' Make sure that the line contains only ascii characters.  

    Any ascii decoding errors will be appended to the list of errors.
    @returns True if any decode errors encountered.
    '''
    # First thing is to 
    # thrown by database down the line and I'd rather catch it here.
    ascii_failure = False
    for field in string_list:
        if field is None:
            continue
        try:
            field.decode('ascii')
        except UnicodeDecodeError:
            rep_field = field.decode('ascii','replace').encode('ascii','replace')
            errors.append(error_prefix+'Non-ascii characters in field \"{}\".  Skipping this row!'.format(rep_field))
            ascii_failure = True

    return ascii_failure

def parse_prevalence_row( this_row, error_prefix, errors ):
    if ascii_check(this_row,error_prefix,errors):
        return None

    if len( this_row ) < 3:
        errors.append(error_prefix+'Must have an ID ( can be blank ), name, and type identifier (e.g., \"Disease\"). Skipping this row!')
        return None

    this_row_id          = this_row[0].strip()
    this_row_name        = this_row[1].strip().capitalize()
    this_row_typeid      = this_row[2].strip().capitalize()

    if len( this_row_name ) == 0:
        errors.append(error_prefix+'Name must NOT be empty!')
        return None

    if this_row_typeid not in EXPLANATION_TYPE_IDENTIFIERS:
        errors.append(error_prefix+'Invalid type identifier \"{}\", must be one of {}.  Skipping this row!'.format( this_row_typeid, EXPLANATION_TYPE_IDENTIFIERS))
        return None


    if len( this_row ) > 3:
        this_row_findings = this_row[2:]
    else:
        this_row_findings = [':0.5']

    # Before messing with the database to figure out if we are creating or updating, we first parse the findings because if
    # that fails then we are going to skip this entry anyway.
    finding_parse_error, finding_weights = _parse_findings(this_row_findings, error_prefix, errors)
    if finding_parse_error:
        return None

    return {'name':this_row_name,'type_identifier':this_row_typeid,'findings':finding_weights}



def parse_prevalence_csv( file ):
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

    # Gather operations for bulk updates.  Keep track as a dictionary so that we just overwrite any previous guys with the
    # same name and type.
    update_explanations = {}

    line_no = 0
    for csv_entry in reader:
        line_no += 1
        update_row = parse_prevalence_row(csv_entry,'Row: {} -- '.format(line_no),errors)
        if update_row is not None:
            update_explanations[update_row['name']+update_row['type_identifier']] = update_row

    return errors,update_explanations


def parse_gdata( gd_prev, gd_geo ):
    ''' Parse google sheets document.  Pull out both prevalence weights and geocoding stuff.

    The inputs are in the form of lists of dictionaries.  

    @param gd_prev Dictionary of prevalence weights.  Indexed by explanatory variable name, each row has 'id', 'type', and 'rowname'
    then any number of others which correspond to findings.
    
    @param gd_geo Dictionary of geocode data.  Indexed by explanatory variable name, each row has 'subtype', 'rowname',
    and 'alllocations' (ignored), followed by all elements of EXPLANATION_REGIONS (without spaces and lower case).

    @returns List of parse errors encountered along the way.
    '''
    errors = []

    all_keys = list(set(gd_prev.keys())|set(gd_geo.keys()))
    all_regions_set = set(EXPLANATION_REGIONS)

    # Gather operations for bulk updates.
    update_explanations = {}
    for name in all_keys:
        if name in gd_prev:
            row_dict = gd_prev[name]
            row_list = [row_dict.get('id'),name,row_dict.get('type')]
            [row_list.append(row_dict.get(this_key)) for this_key in row_dict.keys() 
             if this_key not in ['explanatoryvariable','id','type','rowname']]
            # Empty cells in the google sheet come up as None type here, but for csv they read as ''.
            update_row = parse_prevalence_row(map(lambda x: '' if x is None else x,row_list),
                                              'Prevalence data '+row_dict['rowname']+' -- ', errors)
            if update_row is not None:
                update_explanations[name] = update_row

        if name in gd_geo:
            row_dict = gd_geo[name]
            error_prefix = 'Geo data \"'+row_dict['rowname']+'\" -- '
            if ascii_check(row_dict.values(),error_prefix,errors):
                continue

            regions = list(set([ff[:-2] for ff in row_dict.values() if ff[-2:] == ':1']).intersection(all_regions_set))
            if regions is None or len(regions) == 0:
                errors.append(error_prefix+'No acceptable regions? ({} filtered to {} when seeking strings ending in ":1")'
                              .format(row_dict.values(),[ff[:-2] for ff in row_dict.values() if ff[-2:] == ':1']))
                continue
            
            if name not in update_explanations:
                errors.append(error_prefix+'This explanation does not match any in prevalence data!  Skipping!'.format(name))
                continue

            # Prepend subtype to disease.
            update_explanations[name]['type_identifier'] = row_dict['subtype'].capitalize()+' '+update_explanations[name]['type_identifier']
            update_explanations[name]['regions'] = regions

    return errors,update_explanations
