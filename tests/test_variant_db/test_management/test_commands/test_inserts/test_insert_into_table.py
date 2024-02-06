from django.test import TestCase

from variant_db.models import Sample 
from variant_db.management.commands.insert import (
    _insert_into_table,
)

class TestInsertIntoTable_GettingExisting(TestCase):
    """
    Check that when GETTING already-existing entries from a model, the function works correctly
    CASE: A Sample already exists in the table and an entry is made for it.s
    EXPECT: the Sample is fetched rather than duplicated. "rename" isn't used.
    """
    def setUp(self) -> None:
        self.sample, _ = Sample.objects.get_or_create(
            instrument_id="test_inst",
            batch_id="test_batch",
            specimen_id="test_specimen"
        )

    def test_getting_sample_without_rename(self):
        # Call the function on a test dictionary, which is already subsetted and has correct names
        test_dict = {
            "instrument_id": "test_inst",
            "batch_id": "test_batch",
            "specimen_id": "test_specimen"
        }

        retrieved_entry = _insert_into_table(Sample, **test_dict)

        # in this case, we expect _insert_into_table to fetch the already-existing entry,
        # rather than making a new one 
        assert self.sample.id == retrieved_entry.id

    #TODO: sample with rename
    #TODO: same again except it's making from scratch, rather than the db already having entries
    #TODO: make sure the try/except is hit