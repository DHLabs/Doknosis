from gdata.spreadsheet.service import SpreadsheetsService,DocumentQuery

GDATA_MAIN_DOC = 'Doknosis 0.2'
GDATA_SOURCE = 'doknosis.GDSpreadsheet'
GDATA_WS_PREVALENCE = 'Drugs and Diseases Updated'
GDATA_WS_GEO = 'Geo'

class GDError(Exception):
    """ Exception generated when google data access classes are misused. """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return 'Google Data Access Error -- \"{}\"!'.format(self.msg)


class GDataClient(object):
    # gd_client = SpreadsheetsService()
    gd_client = None
    gd_cur_ss_key = None
    gd_cur_ws_id = None

    def __init__(self,uname,pswd):
        # Connect to Google
        self.gd_client = SpreadsheetsService(email=uname,password=pswd,source=GDATA_SOURCE)
        self.gd_client.ProgrammaticLogin()

    def __ss_check(self):
        if self.gd_cur_ss_key is None:
            raise GDError('Must set spreadsheet before accessing worksheets!')        

    def set_document(self, docname):
        q = DocumentQuery(params={'title':docname,'title-exact':'true'})
        ss_feed = self.gd_client.GetSpreadsheetsFeed(query=q)
        if len(ss_feed.entry) != 1:
            raise GDError('{} spreadsheets match the given name "{}" (expected exactly one)!'.format(len(ss_feed.entry),docname))
        self.gd_cur_ss_key = ss_feed.entry[0].id.text.rsplit('/',1)[1]

    def list_documents(self):
        feed = self.gd_client.GetSpreadsheetsFeed(DocumentQuery())
        return [en.title.text for en in feed.entry]

    def list_worksheets(self):
        self.__ss_check()
        ws_feed = self.gd_client.GetWorksheetsFeed(self.gd_cur_ss_key)
        return [en.title.text for en in ws_feed.entry]

    def set_worksheet(self, sheetname):
        self.__ss_check()
        q = DocumentQuery(params={'title':sheetname,'title-exact':'true'})
        ws_feed = self.gd_client.GetWorksheetsFeed(self.gd_cur_ss_key,query=q)
        if len(ws_feed.entry) != 1:
            raise GDError('{} worksheets match the given name "{}" (expected exactly one)!'.format(len(ws_feed.entry),sheetname))
        self.gd_cur_ws_id = ws_feed.entry[0].id.text.rsplit('/',1)[1]


    def read_to_list(self,num_lines=None):
        """ Read the sheet into a list of lists of strings """
        if num_lines is not None:
            q = DocumentQuery(params={'max-results':'%d'%num_lines})
            list_feed = self.gd_client.GetListFeed(self.gd_cur_ss_key, self.gd_cur_ws_id,query=q)
        else:
            list_feed = self.gd_client.GetListFeed(self.gd_cur_ss_key, self.gd_cur_ws_id)

        string_list = []
        for i, entry in enumerate(list_feed.entry):
            row = {key:entry.custom[key].text for key in entry.custom}
            row['rowname'] = entry.title.text
            string_list.append(row)
        
        return string_list

    def read_to_dict(self,key_column_name):
        """ Read the sheet into a dictionary with keys given by the named column.
        
        NOTE: Raises an error on any redundant rows.
        """

        # Use this for testing to limit number of results handled:
        # q = DocumentQuery(params={'max-results':'210'})
        # list_feed = self.gd_client.GetListFeed(self.gd_cur_ss_key, self.gd_cur_ws_id,query=q)
        list_feed = self.gd_client.GetListFeed(self.gd_cur_ss_key, self.gd_cur_ws_id)

        multi_rows = []
        string_dict = {}
        for i, entry in enumerate(list_feed.entry):
            # If we get the title column, ignore it.
            if entry.custom[key_column_name].text.replace(' ','').lower() == key_column_name:
                continue
            row = {key:entry.custom[key].text for key in entry.custom if key is not key_column_name}
            row['rowname'] = entry.title.text
            key_name = entry.custom[key_column_name].text
            if key_name in string_dict:
                multi_rows.append(key_name)
            string_dict[key_name] = row

        if len(multi_rows) > 0:
            errors = 'read_to_dict -- Column {} contains multiple rows with each of the following values: {}'.format(key_column_name,multi_rows)
            # raise GDError('read_to_dict -- Column {} contains multiple rows with each of the following values: {}'.format(key_column_name,multi_rows))
        else:
            errors = None

        return string_dict,errors
