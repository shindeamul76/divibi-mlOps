import os
from dotenv import load_dotenv
import env_loader

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

environment = os.getenv('FLASK_ENV', 'development')
if environment == 'production':
    load_dotenv(os.path.join(basedir, '.env.prod'))
else:
    load_dotenv(os.path.join(basedir, '.env.dev'))

# print(os.environ.get('SQLALCHEMY_DATABASE_URI'), "database")

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')\
        or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
    AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
    AWS_REGION = os.environ.get('AWS_REGION')
    S3_BUCKET = os.environ.get('S3_BUCKET')


class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'