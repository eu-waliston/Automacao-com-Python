# .env file
API_KEY=""
DB_PASSWORD=""

# Uso
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("API_KEY")
