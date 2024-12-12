#!/bin/sh

#!/bin/sh

# Start the Flask app using Gunicorn
exec gunicorn -b 0.0.0.0:8080 gb_to_gcs:app

# Start the application with a timeout of 30 seconds
#timeout 30s python gb_to_gcs.py