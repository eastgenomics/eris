# panel_requests

Abbreviations:
- CI: clinical indication
- PA: PanelApp (website at https://panelapp.genomicsengland.co.uk/)
- TD: NHS England National Genomic Test Directory (website at https://www.england.nhs.uk/publication/national-genomic-test-directories/)

Descriptions of the various gene and region metadata attributes can be found in the online PanelApp handbook at https://panelapp.genomicsengland.co.uk/media/files/PanelApp_Handbook_V18_120210506.pdf.

## Create or update database models
Make any changes to the models.py file, then execute:
```sh
python manage.py makemigrations requests_app
python manage.py migrate requests_app
```

## Clear all records and models from an existing database
This involves executing several MySQL commands:
```sh
sudo mysql
DROP DATABASE IF EXISTS panel_requests;
CREATE DATABASE panel_requests CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON panel_requests.* TO 'user'@'localhost';
FLUSH PRIVILEGES;
exit
```
Then delete all pre-existing migrations files in requests_app/migrations (but make sure you leave the init.py files).

## Populate the database
### 1. Insert data from PanelApp
The generic command for this is:
```sh
python manage.py seed panels all
```
- This command retrieves all current panels from the PanelApp API, parses the data, and inserts it into the appropriate database models.
- It can be executed as-is and has no variable arguments.

### 2. Insert data from the National Genomic Test Directory
The generic command for this is:
```sh
python manage.py seed test_dir <input_json> <Y/N>
```
- Example usage:
```sh
python manage.py seed test_dir 220713_RD_TD.json Y
```
- This command retrieves data from a JSON file, inserts it into the appropriate database models, and links these to the appropriate panel data as specified within the test directory.
- The JSON file can be created from the original test directory MS Excel file using https://github.com/eastgenomics/test_directory_parser, and take the following format:
```sh
{
directory_version_name,
directory_version_date,
clinical_indications : [
	{
	ci_code,
	ci_name,
	gemini_name,
	panels : [panel_id_1, panel_id_2, ... , panel_id_N],
	}
	{ci_2},
	...
	{ci_N},
	],
}
```
The two arguments for this command are:
- The name of the JSON file (which should be located within the same folder as the manage.py script)
- Y/N to specify whether this is the current version of the test directory

## Create a request form
The generic command for this is:
```sh
python manage.py create_form <request_date> <requester> <ci_code> <hgnc_filename>
```
- Example usages:
```sh
# The CI links to a PanelApp panel which has both regions and genes
python manage.py create_form 20221201 user R149.1 20221201_hgnc_dump.txt

# The CI links to a list of HGNC IDs
python manage.py create_form 20221201 user R417.2 20221201_hgnc_dump.txt

# The CI links to nothing
python manage.py create_form 20221201 user R413.1 20221201_hgnc_dump.txt
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
``` sh
python manage.py seed form <fp>
```
- Example usage:
``` sh
python manage.py seed form request_form_20221201_R149.1_user.xlsx
```

The command takes 1 argument (fp) which is the path to the completed request form.

Executing the command reads in and parses a request form, creates a new panel instance from the request, links the relevant clinical indication to the new panel, and updates the link to the previous panel so that it is no longer current.

## Running unit tests
Unit tests are defined in requests_app/tests.py, and can be run from within the top-level panel_requests directory.

- Example usages:
```sh
# Basic execution
pytest

# Output is quiet or verbose
pytest -q
pytest -v

# Output includes line coverage
pytest --cov=panel_requests panel_requests/requests_app/tests.py
```
## Generate genepanel tsv
```
Make a HGNC dump txt file here: https://www.genenames.org/download/custom/
Include columns:
- HGNC id
- Locus Type
- Approved Name

python manage.py generate genepanels --hgnc testing_files/hgnc_dump_23052023.txt --output /home/jason/github/eris/testing_files
```

# Get Started
```
python manage.py migrate requests_app
python manage.py seed panelapp all

```

# Seed Function
`python manage.py seed <panelapp/panel-id> <all/1.0>`
`python manage.py seed td <path to td json file> <Y/N>`
`python manage.py seed transcript --hgnc <path to hgnc.txt> --mane <path to mane.csv> --gff <path to parsed gff.tsv> --g2refseq <path to g2refseq.csv from HGMD database> --markname <path to markname.csv from HGMD database>`
