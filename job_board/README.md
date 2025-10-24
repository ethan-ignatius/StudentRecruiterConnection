To load dummy jobs run the following (in the job board directory)
python manage.py migrate
python manage.py loaddata .\dummy_jobs.json

Has seeker1, seeker2, recruiter1, recruiter2, the password forall of them is 'Hellothere142857'

To clear all data run the following (in the job board directory)
python manage.py loaddata flush

or delete db.sqlite3 and run the following
python manage.py migrate

To Run the server run the following (in the job board directory)
python manage.py runserver