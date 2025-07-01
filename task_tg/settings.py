import os

db_user = os.getenv("POSTGRES_DB")
db_name = os.getenv("POSTGRES_DB")
db_password = os.getenv("POSTGRES_PASSWORD")
db_host = os.getenv("POSTGRES_HOST")
db_port = os.getenv("POSTGRES_PORT", default=5432)

