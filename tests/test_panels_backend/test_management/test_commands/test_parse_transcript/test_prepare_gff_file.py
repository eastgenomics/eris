from django.test import TestCase
from django.contrib.auth.models import User
from unittest import mock
import pandas as pd

from panels_backend.models import Gene, HgncRelease
from panels_backend.management.commands._parse_transcript import (
    _prepare_gff_file,
)

class TestPrepareGffFile(TestCase):
    """
    Test the function prepare_hgnc_file in _parse_transcript.py
    """

    def setUp(self) -> None:
        return None        
    
    def test_prepare_normal_format(self):
        # TODO: add mocking of file open
        _prepare_gff_file(
            "/dev/null"
        )
