"""All sqlite3 dependencies.

All sqlite3 dependent code is collected in this module. The rest of the game app will be isolated from direct
interaction with sqlite3. This makes it easy to replace sqlite3 with a different database. Only the code in this
module needs to be adapted for a different database. The rest of the app will work the same.
"""

import sqlite3
import json


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

    def get_game_by_id(self, game_id):
        cursor = self.connection.cursor()
        cursor.execute('SELECT players, goal, state, ts, turns FROM game WHERE rowid = ?', [game_id])
        return cursor.fetchone()

    def get_games_by_user(self, username):
        cursor = self.connection.cursor()
        cursor.execute(
            'SELECT game.rowid, players, goal, state, ts, turns '
            'FROM game, player '
            'WHERE player.game_id = game.rowid AND playing AND user_name = ? '
            'ORDER BY 1', [username]
        )
        return cursor.fetchall()

    def get_registering_games_by_user(self, username):
        cursor = self.connection.cursor()
        cursor.execute(
            'SELECT game_id, players, goal, ts, turns FROM game, ('
            ' SELECT rowid game_id FROM game WHERE state = 0 AND rowid NOT IN ('
            '  SELECT game.rowid FROM game, player'
            '  WHERE state = 0 AND game.rowid = player.game_id AND player.user_name = ?'
            ' )'
            ') registering '
            'WHERE game.rowid = registering.game_id '
            'ORDER BY 1 DESC', [username]
        )
        return cursor.fetchall()

    def new_game(self, players, goal, username):
        cursor = self.connection.cursor()
        cursor.execute('INSERT INTO game (players, goal) VALUES (?, ?);', [players, goal])
        cursor.execute('INSERT INTO player (game_id, user_name) VALUES (last_insert_rowid(), ?)', [username])
        self.connection.commit()

    def join_game(self, game_id, username):
        game = self.get_game_by_id(game_id)
        if not game:
            print("Unknown game")
            return

        max_players, goal, state, ts, turns = game
        if state > 0:
            print("Game full")
            return

        cursor = self.connection.cursor()
        cursor.execute('INSERT INTO player (game_id, user_name) VALUES (?, ?)', [game_id, username])
        cursor.execute('SELECT count(*) FROM player WHERE game_id = ?', [game_id])
        (players_in_game,) = cursor.fetchone()
        if players_in_game == max_players:  # Players filled
            cursor.execute('UPDATE game SET state = 1, ts = datetime() WHERE rowid = ?', [game_id])
            self.connection.commit()
        elif players_in_game < max_players:  # Waiting more players
            cursor.execute('UPDATE game SET ts = datetime() WHERE rowid = ?', [game_id])
            self.connection.commit()
        elif players_in_game > max_players:  # Too many players
            self.connection.rollback()

    def updated_games(self, username):
        cursor = self.connection.cursor()
        cursor.execute(  # Find latest timestamps of players' game joins, quits, moves where user himself has not quit
            'SELECT max(ts) FROM game, player '
            'WHERE player.user_name = ? AND player.playing AND player.game_id = game.rowid ', [username])
        (latest_timestamp_of_running_games,) = cursor.fetchone()
        cursor.execute(  # Latest timestamps of games waiting for registrations
            'SELECT max(ts) FROM game, ('
            ' SELECT rowid game_id FROM game WHERE state = 0 AND rowid NOT IN ('
            '  SELECT game.rowid FROM game, player'
            '  WHERE state = 0 AND game.rowid = player.game_id AND player.user_name = ?'
            ' )'
            ') registering '
            'WHERE game.rowid = registering.game_id', [username]
        )

        (latest_timestamp_of_registering_games,) = cursor.fetchone()
        return latest_timestamp_of_running_games, latest_timestamp_of_registering_games

    def quit_game(self, game_id, username):
        cursor = self.connection.cursor()
        cursor.execute(
            'SELECT state FROM player, game '
            'WHERE player.user_name = ?'
            ' AND player.game_id = game.rowid'
            ' AND game.rowid = ?',
            [username, game_id]
        )
        game = cursor.fetchone()
        if not game:
            print('Player not found in game')
            return

        (game_state,) = game

        if game_state == 0:  # Still registering players
            cursor.execute('DELETE FROM player WHERE user_name = ? AND game_id = ?', [username, game_id])
            cursor.execute('SELECT count(*) FROM player WHERE game_id = ?', [game_id])
            (remaining_players,) = cursor.fetchone()
            if remaining_players > 0:
                cursor.execute('UPDATE game SET ts = datetime() WHERE rowid = ?', [game_id])
            else:
                cursor.execute('DELETE FROM game WHERE rowid = ?', [game_id])
                # Minor prob: Reg list will not update if a newer game is in the list
            self.connection.commit()
        else:
            cursor.execute(
                'UPDATE player SET playing = 0 WHERE user_name = ? AND game_id = ?', [username, game_id]
            )
            cursor.execute('UPDATE game SET ts = datetime() WHERE rowid = ?', [game_id])
            self.connection.commit()

    def dump(self):
        cursor = self.connection.cursor()

        cursor.execute('SELECT name, password FROM user')
        users = cursor.fetchall()

        cursor.execute('SELECT rowid, players, goal, state, ts, turns FROM game')
        games = cursor.fetchall()

        cursor.execute('SELECT rowid, game_id, user_name, score, playing FROM player')
        players = cursor.fetchall()

        return users, games, players

    def clear_tables(self, clear_all):
        cursor = self.connection.cursor()
        if clear_all:
            cursor.execute('DELETE FROM user')
        cursor.execute('DELETE FROM game')
        cursor.execute('DELETE FROM player')
        self.connection.commit()


class Game:
    """Base functionality for game classes."""
    def __init__(self, game_id, num_players, goal, state, ts, turns, connection):
        """Initialize game object with state and load players and scores from database."""
        self.id = game_id
        self.num_players = num_players
        self.goal = goal
        self.state = state  # 0={Registering players}, 1={Game on}, 2={Game over}
        self.ts = ts
        self.turns = json.loads(turns)

        self.connection = connection
        cursor = connection.cursor()
        cursor.execute('SELECT user_name, score, playing FROM player WHERE game_id = ? ORDER BY rowid', [game_id])
        self.players = [{'name': n, 'score': s, 'playing': p} for n, s, p in cursor.fetchall()]

    def player_index(self, username):
        """Return player's index in player list

        :param username: Name of the user to find index for
        :return: int
        """
        return [p['name'] for p in self.players].index(username)

    def save_score_for_player(self, index):
        """Save player's score.

        :param index: Position of player in Game's player list
        """
        player = self.players[index]
        cursor = self.connection.cursor()
        cursor.execute(
            'UPDATE player SET score = ? '
            'WHERE user_name = ? AND game_id = ?', [player['score'], player['name'], self.id])
        # Commit in save_game_state()

    def set_game_over(self):
        """Set game status to game over."""
        self.state = 2  # Game over
        cursor = self.connection.cursor()
        cursor.execute('UPDATE game SET state = 2 WHERE rowid = ?', [self.id])
        # Commit in save_game_state()

    def save_game_state(self):
        """Save game state to database."""
        cursor = self.connection.cursor()
        cursor.execute(
            'UPDATE game SET turns = ?, ts = datetime() '
            'WHERE rowid = ?', [json.dumps(self.turns), self.id])
        self.connection.commit()
        cursor = self.connection.cursor()
        cursor.execute('SELECT ts FROM game WHERE rowid = ?', [self.id])
        self.ts = cursor.fetchone()[0]
