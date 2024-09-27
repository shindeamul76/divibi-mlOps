# env_loader.py

import os
from dotenv import load_dotenv

# Get the base directory of the project
basedir = os.path.abspath(os.path.dirname(__file__))

# Determine which .env file to load based on the FLASK_ENV environment variable
environment = os.getenv('FLASK_ENV', 'development')

# Load the appropriate .env file
if environment == 'production':
    load_dotenv(os.path.join(basedir, '.env.prod'))
    print("Loaded .env.prod")
elif environment == 'testing':
    load_dotenv(os.path.join(basedir, '.env.test'))
    print("Loaded .env.test")
else:
    load_dotenv(os.path.join(basedir, '.env.dev'))
    print("Loaded .env.dev")
