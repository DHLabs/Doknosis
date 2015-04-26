#!/usr/bin/env python
import sys,os,re,time,pickle,itertools
if '../server/helpers' not in sys.path:
    sys.path.append('../server/helpers')
if '.' not in sys.path:
    sys.path.append('.')

from pprint import pprint

from GDataClient import GDataClient,GDError,GDATA_MAIN_DOC,GDATA_WS_PREVALENCE
from BioPortalClient import BioPortalClient,ONTOLOGY_SNOMEDCT,ONTOLOGY_ICD10,ONTOLOGY_LOINC
from BioPortalClient import ONTOLOGY_INFO_NEAR,ONTOLOGY_INFO_PREF,ONTOLOGY_INFO_STYPE,ONTOLOGY_INFO_DISTANCE

# Put google data username and password into the following file (didn't want to check mine in!)
from GoogleDataCredentials import GDATA_USER,GDATA_PASSWORD

# The non-exact matches can get a bit excessive in terms of pages of data.
ONTOLOGY_MATCH_PAGE_LIMIT=3

# Temp for working with old stuff
FILE_RESULTS_EXACT='ontology_ExactMatchResults.p'

FILE_GD_DATA='ontology_PhraseLists.p'
FILE_RESULTS_IN_PROGRESS='ontology_InProgress.p'
FILE_LOG='ontology.log'

# For now use my temporary google sheets doc so I don't mess up the main one.
GDATA_OUTPUT_MAIN_DOC='Doknosis Test'


PHRASE_TYPE_EX='explanations'
PHRASE_TYPE_FI='findings'
PHRASE_TYPES = [PHRASE_TYPE_EX,PHRASE_TYPE_FI]


# Output worksheet names.  True/False refers to the "exact" boolean.
WS_KEY_EXACT='Exact'
WS_KEY_PARTIAL='Partial'
WS_KEY_NONE='No Match'
GDATA_OUTPUT_WORKSHEET={pt:
                            {WS_KEY_EXACT:pt.capitalize()+' - Exact Ontology Matches',
                             WS_KEY_PARTIAL:pt.capitalize()+' - Partial Ontology Matches',
                             WS_KEY_NONE:pt.capitalize()+' - No Ontology Match Found'
                             }
                        for pt in PHRASE_TYPES
                        }


ONTOLOGIES={PHRASE_TYPE_EX:[ONTOLOGY_ICD10,ONTOLOGY_SNOMEDCT,ONTOLOGY_LOINC],
            PHRASE_TYPE_FI:[ONTOLOGY_SNOMEDCT,ONTOLOGY_ICD10,ONTOLOGY_LOINC]}
ONTOLOGY_DISPLAY_KEYS=[ONTOLOGY_INFO_NEAR,ONTOLOGY_INFO_PREF,ONTOLOGY_INFO_STYPE]

SEMANTIC_TYPES_RESTRICT = {pt:None for pt in PHRASE_TYPES}

# No kind of exhaustive list at all, but a half-assed attempt at figuring out the ones which
# should come first when deciding between different terms.  A bunch of these are complete guesses
# as to whether we are interested or not.
SEMANTIC_TYPES_SORT = {PHRASE_TYPE_EX:
                           [u'T047', u'T046', u'T200', u'T037', u'T190', u'T048', u'T049', u'T053', 
                            u'T103', u'T167', u'T168', u'T190', u'T195', u'T196', u'T104', 
                            u'T125', u'T126', u'T127', u'T110', u'T111', u'T114', u'T115', 
                            u'T116', u'T118', u'T119', u'T120', u'T121', u'T122', u'T123', 
                            u'T124', u'T129', u'T130', u'T131', u'T197', u'T109', u'T203'],
                       PHRASE_TYPE_FI:
                           [u'T033', u'T184', u'T047', u'T046', u'T037', u'T190', u'T048', u'T049', 
                            u'T054', u'T055', u'T171', u'T056', u'T057', u'T058', u'T053', 
                            u'T090', u'T096', u'T097', u'T098', u'T099', u'T100', u'T101', 
                            u'T102', u'T129', u'T201']}

# For comparison, when I ran an exact search I got the following semantic types.  Not even sure
#  if these are the ones we want, though...
# Semantic Types Found for findings:
# set(['T004', 'T005', 'T007', 'T018', 'T019', 'T020', 'T023', 'T025', 'T026', 'T031', 'T032', 
#      'T033', 'T034', 'T037', 'T040', 'T041', 'T042', 'T043', 'T045', 'T046', 'T047', 'T048', 
#      'T049', 'T054', 'T055', 'T056', 'T058', 'T060', 'T061', 'T067', 'T070', 'T073', 'T074', 
#      'T079', 'T080', 'T081', 'T082', 'T083', 'T091', 'T097', 'T098', 'T100', 'T101', 'T104', 
#      'T109', 'T110', 'T114', 'T116', 'T121', 'T122', 'T123', 'T124', 'T125', 'T129', 'T131', 
#      'T167', 'T168', 'T169', 'T170', 'T184', 'T185', 'T190', 'T191', 'T195', 'T196', 'T201', 
#      'T204'])
# Semantic Types Found for explanations:
# set(['T005', 'T007', 'T019', 'T020', 'T031', 'T033', 'T037', 'T041', 'T046', 'T047', 'T048', 
#      'T061', 'T098', 'T109', 'T110', 'T114', 'T115', 'T116', 'T118', 'T119', 'T120', 'T121', 
#      'T122', 'T123', 'T124', 'T125', 'T127', 'T129', 'T130', 'T131', 'T184', 'T190', 'T191', 
#      'T195', 'T197', 'T201', 'T204'])

MATCH_KEY_LIST='Phrase List'
MATCH_KEY_STATUS='Cur Status'
MATCH_KEY_PUSHED='Pushed'
MATCH_KEY_RESULTS='Results'
MATCH_STATUS_UNMATCHED=0
MATCH_STATUS_EXACT=1
MATCH_STATUS_EXACT_MIS=2
MATCH_STATUS_PARTIAL=3
MATCH_STATUS_PARTIAL_MIS=4


def find_matches(exact_only=False,disable_intermediate_save=False,limit=None,disable_push=False):
    ''' Runs through all findings and explanations in google data sheets and finds ontological mappings.

    Starts with an exact search on each phrase, then try to do partial matches for any phrases that
    were not yet matched.  Keep track of lists of all phrases along with info on whether they have
    been matched or pushed.  On expected exceptions (e.g. socket errors) we store the current data
    to FILE_RESULTS_IN_PROGRESS.  Any time this function is called, it first checks there to see
    if there are partial results to start from.

    @param exact_only Don't go beyond the exact match step.
    @param limit Only do a few iterations.  For testing.
    @param disable_intermediate_save Disable the file write of intermediate results for testing.
    @param disable_push Disable the push of results to google sheets for testing.
    '''

    if os.path.isfile(FILE_RESULTS_IN_PROGRESS):
        _print_log('Continuing from partial results.')
        ont_matches = _load_partial_results()
    else:
        ont_matches = _init_match_dict()
        # Make sure the file is there next time.
        _store_partial_results(ont_matches,disable_intermediate_save)

    _print_cur_status('Initial status',ont_matches)

    _ontology_match_loop(ont_matches,exact_only=exact_only,disable_intermediate_save=disable_intermediate_save,limit=limit)

    _print_cur_status('After match loop',ont_matches)

    if not disable_push:
        _push_results(ont_matches,limit=limit,disable_intermediate_save=disable_intermediate_save)

    _print_cur_status('After pushing results',ont_matches)

    return ont_matches

####################################################################################################
##
## Utilities for handling data structures
##
####################################################################################################

def _init_match_dict():
    ''' Pick up the stuff we need...
    '''
    ont_matches = {}
    if os.path.isfile(FILE_GD_DATA):
        _print_log('Setting up initial data from file {}'.format(FILE_GD_DATA))
        gd_data = _get_gdata_from_file()
    else:
        _print_log('Picking up initial data from google sheets')
        gd_data = _parse_gdata(row_start=row_start,row_num=row_num,suppress_errors=suppress_errors)

    ont_matches[MATCH_KEY_LIST] = gd_data
    ont_matches[MATCH_KEY_STATUS] = {pt:[MATCH_STATUS_UNMATCHED]*len(gd_data[pt]) for pt in PHRASE_TYPES}
    ont_matches[MATCH_KEY_PUSHED] = {pt:[False]*len(gd_data[pt]) for pt in PHRASE_TYPES}
    ont_matches[MATCH_KEY_RESULTS] = {pt:{} for pt in PHRASE_TYPES}
    _update_partials_from_prev_version(ont_matches)

    return ont_matches

def _update_partials_from_prev_version(ont_matches):
    if os.path.isfile(FILE_RESULTS_EXACT):
        _print_log('Picking up partial results from {}'.format(FILE_RESULTS_EXACT))
        fo = open(FILE_RESULTS_EXACT,'r')
        prev_matches = pickle.load(fo)
        fo.close()
        for pt in PHRASE_TYPES:
            for phrase in prev_matches[pt].keys():
                ont_matches[MATCH_KEY_RESULTS][pt][phrase] = prev_matches[pt][phrase]
                idx = ont_matches[MATCH_KEY_LIST][pt].index(phrase)
                if any([len(prev_matches[pt][phrase].get(ont,[]))>0 for ont in ONTOLOGIES[pt]]):
                    ont_matches[MATCH_KEY_STATUS][pt][idx]=MATCH_STATUS_EXACT
                else:
                    ont_matches[MATCH_KEY_STATUS][pt][idx]=MATCH_STATUS_EXACT_MIS
    else:
        _print_log('No prev version partials to update from')


def _status_matched(stat):
    return stat in [MATCH_STATUS_EXACT,MATCH_STATUS_PARTIAL]


####################################################################################################
##
## Utilities for file io
##
####################################################################################################

def _load_partial_results():
    fo = open(FILE_RESULTS_IN_PROGRESS,'r')
    res = pickle.load(fo)
    fo.close()
    return res

def _store_partial_results(res,disable_save):
    if disable_save:
        return
    _print_cur_status('Storing partial results to file',res)
    fo = open(FILE_RESULTS_IN_PROGRESS,"w")
    pickle.dump(res,fo)
    fo.close()

def _get_gdata_from_file():
    fo = open(FILE_GD_DATA,'r')
    gd_data = pickle.load(fo)
    fo.close()
    return gd_data

####################################################################################################
##
## Utilities for output formatting
##
####################################################################################################

def _print_cur_status(msg,ont_matches):
    _print_log(msg+' -- '+'  '.join(['{}: {} ({} untouched, {} matched, {} pushed).'.format(
                    pt.capitalize(),len(ont_matches[MATCH_KEY_LIST][pt]),
                    len([True for st in ont_matches[MATCH_KEY_STATUS][pt] if st == MATCH_STATUS_UNMATCHED]),
                    len([True for st in ont_matches[MATCH_KEY_STATUS][pt] if _status_matched(st)]),
                    len([True for st in ont_matches[MATCH_KEY_PUSHED][pt] if st]))
                                     for pt in PHRASE_TYPES]))

def _print_iters(msg,cur):
    if cur < 10:
        _print_log(msg)
    elif cur < 100 and cur % 10 == 0:
        _print_log(msg)
    elif cur < 1000 and cur % 100 == 0:
        _print_log(msg)
    elif cur % 500 == 0:
        _print_log(msg)

def _print_log(msg):
    global fh_log
    print msg
    if fh_log is not None:
        fh_log.write(msg+'\n')

def _pprint_log(obj):
    global fh_log
    pprint(obj)
    if fh_log is not None:
        pprint(obj,fh_log)


####################################################################################################
##
## Utilities below are for pulling data from and pushing data to google sheets
##
####################################################################################################

def _parse_findings( raw_finding_strings, error_prefix, errors ):
    ''' Parse a list of findings from csv input.

    Make sure that the formats are all correct, return just the names.
    
    @param raw_finding_strings List of entries in the csv file, each of which has the form name_string:weight, with weight a number in [0,1].
    @param error_prefix Name of row so we can locate errors.
    @param errors List of errors thus far (if we get an error, we append to list and return).

    @returns List of Finding names.
    '''
    finding_names = []

    finding_parse_error = False

    # Parse the findings
    for finding_string in raw_finding_strings:
        if finding_string is None:
            continue
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

        finding_names.append( finding_name )

    return ( finding_parse_error, finding_names )

def _parse_gdata(row_start=None,row_num=None,suppress_errors=True):
    ''' Parse google sheets document.  Grab findings and explanations from prevalence data.
    
    @returns dictionary with keys 'errors',PHRASE_TYPE_FI,PHRASE_TYPE_EX, each a list of strings.
    '''

    gds = GDataClient(GDATA_USER,GDATA_PASSWORD,GDATA_MAIN_DOC,GDATA_WS_PREVALENCE)
    gd_prev,err = gds.read_to_dict('explanatoryvariable',row_start=row_start,row_num=row_num)
    if err is not None and not suppress_errors:
        _print_log(err)
        return

    errors = []

    # Gather all findings.
    findings = set()
    for exp_name in gd_prev.keys():
        row_dict = gd_prev[exp_name]
        error_prefix = 'Prevalence data '+row_dict['rowname']+' -- '
        cur_find = [row_dict[this_key] for this_key in row_dict.keys()
                    if this_key not in ['explanatoryvariable','id','type','rowname']]
        finding_parse_error, finding_names = _parse_findings(cur_find, error_prefix, errors)
        if not finding_parse_error:
            findings |= set(filter(lambda fi:fi is not None and len(fi) > 0,finding_names))

    return {'errors':errors,PHRASE_TYPE_FI:list(findings),
            PHRASE_TYPE_EX:filter(lambda ex:ex is not None and len(ex) > 0,set(gd_prev.keys()))}


def _push_results(ont_matches,limit=None,disable_intermediate_save=False):
    ''' Push the output to google sheets.
    '''

    gds = GDataClient(GDATA_USER,GDATA_PASSWORD,GDATA_OUTPUT_MAIN_DOC)

    status_by_key = {WS_KEY_EXACT:[MATCH_STATUS_EXACT],
                     WS_KEY_PARTIAL:[MATCH_STATUS_PARTIAL],
                     WS_KEY_NONE:[MATCH_STATUS_EXACT_MIS,MATCH_STATUS_PARTIAL_MIS]}

    for phrase_type in PHRASE_TYPES:

        for ws_key in [WS_KEY_EXACT,WS_KEY_PARTIAL,WS_KEY_NONE]:
            ws_name = GDATA_OUTPUT_WORKSHEET[phrase_type][ws_key]
            phrase_list = [phrase for phrase,status,pushed in 
                           zip(ont_matches[MATCH_KEY_LIST][phrase_type],
                               ont_matches[MATCH_KEY_STATUS][phrase_type],
                               ont_matches[MATCH_KEY_PUSHED][phrase_type])
                           if not pushed and status in status_by_key[ws_key]]
            if limit is not None:
                phrase_list = phrase_list[0:min(limit,len(phrase_list))]
            try:
                _push_results_one_page(gds,ont_matches[MATCH_KEY_RESULTS][phrase_type],phrase_list,ws_name,ONTOLOGIES[phrase_type])
            except Exception as exc:
                if disable_intermediate_save:
                    _print_log('Exception, but NOT dumping current results!')
                else:
                    _print_log('Dumping current results on exception!')
                    _store_partial_results(ont_matches,disable_intermediate_save)
                raise exc

            # Next, change the status of those guys to uploaded
            for phrase_idx,phrase in enumerate(ont_matches[MATCH_KEY_LIST][phrase_type]):
                if phrase in phrase_list:
                    ont_matches[MATCH_KEY_PUSHED][phrase_type][phrase_idx]=True

            # Store the updates so we don't have to rewrite those guys.
            _store_partial_results(ont_matches,disable_intermediate_save)


def _gdata_col_hdr(ont,info_type,askey=False):
    hdr_string = info_type+' - '+ont
    if askey:
        # gdata columns are keyed by just the lower case alphanumeric characters plus "-" and "." found in the header title.
        return ''.join(re.findall('[a-z\-0-9\.]+',hdr_string.lower()))
    else:
        return hdr_string


def _push_results_one_page(gds,matches_by_type,phrase_list,ws_name,ontologies):
    ''' grab the results and stick them into a google spreadsheet.

    This is pretty convoluted and probably very slow, but I'm a little bogged down with premature optimization right
    now and just want to get something to work!

    @param gds A connected GDataClient object for output storage
    @param matches_by_type A dictionary of ontology matches whose keys are the search terms.
    @param phrase_list A list of all phrases (not ordered) to be pushed.
    @param ws_name Name of worksheet to push these phrases to.
    '''

    # Funky hierarchical sort:
    # 1) which ontology is the first (in ONTOLOGIES) to contain a match? (i.e., put all those matching
    #    in SNOMEDCT first, then the ones which don't, but do match in ICD10... finish with not matched)
    #    -> This is done by making a list of booleans for whether each ontology was a match, then returning
    #       the index in the sort function.
    # 2) was the matched string the preferred Label or synonym?
    # 3) what was the match distance?
    #

    # I tried to do this a smart way with a single key sort, but kept running into problems with missing keys.  So here we first pluck out the
    # indices of ontology to sort on the other criteria for sublist.
    phrases_left = phrase_list
    sorted_phrases = []
    for ont in ontologies:
        cur_list = [phrase for phrase in phrases_left if len(matches_by_type[phrase][ont]) != 0]
        phrases_left = list(set(phrases_left)-set(cur_list))
        sorted_phrases.extend(sorted(cur_list,
                                     key=lambda phrase:(matches_by_type[phrase][ont][ONTOLOGY_INFO_NEAR] != 
                                                        matches_by_type[phrase][ont][ONTOLOGY_INFO_PREF],
                                   matches_by_type[phrase][ont][ONTOLOGY_INFO_DISTANCE],
                                   matches_by_type[phrase][ont][ONTOLOGY_INFO_PREF])))

    sorted_phrases.extend(sorted(phrases_left))

    gdata_hdrs = {ont:{info_type:_gdata_col_hdr(ont,info_type,True) 
                       for info_type in ONTOLOGY_DISPLAY_KEYS} for ont in ontologies}


    # If we add a new worksheet, only add a single row for headers.  New rows will be inserted as needed.
    if gds.add_worksheet(ws_name,1,len(ontologies)*3+1,False):
        # If we are creating a new file, generate all columns as if we are using all ontologies
        gds.set_headers(['Name'] + [_gdata_col_hdr(ont,info_type) 
                                    for ont in ontologies for info_type in ONTOLOGY_DISPLAY_KEYS])
    else:
        print 'WARNING!!!  We do not really handle merging existing data with new data very well yet.'
        print 'Need to add some code to remove residual elements from a previous list!'
        print 'Should work ok as long as new matches are not made between upload calls.'

    existing_phrases = gds.column_as_list(1)

    # We'll just delete all the overlapping rows and insert extras.
    rows_to_delete = [existing_phrases.index(phrase) for phrase in sorted_phrases if phrase in existing_phrases]

    gds.delete_rows(rows_to_delete)        

    if len(sorted_phrases) == 0:
        return

    # Next, we take the sorted phrases and generate a dictionary for each row to be inserted.  Each
    # row represented by the keys 'name' and all of the gdata_hdrs[ont][info_type]
    row_updates = [dict({gdata_hdrs[ont][info_type]:matches_by_type[phrase].get(ont,{}).get(info_type,'') 
                         for ont in ontologies for info_type in ONTOLOGY_DISPLAY_KEYS},
                        **{'name':phrase}) for phrase in sorted_phrases]

    gds.insert_rows(row_updates)



####################################################################################################
##
## Utilities for looping through phrase list and finding matches in ontologies
##
####################################################################################################
ITERATIONS_BETWEEN_SAVES=50
def _ontology_match_loop(ont_matches,exact_only=False,disable_intermediate_save=False,limit=None):
    num_matched = 0
    cumulative_match_time = 0
    ave_match_time = 0
    bp_client = BioPortalClient()
    for phrase_type in PHRASE_TYPES:
        _print_log('Searching ontologies for {}'.format(phrase_type))
        bp_client.reset_matched_types()
        total_phrases = len(ont_matches[MATCH_KEY_LIST][phrase_type])
        for phrase_idx,phrase in enumerate(ont_matches[MATCH_KEY_LIST][phrase_type]):
            if ont_matches[MATCH_KEY_STATUS][phrase_type][phrase_idx] == MATCH_STATUS_UNMATCHED:
                # If we have not tried a match yet, start with an exact match
                # print 'Searching for exact match to '+phrase
                ma,match_time = _call_find_matches(bp_client,phrase,phrase_type,True,False,ont_matches,disable_intermediate_save)
                cumulative_match_time+=match_time
                num_matched+=1
                if any([len(ma.get(ont,[]))>0 for ont in ONTOLOGIES[phrase_type]]):
                    ont_matches[MATCH_KEY_RESULTS][phrase_type][phrase] = ma
                    ont_matches[MATCH_KEY_STATUS][phrase_type][phrase_idx] = MATCH_STATUS_EXACT
                else:
                    ont_matches[MATCH_KEY_STATUS][phrase_type][phrase_idx] = MATCH_STATUS_EXACT_MIS

            if not exact_only and ont_matches[MATCH_KEY_STATUS][phrase_type][phrase_idx] == MATCH_STATUS_EXACT_MIS:
                # If we tried exact and missed, try a partial match.  Let's just do a partial, not an iterative suggestion
                # print 'Searching for partial match to '+phrase
                ma,match_time = _call_find_matches(bp_client,phrase,phrase_type,False,False,ont_matches,disable_intermediate_save)
                cumulative_match_time+=match_time
                num_matched+=1
                if any([len(ma.get(ont,[]))>0 for ont in ONTOLOGIES[phrase_type]]):
                    ont_matches[MATCH_KEY_RESULTS][phrase_type][phrase] = ma
                    ont_matches[MATCH_KEY_STATUS][phrase_type][phrase_idx] = MATCH_STATUS_PARTIAL
                else:
                    # print 'Failed to match phrase {} even without exact requirement!'.format(phrase)
                    ont_matches[MATCH_KEY_STATUS][phrase_type][phrase_idx] = MATCH_STATUS_PARTIAL_MIS

            if ont_matches[MATCH_KEY_STATUS][phrase_type][phrase_idx] in [MATCH_STATUS_EXACT,MATCH_STATUS_PARTIAL]:
                match_str = 'Matched'
            else:
                match_str = 'Failed to match'

            if num_matched > 0:
                ave_match_time = cumulative_match_time/num_matched
                

            _print_iters(match_str+' phrase {} out of {} (average match time so far: {})'.format(phrase_idx,total_phrases,ave_match_time),
                         phrase_idx)

            if limit is not None and phrase_idx >= limit:
                _print_log('Stopping after iteration limit reached!')
                break
            if num_matched > 0 and phrase_idx > 0 and phrase_idx % ITERATIONS_BETWEEN_SAVES == 0:
                _print_log('Saving current results on iteration {}'.format(phrase_idx))
                _store_partial_results(ont_matches,disable_intermediate_save)
                
        _print_log('Semantic Types Found for {}:'.format(phrase_type))
        _pprint_log(bp_client.matched_semantic_types)
    


def _call_find_matches(bp_client,phrase,phrase_type,exact,suggest,ont_matches,disable_intermediate_save):
    ''' Call find_matches, catch exceptions, time the process.
    @param bp_client BioPortalClient instance for the call.
    @param phrase Phrase to match.
    @param phrase_type One of PHRASE_TYPES.
    @param exact Pass through.
    @param ont_matches In case of exception, we will dump these data
    @param disable_intermediate_save Pass to _store_partial_results on exception.

    @returns result,time,error
    '''
    ma = None
    tstart = time.time()
    try:
        ma = bp_client.find_matches_in_distinct_ontologies(phrase,ONTOLOGIES[phrase_type],
                                                           exact=exact,
                                                           suggest=suggest,
                                                           page_limit=ONTOLOGY_MATCH_PAGE_LIMIT,
                                                           semantic_types=SEMANTIC_TYPES_RESTRICT[phrase_type],
                                                           semantic_types_sort=SEMANTIC_TYPES_SORT[phrase_type])
    except Exception as exc:
        if disable_intermediate_save:
            _print_log('Exception, but NOT dumping current results!')
        else:
            _print_log('Dumping current results on exception!')
            _store_partial_results(ont_matches,disable_intermediate_save)
        raise exc

    return ma,time.time()-tstart


####################################################################################################
##
## If run from the command line, we actually kick off the check_ontologies method, passing args.
##
####################################################################################################


if '__file__' in locals() and sys.argv[0] == os.path.basename(__file__):
    kwargs = {}
    boolean_args = ['exact_only','disable_intermediate_save','disable_push']
    integer_args = ['limit']
    if '-help' in sys.argv:
        print '\nUsage:'
        print '{} [-help] {}\n'.format(__file__,' '.join(['[-'+aa+']' for aa in boolean_args]+['[-'+aa+' INT]' for aa in integer_args]))
        exit(0)

    for argname in boolean_args:
        if '-'+argname in sys.argv:
            kwargs[argname] = True

    if '-test' in sys.argv:
        kwargs['disable_intermediate_save'] = True
        kwargs['disable_push'] = True
        kwargs['limit'] = 5

    for argname in integer_args:
        if '-'+argname in sys.argv:
            kwargs[argname] = int(sys.argv[sys.argv.index('-'+argname)+1])

    fh_log = open(FILE_LOG,'a')
    _print_log('{} called with args:{}'.format(__file__,kwargs))
    find_matches(**kwargs)
else:
    print 'Running in interactive mode.'
    fh_log = None
