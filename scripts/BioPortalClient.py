import urllib,urllib2,json,time,errno,re
from socket import error as socket_error
from pyxdameraulevenshtein import damerau_levenshtein_distance

BIOONT_REST_URL = "http://data.bioontology.org"
BIOONT_API_KEY = "99418b93-626e-4b96-a538-c06e7c1822fd"

SOCKET_RETRY_MAX = 5

# This also includes the bioportal semantic types, which are mostly just for refining searches
ONTOLOGY_SNOMEDCT='SNOMEDCT'
ONTOLOGY_ICD10='ICD10'
ONTOLOGY_ICD10CM='ICD10CM'
ONTOLOGY_LOINC='LOINC'
ONTOLOGY_STY='STY'
ALL_ONTOLOGIES = [ONTOLOGY_SNOMEDCT,ONTOLOGY_ICD10,ONTOLOGY_ICD10CM,ONTOLOGY_LOINC,ONTOLOGY_STY]

# These are keys for info dictionaries returned from searches.  Meanings are:
# ONTOLOGY_INFO_NEAR           - Nearest term (preferred label or synonym) in the ontology to the given phrase
# ONTOLOGY_INFO_PREF           - Preferred label for the matching term
# ONTOLOGY_INFO_STYPE          - Semantic type of the matching term
# ONTOLOGY_INFO_DISTANCE       - Distance between search phrase and nearest term (how good was the match?)
ONTOLOGY_INFO_NEAR='Nearest'
ONTOLOGY_INFO_PREF='Preferred Label'
ONTOLOGY_INFO_STYPE='Semantic Type'
ONTOLOGY_INFO_DISTANCE='Match Distance'
ONTOLOGY_INFO_KEYS = [ONTOLOGY_INFO_NEAR,ONTOLOGY_INFO_PREF,ONTOLOGY_INFO_STYPE,ONTOLOGY_INFO_DISTANCE]

class BPPagingError(Exception):
    """ Exception thrown when the methods in this module are misused (NOT for HTTP error forwarding)"""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
            return 'Paging Error in json responses -- \"{}\"!'.format(self.msg)

class BPUnknownOntologyError(Exception):
    """ Exception thrown when a request is made on an ontology not recognized by this package. """
    def __init__(self, ont):
        self.ont = ont
    def __str__(self):
            return 'Unrecognized Ontology -- \"{}\"!  Add to ALL_ONTOLOGIES?'.format(self.ont)

class BioPortalClient(object):
    '''  API manager for BioPortal.
    
    Handle url connection, enable searches and so forth.
    '''
    all_semantic_types = None
    matched_semantic_types = None
    url_opener=None
    socket_retry=0

    def reset_connection(self):
        self.url_opener = urllib2.build_opener()
        self.url_opener.addheaders = [('Authorization', 'apikey token=' + BIOONT_API_KEY)]

    def reset_matched_types(self):
        self.matched_semantic_types = set()

    def update_matched_types_from_string(self,typestring):
        self.matched_semantic_types |= set(re.findall('\((T[0-9]{3})\)',typestring))

    def __init__(self):
        self.__setup_all_semantic_types()
        self.reset_matched_types()
        self.socket_retry=0
        self.reset_connection()

    def __get_json_from_url(self,url):
        # print 'trying url:'+url
        try:
            jl = json.loads(self.url_opener.open(url).read())
        except urllib2.HTTPError as er:
            # If we get an HTTPError, print the url before we pass it up.
            print 'Exception in the following url: {}'.format(er.url)
            raise er
        except socket_error as er:
            if er.errno != errno.ECONNRESET:
                print 'Socket error trying the following url: {}'.format(url)
                raise er
            # how many times to retry?
            self.socket_retry = self.socket_retry+1
            if self.socket_retry > SOCKET_RETRY_MAX:
                print 'Connection reset {} times trying the following url: {}'.format(self.socket_retry,url)
                raise er
            print 'Connection reset {} times.  Try again after a pause.'.format(self.socket_retry)
            time.sleep(1)
            self.reset_connection()
            jl = self.__get_json_from_url(url)

        # if we made it here, we got through and we will reset the socket_retry count
        self.socket_retry = 0
        return jl

    def bioportal_query(self,query_string):
        return self.__get_json_from_url(BIOONT_REST_URL+"/search?q="+query_string)


    def find_matches_in_distinct_ontologies(self,phrase,ontologies=[ONTOLOGY_SNOMEDCT],**kwargs):
        ''' Find ontological matches for a list of ontologies, return a dictionary of results.

        @returns single key dictionary with ontology name indexing a dictionary with keys ONTOLOGY_INFO_KEYS
        
        '''

        rval = {}
        for ont in ontologies:
            res = self.find_match_in_ontologies(phrase,[ont],**kwargs)
            if res is not None:
                rval[ont] = res

        return rval


    def find_match_in_ontologies(self,phrase,ontologies,semantic_types_sort=None,semantic_types=None,**kwargs):
        ''' Check bioportal for matching terms given a phrase.

        @param phrase String describing the term we're looking for
        @param ontologies String describing the ontologies to search.  Must be in ALL_ONTOLOGIES.
        @param exact Boolean.  Should we use exact matching or try to find the closest?
        @param semantic_types List of strings with bioontology semantic type id's to restrict search.
        
        @returns dict with keys:

        ONTOLOGY_INFO_NEAR:     (string) closest string to name in ontologies (might be synonym or preferred label)
        ONTOLOGY_INFO_PREF:     (string) ontologies 'preferred label' for matching term
        ONTOLOGY_INFO_STYPE:    (string) comma-separated list of "NAME [CODE]", where NAME is
                                         semantic type name and CODE is the code in bioontology
        ONTOLOGY_INFO_DISTANCE: (string) how good was the match?
        '''
        # print 'Searching for match for phrase {}, ontologies {}'.format(phrase,ontologies)
        nl = self.get_node_list_from_string(phrase,ontologies=ontologies,semantic_types=semantic_types,**kwargs)

        if len(nl) == 0:
            return {}

        if semantic_types_sort is None and semantic_types is not None:
            semantic_types_sort = semantic_types

        # It would probably be smart to do some checking here to make sure distance is not too far off...
        distances = [self.__distance_to_term(phrase,ot) for ot in nl]

        # Now we do a crazy min function.  First look at distance (if distance is zero we have an exact match).  If
        # distances tie, give preference to the guy which matched the prefLabel as opposed to a synonym.  Finally,
        # if both of those tie and semantic_types were specified, give preference to the guy with the semantic type
        # which is earliest in our given list.
        if semantic_types_sort is None:
            sort_func = lambda dinfo:(dinfo[ONTOLOGY_INFO_DISTANCE],
                                      dinfo['Nearest'] != dinfo['term']['prefLabel'])
        else:
            # Add all the other types on the end so we can use a simple sorting function (don't have to check
            # for membership in list)
            semantic_types_sort.extend(list(set(self.all_semantic_types) - set(semantic_types_sort)))
            sort_func = lambda dinfo:(dinfo[ONTOLOGY_INFO_DISTANCE],
                                      dinfo['Nearest'] != dinfo['term']['prefLabel'],
                                      min([semantic_types_sort.index(st) for st in dinfo['term']['semanticType']]))

        closest = min(distances,key=sort_func)
        # sortdist = sorted(distances,key=sort_func)
        # from pprint import pprint
        # pprint([(dinfo[ONTOLOGY_INFO_DISTANCE],
        #          dinfo['Nearest'] != dinfo['term']['prefLabel'],
        #          dinfo['term']['semanticType'],dinfo['Nearest']) for dinfo in sortdist[0:20]])
        # closest = sortdist[0]

        cur_stypes_matched = closest['term']['semanticType']
        self.matched_semantic_types |= set(cur_stypes_matched)

        return {ONTOLOGY_INFO_NEAR:closest[ONTOLOGY_INFO_NEAR],
                ONTOLOGY_INFO_PREF:closest['term']['prefLabel'],
                ONTOLOGY_INFO_STYPE:','.join(['{} ({})'.format(self.all_semantic_types[st],st) for st in cur_stypes_matched]),
                ONTOLOGY_INFO_DISTANCE:closest[ONTOLOGY_INFO_DISTANCE]
                }


    def __distance_between_phrases(self,phrase1,phrase2):
        ''' May try different ways to measure distance.
        '''
        return damerau_levenshtein_distance(phrase1,phrase2)

    def __distance_to_term(self,phrase,oterm):
        ''' Return the distance from a given phrase to an ontological term.

        There is probably a more clever way to find the smallest distance and return the string:dist pair,
        but don't want to do too much premature optimization here.

        @param phrase A phrase expected to in some sense partially match the term.
        @param oterm A dictionary with @id,prefLabel,synonym,semanticType 
        (as an element of list returned by get_node_list_from_string)
        @returns {STRING:DIST} Where DIST is the numerical distance and STRING 
        is the string within the ontological term (prefLabel or a synonym) that
        best matches.
        '''
        all_distances = {name:self.__distance_between_phrases(phrase,name.lower()) for name in [oterm['prefLabel']]+oterm['synonym']}
        closest = min(all_distances,key=all_distances.get)

        return {'term':oterm,ONTOLOGY_INFO_NEAR:closest,ONTOLOGY_INFO_DISTANCE:all_distances[closest]}

    def get_all_stypes(self):
        ''' Return the whole semantic type ontology as a dictionary of id:prefLabel pairs.
        '''
        rdict = {}
        for root_node in [u'T071',u'T051']:
            jl = self.bioportal_query(root_node+"&ontologies=http://data.bioontology.org/ontologies/STY"
                                  +"&include=prefLabel&include_context=false&include_links=true&exact_match=true")

            if len(jl['collection']) != 1:
                raise Exception('Failed to find exactly one semantic type for root label {}'.format(root_node))                

            if 'prefLabel' not in jl['collection'][0] or 'links' not in jl['collection'][0] or 'descendants' not in jl['collection'][0]['links']:
                from pprint import pprint
                pprint(jl)
                raise Exception('Root label {} did not have expected structure!  JSON dumped above'.format(root_node))

            rdict[root_node] = jl['collection'][0]['prefLabel']

            jl = self.__get_json_from_url(jl['collection'][0]['links']['descendants'])
            npages = jl['pageCount']
            for idx in range(1,npages+1):
                if jl['page'] != idx:
                    raise BPPagingError('page {} at iteration {}!'.format(jl['page'],idx))
                if(len(jl['collection']) > 0):
                    for v in jl['collection']:
                        rdict[v['@id'][-4:]]=v['prefLabel']
                if jl['page'] < jl['pageCount']:
                    jl = self.__get_json_from_url(jl['links']['nextPage'])
    
            if (npages > 0) and (jl['page'] != npages):
                raise BPPagingError('page {} after processing list of {} pages!'.format(jl['page'],jl['pageCount']))

        return rdict

    def get_node_list_from_string(self,string_in,ontologies,suggest=False,page_limit=None,exact=True,semantic_types=None):
        """ Collect a list of all nodes matching the given string from the given ontologies via the bioontology api

        Two ways of doing non-exact matches:
        1) If 'suggest' is true, it makes suggestions geared towards autocomplete (favors phrase at beginning, does not
        allow for missing terms in the middle of the phrase)
        2) Otherwise suggestions seem to be based in a sense on distance.

        If exact is false and suggest is true, we iterate over successively smaller strings using 'suggest' until there is at least one
        matching node.  Once we collect at least one matching node, we go through all pages (search is paginated to 50/page by default)
        of nodes and collect a subset of the info.  This seems to be catching too many options, so I'll default to exact=True.

        @param string_in search string
        @param ontologies list of one or more strings from ALL_ONTOLOGIES
        @param exact if true, only accept exact matches to string_in.  Otherwise we iterate over successively smaller strings 
        until there is at least one match, or all words in the string contain a single letter.
        @param semantic_types list of STY strings (e.g., 'T184' for Sign or Symptom) to restrict search
        @returns list of dictionaries with @id,prefLabel,synonym,semanticType, and ancestors keys, all of which match string_in 
        (to some degree) in either the label or synonym fields.
        @exception Exception raised if any ontology is unrecognized, if we fail to match any strings, or if we encounter an error 
        in the page count coming back from bioontology.com.
        """
        if string_in is None or len(string_in) == 0:
            return []

        if any([ont not in ALL_ONTOLOGIES for ont in ontologies]):
            raise BPUnknownOntologyError([ont for ont in ontologies if ont not in ALL_ONTOLOGIES])

        if semantic_types is None:
            stStr = ''
        else:
            stStr = '&semantic_types='+','.join(semantic_types)

        ontStr = '&ontologies='+','.join(['http://data.bioontology.org/ontologies/'+ont for ont in ontologies])
        inclStr = '&include=prefLabel,semanticType,synonym&include_context=false&include_links=true'
        params = ontStr+inclStr+stStr

        if exact:
            jl = self.bioportal_query(urllib.quote_plus(string_in)+params+"&exact_match=true")

        elif suggest:

            # The suggestion process has some peculiarities: it has to have all words represented by at least one letter, and will not strip letters
            # to match.  For example, Myocardial infarction has synonym 'infarction of heart', which will be matched with:
            # 'infarction of h' => YES
            # 'infarction o heart' => YES
            # 'infarct of hea' => YES
            # 'infarction heart' => NO  (also 'infarction  heart' => NO)
            # So here we will dial back each word one letter at a time, and try each phrase.  No point dialing back too far, though.  Stop
            # the reduction of longer words at 3 letters.
            words = string_in.split(' ')
            wIdx = 0
            nwords = len(words)
            # suggest_params = params+"&suggest=true&exact_match=false"
            suggest_params = params+"&exact_match=false&suggest=true"
            # Stop reducing at 3 characters for longer words.
            stop_length = [min(len(ww),3) for ww in words]
            jl = self.bioportal_query(urllib.quote_plus(' '.join(words))+suggest_params)
            while (len(jl['collection']) == 0) and len(''.join(words)) > sum(stop_length):
                # Step through words, each iteration we reduce the length of one word by one letter.
                # This will give extra weight to longer words, but I think that's probably a good thing.
                if len(words[wIdx]) > stop_length[wIdx]:
                    words[wIdx] = words[wIdx][:-1]
                    jl = self.bioportal_query(urllib.quote_plus(' '.join(words))+suggest_params)
                wIdx = (wIdx+1)%nwords

        else:
            jl = self.bioportal_query(urllib.quote_plus(string_in)+params)
        
        if len(jl['collection']) == 0:
            return []

        # search is paginated, so next we have to collect all pages.
        allNodes = []
        # Just to make sure, we'll count ourselves
        npages = jl['pageCount']
        if page_limit is not None and page_limit < npages:
            npages = page_limit
        # print 'Sorting through {} pages'.format(npages)
        for idx in range(1,npages+1):
            if jl['page'] != idx:
                raise BPPagingError('page {} at iteration {}!'.format(jl['page'],idx))
            if(len(jl['collection']) > 0):
                allNodes.extend([{'@id':v['@id'],
                                  'prefLabel':v['prefLabel'],
                                  'synonym':v.get('synonym',[]),
                                  'semanticType':v['semanticType'],
                                  'ancestors':v['links']['ancestors']} for v in jl['collection'] 
                                 if 'semanticType' in v and 'prefLabel' in v and '@id' in v])
                # print 'from page {}, found: {}'.format(idx,[v['prefLabel'] for v in jl['collection']
                #                                             if 'semanticType' in v and 'prefLabel' in v and '@id' in v])
            if jl['page'] < npages:
                jl = self.__get_json_from_url(jl['links']['nextPage'])
    
        if (npages > 0) and (jl['page'] != npages):
            raise BPPagingError('page {} after processing list of {} pages!'.format(jl['page'],npages))

        return allNodes

    def cull_to_roots(self,nodeList):
        """ Given a list of bioontology nodes (as returned by get_node_list_from_string), find all the root nodes.

        Remove all nodes from the list which have ancestors within the list.  This code is a little buggy (partially
        because some of the ontologies are a little buggy) so use with caution.

        @param nodeList list of nodes with @id and ancestors keys
        @returns subset of nodeList which does not have ancestors within nodeList
        @exception Exception raised if any of the nodes fails to find any ancestors (all nodes should have at least one!)
        """

        idList = [z['@id'] for z in nodeList]
        outList = []
        for node in nodeList:
            ancestors = self.__get_json_from_url(node['ancestors'])
            found = False
            for ancestor in ancestors:
                if ancestor['@id'] in idList:
                    found = True
                    break
            if not found:
                outList.append(node)

        return outList

##
##  Here is a list of all semantic types.
##
    def __setup_all_semantic_types(self):
        self.all_semantic_types = {u'T001': u'Organism',
                                   u'T002': u'Plant',
                                   u'T004': u'Fungus',
                                   u'T005': u'Virus',
                                   u'T007': u'Bacterium',
                                   u'T008': u'Animal',
                                   u'T010': u'Vertebrate',
                                   u'T011': u'Amphibian',
                                   u'T012': u'Bird',
                                   u'T013': u'Fish',
                                   u'T014': u'Reptile',
                                   u'T015': u'Mammal',
                                   u'T016': u'Human',
                                   u'T017': u'Anatomical Structure',
                                   u'T018': u'Embryonic Structure',
                                   u'T019': u'Congenital Abnormality',
                                   u'T020': u'Acquired Abnormality',
                                   u'T021': u'Fully Formed Anatomical Structure',
                                   u'T022': u'Body System',
                                   u'T023': u'Body Part, Organ, or Organ Component',
                                   u'T024': u'Tissue',
                                   u'T025': u'Cell',
                                   u'T026': u'Cell Component',
                                   u'T028': u'Gene or Genome',
                                   u'T029': u'Body Location or Region',
                                   u'T030': u'Body Space or Junction',
                                   u'T031': u'Body Substance',
                                   u'T032': u'Organism Attribute',
                                   u'T033': u'Finding',
                                   u'T034': u'Laboratory or Test Result',
                                   u'T037': u'Injury or Poisoning',
                                   u'T038': u'Biologic Function',
                                   u'T039': u'Physiologic Function',
                                   u'T040': u'Organism Function',
                                   u'T041': u'Mental Process',
                                   u'T042': u'Organ or Tissue Function',
                                   u'T043': u'Cell Function',
                                   u'T044': u'Molecular Function',
                                   u'T045': u'Genetic Function',
                                   u'T046': u'Pathologic Function',
                                   u'T047': u'Disease or Syndrome',
                                   u'T048': u'Mental or Behavioral Dysfunction',
                                   u'T049': u'Cell or Molecular Dysfunction',
                                   u'T050': u'Experimental Model of Disease',
                                   u'T051': u'Event',
                                   u'T052': u'Activity',
                                   u'T053': u'Behavior',
                                   u'T054': u'Social Behavior',
                                   u'T055': u'Individual Behavior',
                                   u'T056': u'Daily or Recreational Activity',
                                   u'T057': u'Occupational Activity',
                                   u'T058': u'Health Care Activity',
                                   u'T059': u'Laboratory Procedure',
                                   u'T060': u'Diagnostic Procedure',
                                   u'T061': u'Therapeutic or Preventive Procedure',
                                   u'T062': u'Research Activity',
                                   u'T063': u'Molecular Biology Research Technique',
                                   u'T064': u'Governmental or Regulatory Activity',
                                   u'T065': u'Educational Activity',
                                   u'T066': u'Machine Activity',
                                   u'T067': u'Phenomenon or Process',
                                   u'T068': u'Human-caused Phenomenon or Process',
                                   u'T069': u'Environmental Effect of Humans',
                                   u'T070': u'Natural Phenomenon or Process',
                                   u'T071': u'Entity',
                                   u'T072': u'Physical Object',
                                   u'T073': u'Manufactured Object',
                                   u'T074': u'Medical Device',
                                   u'T075': u'Research Device',
                                   u'T077': u'Conceptual Entity',
                                   u'T078': u'Idea or Concept',
                                   u'T079': u'Temporal Concept',
                                   u'T080': u'Qualitative Concept',
                                   u'T081': u'Quantitative Concept',
                                   u'T082': u'Spatial Concept',
                                   u'T083': u'Geographic Area',
                                   u'T085': u'Molecular Sequence',
                                   u'T086': u'Nucleotide Sequence',
                                   u'T087': u'Amino Acid Sequence',
                                   u'T088': u'Carbohydrate Sequence',
                                   u'T089': u'Regulation or Law',
                                   u'T090': u'Occupation or Discipline',
                                   u'T091': u'Biomedical Occupation or Discipline',
                                   u'T092': u'Organization',
                                   u'T093': u'Health Care Related Organization',
                                   u'T094': u'Professional Society',
                                   u'T095': u'Self-help or Relief Organization',
                                   u'T096': u'Group',
                                   u'T097': u'Professional or Occupational Group',
                                   u'T098': u'Population Group',
                                   u'T099': u'Family Group',
                                   u'T100': u'Age Group',
                                   u'T101': u'Patient or Disabled Group',
                                   u'T102': u'Group Attribute',
                                   u'T103': u'Chemical',
                                   u'T104': u'Chemical Viewed Structurally',
                                   u'T109': u'Organic Chemical',
                                   u'T110': u'Steroid',
                                   u'T111': u'Eicosanoid',
                                   u'T114': u'Nucleic Acid, Nucleoside, or Nucleotide',
                                   u'T115': u'Organophosphorus Compound',
                                   u'T116': u'Amino Acid, Peptide, or Protein',
                                   u'T118': u'Carbohydrate',
                                   u'T119': u'Lipid',
                                   u'T120': u'Chemical Viewed Functionally',
                                   u'T121': u'Pharmacologic Substance',
                                   u'T122': u'Biomedical or Dental Material',
                                   u'T123': u'Biologically Active Substance',
                                   u'T124': u'Neuroreactive Substance or Biogenic Amine',
                                   u'T125': u'Hormone',
                                   u'T126': u'Enzyme',
                                   u'T127': u'Vitamin',
                                   u'T129': u'Immunologic Factor',
                                   u'T130': u'Indicator, Reagent, or Diagnostic Aid',
                                   u'T131': u'Hazardous or Poisonous Substance',
                                   u'T167': u'Substance',
                                   u'T168': u'Food',
                                   u'T169': u'Functional Concept',
                                   u'T170': u'Intellectual Product',
                                   u'T171': u'Language',
                                   u'T184': u'Sign or Symptom',
                                   u'T185': u'Classification',
                                   u'T190': u'Anatomical Abnormality',
                                   u'T191': u'Neoplastic Process',
                                   u'T192': u'Receptor',
                                   u'T194': u'Archaeon',
                                   u'T195': u'Antibiotic',
                                   u'T196': u'Element, Ion, or Isotope',
                                   u'T197': u'Inorganic Chemical',
                                   u'T200': u'Clinical Drug',
                                   u'T201': u'Clinical Attribute',
                                   u'T203': u'Drug Delivery Device',
                                   u'T204': u'Eukaryote'}
