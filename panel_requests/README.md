# panel_requests

To create or update database models:

python manage.py makemigrations
python manage.py migrate


To clear all records and models from an existing database:

sudo mysql
DROP DATABASE IF EXISTS panel_requests;
CREATE DATABASE panel_requests CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON panel_requests.* TO 'jay'@'localhost';
FLUSH PRIVILEGES;
exit
Then delete all migrations files in requests_app/migrations.


To populate the database:

1. Retrieve data on all current panels from PanelApp and insert:

python manage.py seed p --panel_id all

2. Retrieve data from a parsed json file of a test directory:

python manage.py seed d --td_json <filename> --td_current <Y/N>
