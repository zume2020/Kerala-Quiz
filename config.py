import os
# For local env
# TOKEN = "TOKEN FROM BOTFATHER"
# DB_URI = "POSTGRES DATABASE URI"

# For Production
TOKEN = os.environ.get('TOKEN')
DB_URI = os.environ.get('DATABASE_URL')