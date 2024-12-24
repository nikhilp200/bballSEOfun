import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    COHERE_API_KEY = os.getenv('COHERE_API_KEY')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')