"""All MySQL dependencies."""

import pymysql
import json


class DB:
    """Miscellaneous functions for checking username & password, fetching games, updating scores etc."""
    def __init__(self):
        self.connection = pymysql.connect(
            unix_socket='/var/run/mysqld/mysqld.sock',
            user='umpire', passwd='fda323rf', db='game'
        )

    def user_pass_valid(self, username, password):
        cursor = self.connection.cursor()
        cursor.execute('SELECT name FROM user WHERE name = %s AND password = %s', [username, password])
        if cursor.fetchone():
            return True
        else:
            return False

    def add_username(self, username, password):
        cursor = self.connection.cursor()
        cursor.execute('SELECT name FROM user WHERE name = %s', [username])
        if cursor.fetchone():
            return False
        else:
            cursor.execute('INSERT INTO user (name, password) VALUES (%s, %s)', [username, password])
            self.connection.commit()
            return True

    def dump(self):
        cursor = self.connection.cursor()

        cursor.execute('SELECT name, password FROM user')
        users = cursor.fetchall()

        return users

    def clear_tables(self):
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM user')
        self.connection.commit()
