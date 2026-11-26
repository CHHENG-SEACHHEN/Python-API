import os
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

db_pool = pooling.MySQLConnectionPool(
    pool_name="bookstore_pool",
    pool_size=5,
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

def get_db():
    conn = db_pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()