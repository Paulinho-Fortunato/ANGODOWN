import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32))
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    RATE_LIMIT_REQUESTS = 30
    RATE_LIMIT_WINDOW = 60
    DOWNLOAD_DIR = 'downloads'
    ALLOWED_FORMATS = ['mp3', '720', '1080']
    CACHE_TIMEOUT = 300
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = 'sessions'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['DOWNLOAD_DIR'], exist_ok=True)
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)