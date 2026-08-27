import os
import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "db"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "eduanimate"),
        password=os.getenv("MYSQL_PASSWORD", "eduanimate_dev"),
        database=os.getenv("MYSQL_DATABASE", "eduanimate"),
        autocommit=False,
    )
