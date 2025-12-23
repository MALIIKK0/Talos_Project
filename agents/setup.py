from dotenv import load_dotenv
import os   
load_dotenv()

SF_USERNAME = os.getenv("SF_USERNAME")
SF_PASSWORD = os.getenv("SF_PASSWORD")
SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN")
API_VERSION = os.getenv("SF_API_VERSION", "v65.0")  # adjust if needed