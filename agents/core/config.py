import os
from dotenv import load_dotenv


load_dotenv()


SALESFORCE_API_KEY = os.getenv("SALESFORCE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")