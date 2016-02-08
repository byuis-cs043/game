import sqlite3

connection = sqlite3.connect('game.db')

connection.execute('DROP TABLE IF EXISTS user')
connection.execute('DROP TABLE IF EXISTS game')
connection.execute('DROP TABLE IF EXISTS player')

connection.execute('''
CREATE TABLE user (
 name VARCHAR(64) NOT NULL PRIMARY KEY,
 password VARCHAR(64) NOT NULL
)
''')

connection.execute('''
CREATE TABLE game (
 players INTEGER,
 goal INTEGER,
 state INTEGER DEFAULT 0,
 ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 turns VARCHAR(4096) DEFAULT '[]'
)
''')

connection.execute('''
CREATE TABLE player (
 game_id INTEGER,
 user_name VARCHAR(64),
 score INTEGER DEFAULT 0,
 playing INTEGER DEFAULT 1,
 UNIQUE (game_id, user_name)
)
''')

connection.commit()
