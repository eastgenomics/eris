# panel_requests

Abbreviations:
- CI: clinical indication
- PA: PanelApp (website at https://panelapp.genomicsengland.co.uk/)
- TD: NHS England National Genomic Test Directory (website at https://www.england.nhs.uk/publication/national-genomic-test-directories/)

## Create or update database models
Make any changes to the models.py file, then execute:
```sh
python manage.py makemigrations
python manage.py migrate
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
python manage.py seed p --panel_id all
```
- This command retrieves all current panels from the PanelApp API, parses the data, and inserts it into the appropriate database models.
- It can be executed as-is and has no variable arguments.

### 2. Insert data from the National Genomic Test Directory
The generic command for this is:
```sh
python manage.py seed d --td_json <filename> --td_current <Y/N>
```
- Example usage:
```sh
python manage.py seed d --td_json 220713_RD_TD.json --td_current Y
```
- This command retrieves data from a JSON file, inserts it into the appropriate database models, and links these to the appropriate panel data as specified within the test directory.
- The JSON file should be created from the original test directory MS Excel file and take the following format:
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
python manage.py create_form <request_date> <requester> <ci_code> <genome_build> <hgnc_filename>
```
- Example usages:
```sh
# The CI links to a PanelApp panel which has both regions and genes
python manage.py create_form 20220817 JJM R149.1 GRCh37 20220817_hgnc_dump.txt

# The CI links to a list of HGNC IDs
python manage.py create_form 20220817 JJM R417.2 GRCh37 20220817_hgnc_dump.txt

# The CI links to nothing
python manage.py create_form 20220817 JJM R413.1 GRCh37 20220817_hgnc_dump.txt
```

This command requires 5 arguments, the first 4 of which should come from the user request:
- Request date (in YYYYMMDD format)
- Requester initials
- The clinical indication R code
- The reference genome build to use (GRCh37 or GRCh38)
- The path to a text file dump of the HGNC database

To create the HGNC text file:
- Go to https://www.genenames.org/download/custom/
- In the first section, uncheck boxes so that only 'HGNC ID', 'Approved symbol', 'Previous symbols' and 'Alias symbols' are left ticked
- Scroll down and click 'submit'
- Copy the entire resulting text output (ctrl + A), and paste into a text editor
- Save as '<YYYYMMDD>_hgnc_dump.txt' in the same folder as the manage.py script

Executing the command will generate an MS Excel file named 'request_form_<req_date>-<ci_code>-<ref_genome>_<requester>.xlsx' in the same folder as the manage.py script.

The file consists of four pandas dataframes:
1. Generic information about the request (request date, clinical indication used, genome build used etc.)
2. Data on which panels are currently associated with that clinical indication
3. A list of the genes in these panels and their associated metadata (mode of inheritance, penetrance etc.)
4. A list of the regions in these panels and their associated metadata

More information about each metadata field can be found in the PanelApp handbook at https://panelapp.genomicsengland.co.uk/media/files/PanelApp_Handbook_V18_120210506.pdf
