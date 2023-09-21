from django.test import TestCase

import pandas as pd

# Data sources: MANE, markname from HGMD, gene2refseq from HGMD

#TODO: transcript assigner cases:

# CASE gene (any transcript) is in gene_clinical_transcript already
# EXPECT the transcript to return as non-clinical

# CASE gene and transcript are both in MANE data
# EXPECT the transcript to return straight away as clinical, source = MANE,
# regardless of whether it's in other files or not

# CASE gene is in MANE data, but the transcript isn't a MANE one
# EXPECT the transcript to return straight away as non-clinical, source = None

