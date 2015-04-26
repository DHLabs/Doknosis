from gdata.spreadsheet.service import SpreadsheetsService,DocumentQuery,CellQuery,ListQuery
from gdata.spreadsheet import SpreadsheetsCellsFeed
import time,re

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
    gd_client = None
    gd_cur_ss_key = None
    gd_cur_ws_id = None
    
    def __init__(self,uname,pswd,document_name=None,worksheet_name=None):
        # Connect to Google
        self.gd_client = SpreadsheetsService(email=uname,password=pswd,source=GDATA_SOURCE)
        self.gd_client.ProgrammaticLogin()
        if document_name is not None:
            self.set_document(document_name)
        if worksheet_name is not None:
            self.set_worksheet(worksheet_name)
    
    def __ss_check(self):
        ''' Make sure spreadsheet has been set before we try to do anything with worksheets.
        '''
        if self.gd_cur_ss_key is None:
            raise GDError('Must set spreadsheet before accessing worksheets!')

    def __header_to_key(self,hdr_string):
        ''' Google sheets column headers are used as keys to row info dictionaries, but first most non alphanumeric 
        characters are removed and the letters are lower-cased.
            
        '''
        return ''.join(re.findall('[a-z\-0-9\.]+',hdr_string.lower()))

    def set_document(self, docname):
        ''' Set current spreadsheet document given a title.
        '''
        q = DocumentQuery(params={'title':docname,'title-exact':'true'})
        ss_feed = self.gd_client.GetSpreadsheetsFeed(query=q)
        if len(ss_feed.entry) != 1:
            raise GDError('{} spreadsheets match the given name "{}" (expected exactly one)!'.format(len(ss_feed.entry),docname))
        self.gd_cur_ss_key = ss_feed.entry[0].id.text.rsplit('/',1)[1]

    def list_documents(self):
        ''' List all spreadsheet documents available.
        '''
        feed = self.gd_client.GetSpreadsheetsFeed(DocumentQuery())
        return [en.title.text for en in feed.entry]

    def list_worksheets(self):
        ''' List all worksheets in the current spreadsheet document.
        '''
        self.__ss_check()
        ws_feed = self.gd_client.GetWorksheetsFeed(self.gd_cur_ss_key)
        return [en.title.text for en in ws_feed.entry]

    def set_worksheet(self, sheetname):
        ''' Set current worksheet within the current spreadsheet document.
        '''
        self.__ss_check()
        q = DocumentQuery(params={'title':sheetname,'title-exact':'true'})
        ws_feed = self.gd_client.GetWorksheetsFeed(self.gd_cur_ss_key,query=q)
        if len(ws_feed.entry) != 1:
            raise GDError('{} worksheets match the given name "{}" (expected exactly one)!'.format(len(ws_feed.entry),sheetname))
        self.gd_cur_ws_id = ws_feed.entry[0].id.text.rsplit('/',1)[1]

    def add_worksheet(self, title, rows, cols, overwrite=False):
        ''' Add a worksheet to current spreadsheet document (if it does not exist).  Switch current sheet to the (new) guy.
        '''
        self.__ss_check()
        
        # First, check to see if the worksheet already exists
        q = DocumentQuery(params={'title':title,'title-exact':'true'})
        ws_feed = self.gd_client.GetWorksheetsFeed(self.gd_cur_ss_key,query=q)
        ws_found = None
        if len(ws_feed.entry) > 0:
            if overwrite:
                if not self.gd_client.DeleteWorksheet(ws_feed.entry[0]):
                    raise GDError('Failed to delete existing worksheet named {} to overwrite!'.format(title))
            else:
                ws_found = ws_feed.entry[0]

        is_new = ws_found is None
        if is_new:
            ws_found = self.gd_client.AddWorksheet(title,rows,cols,self.gd_cur_ss_key)

        self.gd_cur_ws_id = ws_found.id.text.rsplit('/',1)[1]

        return is_new

    def set_headers(self,header_names):
        ''' Set the current worksheet headers given a list.
        NOTE: header list length must match columns in sheet!
        '''
        self.__ss_check()
        ws = self.gd_client.GetWorksheetsFeed(self.gd_cur_ss_key,self.gd_cur_ws_id)
        if int(ws.col_count.text) != len(header_names):
            raise GDError('Number of headers ({}) does not match columns in spreadsheet ({})!'
                          .format(len(header_names),int(ws.col_count.text)))

        query = CellQuery(params={'min-row':'1','max-row':'1','min-col':'1','max-col':str(len(header_names))})
        cells = self.gd_client.GetCellsFeed(self.gd_cur_ss_key,self.gd_cur_ws_id,query=query)
        if len(cells.entry) == 0:
            query = CellQuery(params={'min-row':'1','max-row':'1','min-col':'1','max-col':str(len(header_names)),'return-empty':'true'})
            cells = self.gd_client.GetCellsFeed(self.gd_cur_ss_key,self.gd_cur_ws_id,query=query)

        batchRequest = SpreadsheetsCellsFeed()

        for idx,val in enumerate(header_names):
            cells.entry[idx].cell.inputValue = val
            batchRequest.AddUpdate(cells.entry[idx])

        updated = self.gd_client.ExecuteBatch(batchRequest,cells.GetBatchLink().href)


    def delete_rows(self,row_list):
        ''' Given a list of row numbers, delete the corresponding rows from the current sheet.
        @param row_list List of integers in 0:num_rows
        '''
        if len(row_list) == 0:
            return

        self.__ss_check()
        list_feed = self.gd_client.GetListFeed(self.gd_cur_ss_key, self.gd_cur_ws_id)
        ordered_list = sorted(row_list,reverse=True)
        if ordered_list[0] > int(list_feed.total_results.text):
            raise GDError('Tried to delete row {} but highest row number in sheet is {}!'.format(ordered_list[0],list_feed.total_results.text))

        for row in ordered_list:
            if not self.gd_client.DeleteRow(list_feed.entry[row]):
                raise GDError('Failed to delete row {} (partway through list: {})'.format(row,ordered_list))        
        
    def insert_rows(self,info_dict_list):
        ''' Add a group of rows based on list of dictionaries.

        @param info_dict_list Dictionary with keys for any headers with non-blank info in the new row 
        (all missing keys will be have blank data).
        '''
        self.__ss_check()
        # Check and make sure that none of the input dictionaries contains keys not in the first row of our list.
        hdr_list = [self.__header_to_key(hdr) for hdr in self.row_as_list(1)]
        bad_row = next((dd for dd in info_dict_list if len(set(dd.keys()) - set(hdr_list)) > 0), None)
        if bad_row is not None:
            raise GDError('Failed to insert row {} because it contains keys not in spreadsheet headers ({})!'
                          .format(bad_row,hdr_list))

        list_feed = self.gd_client.GetListFeed(self.gd_cur_ss_key, self.gd_cur_ws_id)
        for inf in info_dict_list:
            self.gd_client.InsertRow(inf,self.gd_cur_ss_key, self.gd_cur_ws_id)

    def column_as_list(self,column,with_header=False):
        ''' Read just a single column into a list of strings.

        Ignore the first row by default because it's the column header.
        '''
        self.__ss_check()
        if with_header:
            minrow = 1
        else:
            minrow = 2
        ws = self.gd_client.GetWorksheetsFeed(self.gd_cur_ss_key,self.gd_cur_ws_id)
        if int(ws.row_count.text) < minrow:
            return []

        q = CellQuery(params={'min-row':str(minrow),'min-col':str(column),'max-col':str(column)})
        cells = self.gd_client.GetCellsFeed(self.gd_cur_ss_key,self.gd_cur_ws_id,query=q)

        return [cellentry.cell.text for cellentry in cells.entry]

    def row_as_list(self,row):
        ''' Read just a single row into a list of strings.

        NOTE: this is indexed by cell, so row 1 is the header row!
        '''
        self.__ss_check()
        mincol = 1
        ws = self.gd_client.GetWorksheetsFeed(self.gd_cur_ss_key,self.gd_cur_ws_id)
        if int(ws.col_count.text) < mincol:
            return []

        q = CellQuery(params={'min-row':str(row),'min-col':str(mincol),'max-row':str(row)})
        cells = self.gd_client.GetCellsFeed(self.gd_cur_ss_key,self.gd_cur_ws_id,query=q)

        return [cellentry.cell.text for cellentry in cells.entry]
        

    def read_to_list(self,num_lines=None):
        """ Read the sheet into a list of lists of strings """
        self.__ss_check()
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

    def read_to_dict(self,key_column_name,row_start=None,row_num=None):
        """ Read the sheet into a dictionary with keys given by the named column.
        
        NOTE: Raises an error on any redundant rows.
        """

        self.__ss_check()

        # Use this for testing to limit number of results handled:
        params = {}
        if row_start is not None:
            params['start-index'] = '%d'%row_start
        if row_num is not None:
            params['max-results'] = '%d'%row_num
        if len(params) != 0:
            q = ListQuery(params=params)
            list_feed = self.gd_client.GetListFeed(self.gd_cur_ss_key, self.gd_cur_ws_id,query=q)
        else:
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
