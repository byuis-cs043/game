-- File not used, just shows how the remote table is created

DROP TABLE IF EXISTS user;

CREATE TABLE user (
 name VARCHAR(64) NOT NULL PRIMARY KEY,
 password VARCHAR(64) NOT NULL
);
