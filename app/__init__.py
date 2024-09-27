from flask import Flask
import os

from config import Config
from dotenv import load_dotenv
from app.extensions import db
from flask_migrate import Migrate



import env_loader

def create_app(config_class=Config):

    app = Flask(__name__)
    app.config.from_object(config_class)

    # db.init_app(app)
    migrate = Migrate(app, db)

    # Initialize Flask extensions here
    db.init_app(app)


     # Import models and blueprints after initializing the app and db
    from app import models 


    # Register blueprints here
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.ai_model import bp as ai_model_bp
    app.register_blueprint(ai_model_bp, url_prefix='/ai-model')

     # Create database tables
    with app.app_context():
        db.create_all() 

    @app.route('/test/')
    def test_page():
        return '<h1>Testing the Flask Application Factory Pattern</h1>'

    return app