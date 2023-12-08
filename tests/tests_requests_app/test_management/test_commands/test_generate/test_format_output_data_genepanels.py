# from django.test import TestCase

# from requests_app.models import (
#     ReferenceGenome,
#     Gene,
#     Transcript,
#     TranscriptRelease,
#     TranscriptReleaseTranscript,
#     TranscriptSource,
# )
# from requests_app.management.commands.generate import Command


# class TestFormatOutputData(TestCase):
#         #     :param: ci_panels, a dict linking clinical indications to panels
#         # :param: panel_genes, a dict linking genes to panel IDs
#         # :param: rnas, a set of RNAs parsed from HGNC information

#     def test_straightforward_case(self):
#         ci_panels = {"R123.2": ["panel_3"], "R345": []}
#         panel_genes = {"panel_3": ["HGNC:1", "HGNC:2"]}
#         rnas = set(["HGNC:2", "HGNC:1"])
#         cmd = Command()
#         formatted = cmd._format_output_data_genepanels(ci_panels, panel_genes, rnas)
#         expected = [
#             ["R123.2", "panel_3", "HGNC:1"],
#             ["R123.2", "panel_3", "HGNC:2"]
#         ]
#         self.assertIsEqual(formatted, expected)
