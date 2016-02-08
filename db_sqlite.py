"""All sqlite3 dependencies.

All sqlite3 dependent code is collected in this module. The rest of the game app will be isolated from direct
interaction with sqlite3. This makes it easy to replace sqlite3 with a different database. Only the code in this
module needs to be adapted for a different database. The rest of the app will work the same.
"""

import sqlite3


class DB:
    """Miscellaneous functions for checking username & password, fetching games, updating scores etc."""
    def __init__(self):
        self.connection = sqlite3.connect('game.db')

    def user_pass_valid(self, username, password):
        cursor = self.connection.cursor()
        cursor.execute('SELECT name FROM user WHERE name = ? AND password = ?', [username, password])
        if cursor.fetchone():
            return True
        else:
            return False

    def add_username(self, username, password):
        cursor = self.connection.cursor()
        cursor.execute('SELECT name FROM user WHERE name = ?', [username])
        if cursor.fetchone():
            return False
        else:
            cursor.execute('INSERT INTO user (name, password) VALUES (?, ?)', [username, password])
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
