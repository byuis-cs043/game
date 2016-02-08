import sqlite3

connection = sqlite3.connect('game.db')

connection.execute('DROP TABLE IF EXISTS user')

connection.execute('''
CREATE TABLE user (
 name VARCHAR(64) NOT NULL PRIMARY KEY,
 password VARCHAR(64) NOT NULL
)
''')

connection.commit()
