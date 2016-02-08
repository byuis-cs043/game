"""Skeleton for Pyramid game

The code below is still the same as for Rock-Paper-Scissors.
Modify to implement the Pyramid game.
"""

from db_sqlite import Game


class Pyramid(Game):
    def valid_moves(self, username):
        """Return list of pairs with valid moves for this player and how to display them.

        For example [('r', 'Rock'), ('p', 'Paper'), ('s', 'Scissors')]
        :param username: The moves valid for this user
        :return: List of pairs
        """
        return [('r', 'Rock'), ('p', 'Paper'), ('s', 'Scissors')]

    def add_player_move(self, username, move):
        """Add a new move by a player to the game.

        :param username: Username of player who moves
        :param move: One of the strings 'r', 'p', 's'
        """
        # Discard move if Game not in play (i.e. state != 1), or the move is not r(ock), p(aper) or s(cissors)
        if self.state != 1 or move not in ('r', 'p', 's'):
            return

        # Find the index (position) of this player in the list of players in the game.
        # In the case of RPS games this value will be 0 or 1 since RPS always has 2 players.
        index = self.player_index(username)

        # If there are no game rounds yet, or the last one is complete
        if not self.turns or not [None for m in self.turns[-1] if m is None]:  # No turns or last complete
            new_turn = [None] * len(self.players)
            new_turn[index] = move
            self.turns.append(new_turn)
            self.save_game_state()

        # If opponent(s) moved in last round but user has not
        elif self.turns[-1][index] is None:
            last_turn = self.turns[-1]
            last_turn[index] = move
            # Check if turn is complete and if so calculate scores
            if not [None for m in last_turn if m is None]:
                if last_turn in (['p', 'r'], ['s', 'p'], ['r', 's']):
                    self.players[0]['score'] += 1
                    self.save_score_for_player(0)
                    if self.players[0]['score'] == self.goal:
                        self.set_game_over()
                elif last_turn in (['r', 'p'], ['p', 's'], ['s', 'r']):
                    self.players[1]['score'] += 1
                    self.save_score_for_player(1)
                    if self.players[1]['score'] == self.goal:
                        self.set_game_over()
            self.save_game_state()

    def decorated_moves(self, username):
        """Return a list of moves with formatting information.

        :param username: Player's username
        :return: Formatted list of moves
        """
        if not self.turns:
            return []

        last_turn = self.turns[-1]
        if [None for m in last_turn if m is None]:  # Everybody has not yet moved in last turn, it is incomplete
            incomplete_last_turn = last_turn
            complete_turns = self.turns[:-1]
        else:
            incomplete_last_turn = None
            complete_turns = self.turns

        translate = {'r': 'Rock', 'p': 'Paper', 's': 'Scissors'}
        decorated_turns = []

        for turn in complete_turns:
            if turn in (['p', 'r'], ['s', 'p'], ['r', 's']):
                decorated_turns.append([(translate[turn[0]], True), (translate[turn[1]], False)])
            elif turn in (['r', 'p'], ['p', 's'], ['s', 'r']):
                decorated_turns.append([(translate[turn[0]], False), (translate[turn[1]], True)])
            else:
                decorated_turns.append([(translate[turn[0]], False), (translate[turn[1]], False)])

        if incomplete_last_turn:
            index = self.player_index(username)
            decorated_last_turn = []
            for i, m in enumerate(incomplete_last_turn):
                if m is None:
                    decorated_last_turn.append(('', False))
                elif i == index or incomplete_last_turn[index]:
                    decorated_last_turn.append((translate[m], False))
                else:
                    decorated_last_turn.append(('?', False))
            decorated_turns.append(decorated_last_turn)

        return decorated_turns

    def is_players_turn(self, username):
        """Check if it is player's turn.

        :param username: Player's username
        :return: boolean
        """
        if self.state != 1:  # Game not in play
            return False
        if not self.turns:  # Nobody has made any moves yet
            return True

        latest_turn = self.turns[-1]
        if not latest_turn[self.player_index(username)]:  # User not yet moved in latest turn
            return True
        if not [None for m in latest_turn if m is None]:  # Latest turn is complete, start new turn
            return True
