-- File not used, just shows how the remote tables are created

DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS game;
DROP TABLE IF EXISTS player;

CREATE TABLE user (
 name VARCHAR(64) NOT NULL PRIMARY KEY,
 password VARCHAR(64) NOT NULL
);

CREATE TABLE game (
 rowid INTEGER AUTO_INCREMENT PRIMARY KEY,
 players INTEGER,
 goal INTEGER,
 state INTEGER DEFAULT 0,
 ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 turns VARCHAR(4096) DEFAULT '[]'
);

CREATE TABLE player (
 rowid INTEGER AUTO_INCREMENT PRIMARY KEY,
 game_id INTEGER,
 user_name VARCHAR(64),
 score INTEGER DEFAULT 0,
 playing INTEGER DEFAULT 1,
 UNIQUE (game_id, user_name)
);
