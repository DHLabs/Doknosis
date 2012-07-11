import server
import json

import unittest

from server.settings import Testing


class AdminTestCase( unittest.TestCase ):

    is_setup = False

    def setUp( self ):
        if not self.is_setup:
            self.__class__.app = server.create_app( Testing ).test_client()
            self.__class__.is_setup = True

    def test_disease_autocomplete( self ):
        rv = self.app.get( '/admin/disease/autocomplete?term=AID' )

        results = json.loads( rv.data )

        assert len( results ) == 1
        assert results[0][ 'value' ] == 'AIDS'
        assert results[0][ 'label' ] == 'AIDS'

    def test_disease_autocomplete_multi( self ):
        rv = self.app.get( '/admin/disease/autocomplete?term=Fak' )

        results = json.loads( rv.data )

        assert len( results ) == 2
        assert results[0][ 'value' ] == 'Fake1'
        assert results[0][ 'label' ] == 'Fake1'
