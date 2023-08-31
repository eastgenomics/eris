# panel_requests

Abbreviations:
- CI: clinical indication
- PA: PanelApp (website at https://panelapp.genomicsengland.co.uk/)
- TD: NHS England National Genomic Test Directory (website at https://www.england.nhs.uk/publication/national-genomic-test-directories/)

Descriptions of the various gene and region metadata attributes can be found in the online PanelApp handbook at https://panelapp.genomicsengland.co.uk/media/files/PanelApp_Handbook_V18_120210506.pdf.

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
The generic command for this is:
```
python manage.py seed panelapp all
```
- This command retrieves all current panels from the PanelApp API, parses the data, and inserts it into the appropriate database models.
- It can be executed as-is and has no variable arguments.

### 2. Insert data from the National Genomic Test Directory
The generic command for this is:
```
python manage.py seed td <input_json>
```
- Example usage:
```
python manage.py seed td testing_files/230616_RD_TD_v5.json
```
- This command retrieves data from a JSON file, inserts it into the appropriate database models, and link the clinical indication to the appropriate Panel record as specified
- The JSON file can be created from the original test directory MS Excel file using https://github.com/eastgenomics/test_directory_parser, and take the following format:

```json
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
```

The argument for this command is:
- The name of the JSON file (which should be located within the same folder as the manage.py script)


### 3. Insert transcript data
The generic command for this is:
```
python manage.py seed transcript --hgnc <path> --mane <path> --gff <path> --g2refseq <path> --markname <path> --refgenome <ref_genome_version> --error
```
- Example usage:
```
python manage.py seed transcript --mane testing_files/mane_grch37.csv \
--hgnc testing_files/hgnc_dump_20230613.txt \
--gff testing_files/GCF_000001405.25_GRCh37.p13_genomic.exon_5bp_v2.0.0.tsv \
--g2refseq testing_files/gene2refseq_202306131409.csv \
--markname testing_files/markname_202306131409.csv \
--refgenome 37
```

## Create a request form
The generic command for this is:
```
python manage.py form <request_date> <requester> <ci_code> <hgnc_filename>
```
- Example usages:
```
# The CI links to a PanelApp panel which has both regions and genes
python manage.py form 20221201 user R149.1

# The CI links to a list of HGNC IDs
python manage.py form 20221201 user R417.2

# The CI links to nothing
python manage.py form 20221201 user R413.1
```

This command requires 4 arguments, the first 3 of which should come from the user request:
- Request date (in YYYYMMDD format)
- Requester initials
- The clinical indication R code
- The path to a text file dump of the HGNC database

To create the HGNC text file:
- Go to https://www.genenames.org/download/custom/
- In the first section, uncheck boxes so that only 'HGNC ID', 'Approved symbol', 'Previous symbols' and 'Alias symbols' are left ticked
- Scroll down and click 'submit'
- Copy the entire resulting text output (ctrl + A), and paste into a text editor
- Save as '<YYYYMMDD>_hgnc_dump.txt' in the same folder as the manage.py script

Executing the command will generate an MS Excel file named 'request_form_<req_date>_<ci_code>_<requester>.xlsx' in the same folder as the manage.py script.

The file consists of four pandas dataframes:
1. Generic information about the request (request date, clinical indication used, genome build used etc.)
2. Data on which panels are currently associated with that clinical indication
3. A list of the genes in these panels and their associated metadata (mode of inheritance, penetrance etc.)
4. A list of the regions in these panels and their associated metadata

More information about each metadata field can be found in the PanelApp handbook at https://panelapp.genomicsengland.co.uk/media/files/PanelApp_Handbook_V18_120210506.pdf

## Import a completed panel request form and update models
The generic command for this is:
``` 
python manage.py seed form <fp>
```
- Example usage:
``` 
python manage.py seed form request_form_20221201_R149.1_user.xlsx
```

The command takes 1 argument (fp) which is the path to the completed request form.

Executing the command reads in and parses a request form, creates a new panel instance from the request, links the relevant clinical indication to the new panel, and updates the link to the previous panel so that it is no longer current.


## Generate genepanel
```
Make a HGNC dump txt file here: https://www.genenames.org/download/custom/
Include columns:
- HGNC id
- Locus Type
- Approved Name

python manage.py genepanels --hgnc <hgnc dump path>
python manage.py generate genepanels --hgnc testing_files/hgnc_dump_23052023.txt --output /home/jason/github/eris/testing_files
```

## Generate g2t
This command required 5 files:
1. hgnc dump with HGNC ID, Approved symbol, Previous symbols and Alias symbols
2. mane.csv http://tark.ensembl.org/web/mane_GRCh37_list/
3. gff - download from DNAnexus (project-Fkb6Gkj433GVVvj73J7x8KbV:file-GF611Z8433Gk7gZ47gypK7ZZ)
4. g2refseq - table from HGMD db dump (in testing files)
5. markname - table from HGMD db dump (in testing files)
	
```
python manage.py seed transcript --hgnc <hgnc path> --mane <mane.csv path> --gff <gff.tsv path> --g2refseq <g2refseq.csv path> --markname <markname.csv path>
python manage.py seed transcript --hgnc <path to hgnc.txt> --mane <path to mane.csv> --gff <path to parsed gff.tsv> --g2refseq <path to g2refseq.csv from HGMD database> --markname <path to markname.csv from HGMD database>
```


# Running unit tests

Unit tests are stored in the 'tests' directory, and can be run through 'manage.py':
```
python manage.py test tests
```
Database-dependent tests use Django's unit testing library (based on unittest) to make, populate and tear down a temporary database based on models.py. Note that the test database will be named by prepending 'test_' to the value of the NAMEs in DATABASES.
