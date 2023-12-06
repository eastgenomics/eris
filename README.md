# panel_requests

Abbreviations:
- CI: clinical indication
- PA: PanelApp (website at https://panelapp.genomicsengland.co.uk/)
- TD: NHS England National Genomic Test Directory (website at https://www.england.nhs.uk/publication/national-genomic-test-directories/)

Descriptions of the various gene metadata attributes can be found in the online PanelApp handbook at https://panelapp.genomicsengland.co.uk/media/files/PanelApp_Handbook_V18_120210506.pdf.

# Python
Please note this app requires Python version 3.10

# Setup
## Create or update database models
Make migrations if necessary and migrate to existing database.
```
python manage.py makemigrations requests_app
python manage.py migrate requests_app
```

## Populate the database
### 1. Insert data from PanelApp
You can choose to seed all panels, or to seed specified panels by their PanelApp IDs.
Note that panels can be either standard panels, or superpanels. Superpanels are collections of standard panels, and contain all the genes contained by each of those standard panels.

To seed all panels, the generic command is:
```
python manage.py seed panelapp all
```
- This command retrieves all signed-off panels and superpanels from the PanelApp API, parses the data, and inserts it into the appropriate database models.
- For each signed-off superpanel, the most recently signed-off version of every child panel will also be retrieved.
- It can be executed as-is and has no variable arguments.

To seed specified versions of panels, the command is:
```
python manage.py seed panelapp <panel or superpanel id> <panel or superpanel version>
```
- The version argument is optional.
- If you provide a version:
  - For a standard panel: that particular user-specified version of the panel will be fetched from PanelApp. Note that you can add a non-signed-off version of a panel in this way.
  - This option is NOT AVAILABLE for superpanels, which will raise an error and cancel.
- If you don't provide a version:
  - For Panels, the most-recent version is retrieved, regardless of whether or not it is the latest signed-off version.
  - For Superpanels, the most-recent SIGNED OFF version is retrieved. In addition, the most recent signed-off versions of its child panels are retrieved.

  
### 2. Insert data from the National Genomic Test Directory
The generic command for this is:
```
python manage.py seed td <input_json> --td_release <td_release>
```
- Example usage:
```
python manage.py seed td testing_files/230616_RD_TD_v5.json --td_release 5
```
- This command retrieves data from an output JSON file generated by "test directory parser", inserts the data into the appropriate database models, and link the clinical indication to the appropriate Panel record as specified
- The JSON file can be created from the original test directory MS Excel file using https://github.com/eastgenomics/test_directory_parser, and take the following format:

```json
{
  "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.1.xlsx",
  "config_source": "230401_RD",
  "date": "230616",
  "indications": [
    {
      "name": "Monogenic hearing loss",
      "code": "R67.1",
      "gemini_name": "R67.1_Monogenic hearing loss_P",
      "test_method": "WES or Large Panel",
      "panels": [
        "126"
      ],
      "original_targets": "Hearing loss (126)",
      "changes": "No change"
    },
  ]
}
```

The arguments for this command are:
- The name of the JSON file (which should be located within the same folder as the manage.py script)
  - An example of TD JSON file can be found under `testing_files/`
- The version of the test directory release, e.g., 5.


### 3. Seed transcript

Adds transcripts to the database for either GRCh37 or GRCh38. 
MANE and HGMD files are used to assign transcripts as 'default' clinical or non-clinical for each gene - though this can be over-ridden for specific panels, where a non-default transcript is more clinically appropriate. The MANE file for GRCh37 is a CSV file downloaded from Transcript Archive http://tark.ensembl.org/web/mane_GRCh37_list/) and the HGMD files are CSV files of the 'markname' and 'g2refseq' tables, generated when the HGMD database is dumped.
MANE and HGMD files should be version-controlled locally, with file IDs for every file, a release version for MANE, and a release version for HGMD. These are provided as string arguments during transcript seeding. Then, each transcript will be linked to the MANE/HGMD releases which informed the 'clinical/non-clinical' decision.

```
python manage.py seed transcript \
--hgnc <path> --hgnc_release <release> --mane <path> --mane_ext_id <file ID> --mane_release <release> \
--gff <path> --gff_release <release> --g2refseq <path> --g2refseq_ext_id <file ID> --markname <path> \
--markname_ext_id <file ID> --hgmd_release <str> --refgenome <version> \
--error

# working example
python manage.py seed transcript --hgnc testing_files/hgnc_dump_20230613.txt --hgnc_release 1.0 --mane testing_files/mane_grch37.csv --mane_ext_id file-123 --mane_release 1.0 --gff testing_files/GCF_000001405.25_GRCh37.p13_genomic.exon_5bp_v2.0.0.tsv --gff_release 1.0 --g2refseq testing_files/gene2refseq_202306131409.csv --g2refseq_ext_id file-123 --markname testing_files/markname_202306131409.csv --markname_ext_id file-234 --hgmd_release 1.4 --refgenome grch37
```

The arguments are as follows:
- `hgnc`: path to HGMC dump txt file, allowing gene names to be standardised. The file is CSV format and contains columns for HGNC ID, Approved Symbol, Previous Symbols, Alias Symbols. This file should be documented with a release version. An example HGNC file can be downloaded from: https://www.genenames.org/download/custom/
- `hgnc_release`: the documented release version for the `hgnc` file. This must consist only of numbers and full stops, e.g. 1.0.1.
- `mane`: path to MANE CSV file, which informs which transcripts are labelled as clinical. This file should be documented with a release version. An example GRCh37 file is available at: http://tark.ensembl.org/web/mane_GRCh37_list/
- `mane_ext_id`: the external file ID for the release-tagged MANE CSV file
- `mane_release`: the release version associated with the MANE CSV file and its file ID. This must consist only of numbers and full stops, e.g. 1.0.1.
- `gff`: path to parsed gff.tsv (project-Fkb6Gkj433GVVvj73J7x8KbV:file-GF611Z8433Gk7gZ47gypK7ZZ)
- `gff_release`: the documented release version for the `gff` file. This must consist only of numbers and full stops, e.g. 1.0.1.
- `g2refseq`: path to the g2refseq table from the HGMD database, in csv format
- `g2refseq_ext_id`: external file ID for release-tagged HGMD g2refseq table
- `markname`: path to markname table from the HGMD database, in csv format
- `markname_ext_id`: external file ID for versioned HGMD markname table
- `hgmd_release`: the release version of HGMD, associated with both markname and g2refseq. This must consist only of numbers and full stops, e.g. 1.0.1.
- `refgenome`: reference genome. Permitted values are: 37/GRCh37/hg19 or 38/GRCh38/hg38

*HGMD database source can be found on DNAnexus (project-Fz4Q15Q42Z9YjYk110b3vGYQ:file-Fz4Q46842Z9z2Q6ZBjy7jVPY)


# Generating outputs
## Generate genepanel
```
Make a HGNC dump txt file here: https://www.genenames.org/download/custom/
Include columns:
- HGNC id
- Locus Type
- Approved Name

Without output pathway specified:
```
python manage.py generate genepanels --hgnc testing_files/hgnc_dump_20230606_1.txt
```
With output pathway specified:
``````
python manage.py generate genepanels --hgnc testing_files/hgnc_dump_20230606_1.txt --output <output pathway>
```

## Generate g2t	
Without output pathway specified:
```
python manage.py generate g2t --ref_genome GRCh37
```
With output pathway specified:
```
python manage.py generate g2t --ref_genome GRCh37 --output <output pathway>
```

# Running unit tests

Unit tests are stored in the 'tests' directory, and can be run through 'manage.py':
```
python manage.py test
```
Database-dependent tests use Django's unit testing library (based on unittest) to make, populate and tear down a temporary database based on models.py. Note that the test database will be named by prepending 'test_' to the value of the NAMEs in DATABASES.

If you want to generate a coverage report, run:
```
coverage run --source="." manage.py test
```
You can view a coverage overview with:
```
coverage report
```
Or for a more-detailed, per-line breakdown of coverage, use:
```
coverage html
```