# config.py

# --------------------
# Database configuration
# --------------------
DB_CONFIG = {
   "dbname": "ppmc_synergy",
   "user": "ppmc_synergy",
   "password": "ppmc_synergy",
  "host": "101.50.83.121",
   "port": 5432,
}

#--------------------
# Test Local Database 
#--------------------

# DB_CONFIG = {
#     "dbname": "ppmc_synergy",
#     "user": "postgres",
#     "password": "postgres",
#     'host': "localhost",
#     "port": 5432,
# }


# Hikvision credentials
# --------------------
HIK_USERNAME = "admin"
HIK_PASSWORD = "pepco@1234"

# --------------------
# Device URLs
# --------------------
DEVICE_URLS = [
    "http://192.168.18.35/ISAPI/AccessControl/AcsEvent?format=json",
    "http://192.168.18.36/ISAPI/AccessControl/AcsEvent?format=json",
]

# --------------------
# Full import start date
# --------------------
FULL_IMPORT_START_DATE = "2023-01-01"
