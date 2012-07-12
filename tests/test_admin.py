import os
import server
import json

import unittest

from server.settings import Testing
from server.helpers.data import parse_csv


class AdminTestCase( unittest.TestCase ):

    is_setup = False

    def setUp( self ):
        if not self.is_setup:
            self.__class__.app = server.create_app( Testing ).test_client()
            self.__class__.is_setup = True
            self.__class__.data_directory = os.path.join( os.getcwd(),
                                                          'tests/data' )

    def test_disease_autocomplete( self ):
        rv = self.app.get( '/api/disease/autocomplete?term=AID' )

        results = json.loads( rv.data )

        assert len( results ) == 1
        assert results[0][ 'value' ] == 'AIDS'
        assert results[0][ 'label' ] == 'AIDS'

    def test_disease_autocomplete_multi( self ):
        rv = self.app.get( '/api/disease/autocomplete?term=Fak' )

        results = json.loads( rv.data )

        assert len( results ) == 2
        assert results[0][ 'value' ] == 'Fake1'
        assert results[0][ 'label' ] == 'Fake1'

    def test_disease_parsing( self ):
        # Check that we can parse a correct CSV
        errors = parse_csv( os.path.join( self.data_directory,
                                          'csv/good-csv.csv' ) )
        assert len( errors ) == 0

        # Check for correct invalid id checking
        errors = parse_csv(os.path.join( self.data_directory,
                                         'csv/invalid-id.csv' ))
        assert len( errors ) == 1
        assert 'Invalid Disease ID' in errors[0]

        # Check for correct invalid finding checking
        errors = parse_csv(os.path.join( self.data_directory,
                                         'csv/invalid-findings.csv' ))
        assert len( errors ) == 1
        assert 'Invalid finding format' in errors[0]

        # Check for correct invalid disease name
        errors = parse_csv(os.path.join( self.data_directory,
                                         'csv/invalid-format.csv' ))
        assert len( errors ) == 1
        assert 'Invalid Disease Name' in errors[0]
