from django.test import TestCase

from panels_backend.management.commands._insert_ci import (
    _check_for_changed_pg_justification,
)

class TestCheckChangedPg(TestCase):
    def setUp(self) -> None:
        return super().setUp()
    
