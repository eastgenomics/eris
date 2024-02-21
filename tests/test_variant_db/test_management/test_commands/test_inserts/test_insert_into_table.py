from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from variant_db.models import Sample, Institution, Chromosome
from variant_db.management.commands.insert import (
    _get_or_create,
)


class TestInsertIntoTable_GettingExisting(TestCase):
    """
    Check that when GETTING already-existing entries from a model, the function works correctly.
    Check the cases for models which need column renaming, and models which don't.
    """

    def setUp(self) -> None:
        self.sample, _ = Sample.objects.get_or_create(
            instrument_id="test_inst",
            batch_id="test_batch",
            specimen_id="test_specimen",
        )

        self.inst, _ = Institution.objects.get_or_create(
            name="NHS Foundation Trust"
        )

    def test_getting_sample_without_rename(self):
        """
        CASE: A Sample already exists in the table and an entry needs to be linked to it.
        EXPECT: the Sample is fetched rather than duplicated. "rename" isn't used.
        """
        # Call the function on a test dictionary, which is already subsetted and has correct names
        test_dict = {
            "instrument_id": "test_inst",
            "batch_id": "test_batch",
            "specimen_id": "test_specimen",
        }

        retrieved_entry = _get_or_create(Sample, **test_dict)

        # in this case, we expect _get_or_create to fetch the already-existing entry
        assert self.sample.id == retrieved_entry.id

    def test_getting_inst_with_rename(self):
        """
        CASE: An Institute already exists in the table and an entry needs to be linked to it.
        EXPECT: the Institute is fetched rather than duplicated. "rename" IS used.
        """
        # Call the function on a test dictionary, already subsetted, with a rename required
        test_dict = {"institution": "NHS Foundation Trust"}
        names_to = {"institution": "name"}

        retrieved_entry = _get_or_create(
            Institution, names_to=names_to, **test_dict
        )

        # in this case, we expect _get_or_create to fetch the already-existing entry
        assert self.inst.id == retrieved_entry.id


class TestInsertIntoTable_MakingFromScratch(TestCase):
    """
    Check that when CREATING not-already-existing entries in a model, the function works correctly.
    Check the cases for models which need column renaming, and models which don't.
    """

    # no set-up function needed - empty database, in this scenario
    def test_creating_sample_without_rename(self):
        """
        CASE: A Sample isn't in the database yet.
        EXPECT: A Sample entry is made. "rename" isn't used.
        """
        # Call the function on a test dictionary, which is already subsetted and has correct names
        test_dict = {
            "instrument_id": "test_inst",
            "batch_id": "test_batch",
            "specimen_id": "test_specimen",
        }

        retrieved_entry = _get_or_create(Sample, **test_dict)

        assert retrieved_entry.instrument_id == "test_inst"

    def test_creating_inst_with_rename(self):
        # Call the function on a test dictionary, already subsetted, with a rename required
        test_dict = {"institution": "NHS Foundation Trust"}
        names_to = {"institution": "name"}

        retrieved_entry = _get_or_create(
            Institution, names_to=names_to, **test_dict
        )

        assert retrieved_entry.name == "NHS Foundation Trust"
<<<<<<< HEAD


class Test_FetchOnly_Queries(TestCase):
    """
    Test cases to test that the "get" behaviour of `_get_or_create` works as intended
    """

    def setUp(self) -> None:
        """
        Insert a row of valid `Chromosome` data to be referenced
        """
        _, _ = Chromosome.objects.get_or_create(
            name="1",
            numerical_name=1,
            source="RefSeq",
        )

    def test_raises_objectdoesnotexist(self):
        """
        CASE: Submit a query against `Chromosome` for a chromosome that doesn't exist
        EXPECTS: Raises `ObjectDoesNotExist` error (Django exception)
        """
        test_dict = {"name": 500}
        with self.assertRaises(ObjectDoesNotExist) as context:
            _get_or_create(Chromosome, "get", **test_dict)

    def test_gets_objects(self):
        """
        CASE: Submit a query against `Chromosome` for a chromosome that exists
        EXPECTS: Correct row of `Chromosome` data is returned. All fields match expectations
        """
        test_dict = {"name": 1}
        query_result = _get_or_create(Chromosome, "get", **test_dict)
        assert query_result.name == "1"
        assert query_result.numerical_name == 1
        assert query_result.source == "RefSeq"
=======
>>>>>>> 1a4f0d7022c8aad2b5aadb6781da355c5314e34b
