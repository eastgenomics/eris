# Eris: Django apps for panel management and variant storage

## Note
Eris is currently still in active pre-release development, as of 23rd January 2024.


## Purpose
Eris is a tool with two broad functionalities:
1. The 'panels' apps (panels_backend and panels_web) store panels, clinical indications, genes and transcripts in a PostgreSQL database. A command line interface lets the user populate and bulk-update the database from files, and download the information as up-to-date files for downstream pipelines. In addition, a web interface allows easy viewing of the database contents, and lets users add custom panels, or carry out manual approval for some database changes.
  Note that as of 23rd January 2024, the 'panels' apps can be used without the 'variant_db' functionality.
2. The 'variant_db' app allows storage of clinical interpretations, and ultimately, to streamline submission of interpreted variants to ClinVar.

A shared database is used for the two apps.


## Intended environment
Eris requires Python version 3.10. It is designed to run in Docker containers running Ubuntu base images, on a local bioinformatics server using RHEL as its operating system. It needs to be connected to a PostgreSQL database. You also need to be connected to the internet, in order to access the PanelApp API.


## Abbreviations:
- CLI: command line interface
- CI: clinical indication
- PA: PanelApp (website at https://panelapp.genomicsengland.co.uk/)
- TD: NHS England National Genomic Test Directory (website at https://www.england.nhs.uk/publication/national-genomic-test-directories/)

Descriptions of the various gene metadata attributes can be found in the online PanelApp handbook at https://panelapp.genomicsengland.co.uk/media/files/PanelApp_Handbook_V18_120210506.pdf.


## Overview of components
Eris' components are:
- core: contains some basic app settings, common to both the 'panels' and 'variant_db' apps
- panels_backend:
  - Includes the 'panels' database models, in models.py, from which a PostgreSQL database can be populated with tables.
  - Provides the 'panels' command line interface and associated processing scripts, in management/commands
- panels_web: 
  - Controls the 'panels' web 'front-end' interface, which allows scientists to view the clinical indications (CIs), panels, genes, transcripts, and their histories; add custom panels; and review more-complex changes to the database which need human approval 
  - For example, when a panel version is updated in PanelApp, Eris automatically linked to the same clinical indication used for the old panel version. However, this change is marked as 'pending' until a user approves it.
- nginx: basic nginx (forward-proxy) configurations
- variant_db:
  - Includes variant interpretation-specific database models, in models.py, from which a PostgreSQL database can be populated.
  - Provides the command line interface and scripts to enable population of parsed CSV variant interpretations, in management/commands


## Setup
### Create or update database models
First, create a PostgreSQL database for Eris to connect to.
Then, make migrations if necessary, and migrate changes to the existing database.
For the 'panels' functionality:
```
python manage.py makemigrations panels_backend
python manage.py migrate panels_backend
```
If planning to use the 'variant_db' functionality, the add-on models must also be migrated:
```
python manage.py makemigrations variant_db
python manage.py migrate variant_db
```


## Using the 'panels' functionality

### Populate/update the database from CLI
#### 1. Insert data from PanelApp
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

  
#### 2. Insert data from the National Genomic Test Directory
Before it can be used in Eris panels, the National Genomic Test Directory's spreadsheet file must be converted to JSON format. To do this, we pre-check it using the separate 'test_directory_checker', make any required changes, and then convert it with the 'test_directory_parser' projects, which are available in GitHub:
* https://github.com/eastgenomics/test_directory_checker
* https://github.com/eastgenomics/test_directory_parser

Once the test directory is converted to an input JSON, it can be used to populate the Eris database with the following command:
```
python manage.py seed td <input_json> --td_release <td_release>
```
- Example usage:
```
python manage.py seed td testing_files/eris/230616_RD_TD_v5.json --td_release 5
```
- This command inserts the JSON data into the appropriate database models, and links the clinical indication to the appropriate Panel record as specified
- The JSON file will look similar to this:

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
  - An example of TD JSON file can be found under `testing_files/eris/`
- The version of the test directory release, e.g., 5.


#### 3. Seed transcript

Adds transcripts to the database, for either GRCh37 or GRCh38. The possible transcripts are provided in a GFF file. Note that if you use VEP in your pipelines, you should ensure you provide the file compatible with your current version of VEP.

MANE and HGMD files are used to assign transcripts as being the 'default' clinical or non-clinical for each gene. The MANE file for GRCh37 is a CSV file downloaded from Transcript Archive http://tark.ensembl.org/web/mane_GRCh37_list/) and the HGMD files are CSV files of the 'markname' and 'g2refseq' tables, generated when the HGMD database is dumped.  

MANE and HGMD files should be version-controlled locally, with file IDs for every file, a release version for MANE, and a release version for HGMD. These are provided as string arguments during transcript seeding. Then, each transcript will be linked to the MANE/HGMD releases which informed the 'clinical/non-clinical' decision.

```
python manage.py seed transcript \
--hgnc <path> --hgnc_release <release> --mane <path> --mane_ext_id <file ID> --mane_release <release> \
--gff <path> --gff_release <release> --g2refseq <path> --g2refseq_ext_id <file ID> --markname <path> \
--markname_ext_id <file ID> --hgmd_release <str> --refgenome <version> \
--error

# working example
python manage.py seed transcript --hgnc testing_files/eris/hgnc_dump_20230613.txt --hgnc_release 1.0 --mane testing_files/eris/mane_grch37.csv --mane_ext_id file-123 --mane_release 1.0 --gff testing_files/eris/GCF_000001405.25_GRCh37.p13_genomic.exon_5bp_v2.0.0.tsv --gff_release 19 --g2refseq testing_files/eris/gene2refseq_202306131409.csv --g2refseq_ext_id file-123 --markname testing_files/eris/markname_202306131409.csv --markname_ext_id file-234 --hgmd_release 1.4 --refgenome grch37
```

The arguments are as follows:
- `hgnc`: path to HGMC dump txt file, allowing gene names to be standardised. The file is CSV format and contains columns for HGNC ID, Approved Symbol, Previous Symbols, Alias Symbols. This file should be documented with a release version. An example HGNC file can be downloaded from: https://www.genenames.org/download/custom/
- `hgnc_release`: the documented release version for the `hgnc` file. This must consist only of numbers and full stops, e.g. 1.0.1.
- `mane`: path to MANE CSV file, which informs which transcripts are labelled as clinical. This file should be documented with a release version. An example GRCh37 file is available at: http://tark.ensembl.org/web/mane_GRCh37_list/
- `mane_ext_id`: the external file ID for the release-tagged MANE CSV file
- `mane_release`: the release version associated with the MANE CSV file and its file ID. This must consist only of numbers and full stops, e.g. 1.0.1.
- `gff`: path to parsed gff.tsv (project-Fkb6Gkj433GVVvj73J7x8KbV:file-GF611Z8433Gk7gZ47gypK7ZZ)
- `gff_release`: the documented release version for the `gff` file you are providing for transcript annotations. This must consist only of numbers and full stops. It is recommended that you use the Ensembl release, and if you use VEP in your pipeline, you should select a release compatible with your currently-used VEP version.
- `g2refseq`: path to the g2refseq table from the HGMD database, in csv format
- `g2refseq_ext_id`: external file ID for release-tagged HGMD g2refseq table
- `markname`: path to markname table from the HGMD database, in csv format
- `markname_ext_id`: external file ID for versioned HGMD markname table
- `hgmd_release`: the release version of HGMD, associated with both markname and g2refseq. This must consist only of numbers and full stops, e.g. 1.0.1.
- `refgenome`: reference genome. Permitted values are: 37/GRCh37/hg19 or 38/GRCh38/hg38

*HGMD database source can be found on DNAnexus (project-Fz4Q15Q42Z9YjYk110b3vGYQ:file-Fz4Q46842Z9z2Q6ZBjy7jVPY)


### Generating outputs from CLI
A series of output 'dump files' can be created from the contents of the Eris database, using the command line.

#### Generate a genepanel file

Generates a text file which represents each gene in a panel or superpanel, with that panel/superpanel's linked clinical indication, on a separate line. Genes are only output if they are in panels/superpanel which currently have an active link to a clinical indication.

A HGNC file is required to run 'generate genepanels'.
Make a HGNC dump txt file here: https://www.genenames.org/download/custom/
Include the following columns:
- HGNC ID
- Locus Type
- Approved Name

To run without a specified output pathway (note that this will create the file in your current working directory):
```
python manage.py generate genepanels --hgnc testing_files/eris/hgnc_dump_20230606_1.txt
```
To run with a specified output pathway:
```
python manage.py generate genepanels --hgnc testing_files/eris/hgnc_dump_20230606_1.txt --output <output_path>
```

#### Generate a g2t file

Generates a text file which represents every transcript linked to the user-selected reference genome in the Eris database, alongside its linked gene, with a column displaying whether the transcript is the 'clinical transcript' for that gene (True), whether it's not clinical for that gene (False), or whether it's not present in the most up-to-date versions of the transcript sources (None). Currently, the sources used to assign clinical status in Eris are MANE Select, MANE Plus Clinical and HGMD.

Provide the reference genome as a string input. GRCh37 and GRCh38 are the currently-available options. 

To run generate g2t without a specified output pathway (note that this will create the file in your current working directory):
```
python manage.py generate g2t --ref_genome <ref_genome> --gff_release <gff_release>

- `ref_genome`: the name of your reference genome build. Currently permitted values are: 37/GRCh37/hg19 or 38/GRCh38/hg38

- `gff_release`: the documented release version for the `gff` file you are providing for transcript annotations. This must consist only of numbers and full stops. It is recommended that you use an Ensembl release version which is compatible with your chosen reference genome. If you use VEP in your pipeline, you should select a release compatible with your currently-used VEP version. 

```
To run with a specified output pathway:
```
python manage.py generate g2t --ref_genome <ref_genome> --gff_release <gff_release> --output <output pathway>
```

### Edit links between panel-related tables
#### Edit a clinical indication - panel interaction

If an automatically-generated clinical indication/panel link needs to be manually approved (activated or deactivated) this can be done in the web interface, or instead, via the CLI:
```
python manage.py edit <--panel_id or --panel_name> <panel id or panel name> <--clinical_indication_id or --clinical_indication_r_code> <r code or clinical indication id> <activate/deactivate>

e.g. python manage.py edit --panel_id 26 --clinical_indication_id 1 deactivate

NOTE: panel_name is case-insensitive
```

## Using the 'variant_db' functionality

As of 23rd January 2024, this functionality is still in very early development.
More information will be added as it nears completion.


## For developers: Running Unit Tests

Unit tests are stored in the 'tests' directory, and can be run via the 'manage.py' script:
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