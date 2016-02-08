"""Main web application.

Uses classes DB and Pyramid to build a pyramid game.
"""

import wsgiref.simple_server
import urllib.parse
import http.cookies
from db_sqlite import DB
from pyramid import Pyramid


def application(e, start_response):
    db = DB()

    headers = [('Content-Type', 'text/html; charset=utf-8')]
    app_root = urllib.parse.urlunsplit((e['wsgi.url_scheme'], e['HTTP_HOST'], e['SCRIPT_NAME'], '', ''))
    params = urllib.parse.parse_qs(e['QUERY_STRING'])
    path_info = e['PATH_INFO']

    # ----- If user has valid session cookie set session = True --------------------

    session = False
    session_user = None
    cookies = http.cookies.SimpleCookie()
    if 'HTTP_COOKIE' in e:
        cookies.load(e['HTTP_COOKIE'])
        if 'session' in cookies:
            session_user, session_pass = cookies['session'].value.split(':')
            session = db.user_pass_valid(session_user, session_pass)

    # ----- The common start of every page ---------------------------

    page = '''<!DOCTYPE html>
<html><head><title>Game</title>
<style>
    table { border-collapse: collapse; }
    table, th, td { border: 1px solid silver; padding: 2px; }
</style>
</head>
<body>
<h1>Rock-Paper-Scissors</h1>'''

    # ----- For logging in and registering ---------------------------

    if path_info == '/login_register':
        param_do = params['do'][0] if 'do' in params else None
        param_user = params['username'][0] if 'username' in params else None
        param_pass = params['password'][0] if 'password' in params else None

        login_register_form = '''
<form>
    <input type="text" name="username"> Username<br>
    <input type="password" name="password"> Password<br>
    <input type="submit" name="do" value="Login"> or
    <input type="submit" name="do" value="Register">
</form>'''

        if param_do == 'Login' and param_user and param_pass:
            if db.user_pass_valid(param_user, param_pass):
                headers.append(('Set-Cookie', 'session={}:{}'.format(param_user, param_pass)))
                headers.append(('Location', app_root))
                start_response('303 See Other', headers)
                return []
            else:
                start_response('200 OK', headers)
                page += login_register_form
                return [(page + 'Wrong username or password</body></html>').encode()]

        elif param_do == 'Register' and param_user and param_pass:
            if db.add_username(param_user, param_pass):
                headers.append(('Set-Cookie', 'session={}:{}'.format(param_user, param_pass)))
                headers.append(('Location', app_root))
                start_response('303 See Other', headers)
                return []
            else:
                start_response('200 OK', headers)
                page += login_register_form
                return [(page + 'Username {} is taken.</body></html>'.format(param_user)).encode()]

        else:
            start_response('200 OK', headers)
            return [(page + login_register_form + '</body></html>').encode()]

    # ----- Logout --------------------------------------------

    elif path_info == '/logout':
        headers.append(('Set-Cookie', 'session=0; expires=Thu, 01 Jan 1970 00:00:00 GMT'))
        headers.append(('Location', app_root))
        start_response('303 See Other', headers)
        return []

    # ----- Root page -----------------------------------------

    elif path_info == '/' or not path_info:
        if not session:
            start_response('200 OK', headers)
            page += '<a href="{}/login_register">Log in or register</a> to play</body></html>'.format(app_root)
            return [page.encode()]

        page += '{} | <a href="{}/logout">Logout</a>'.format(session_user, app_root)
#       page += ' | <a href="{}">Refresh</a>'.format(app_root)
        page += '<h2>My games</h2>\n'
        page += '<table><tr><th>Game</th><th>Goal</th><th>Quit</th><th>State</th><th>Players</th></tr>\n'
        games = [
            Pyramid(i, p, g, st, ts, t, db.connection) for i, p, g, st, ts, t in db.get_games_by_user(session_user)
            ]
        for game in games:
            page += '<tr><td>{}</td><td>{}</td><td><a href="{}/quit?id={}">quit</a></td>'.format(
                game.id, game.goal, app_root, game.id
            )
            players_scores = ', '.join(
                [
                    '{}{}|{}{}'.format(
                        '' if p['playing'] else '<s>',  # Add open strikethrough tag if player left game
                        p['name'],
                        p['score'],
                        '' if p['playing'] else '</s>'  # Add close strikethrough tag
                    ) for p in game.players
                ]
            )
            if game.state == 0:  # Accepting players
                page += '<td>Awaiting {}</td>'.format(game.num_players - len(game.players))
                page += '<td>' + ', '.join([p['name'] for p in game.players]) + '</td>'
            elif game.state == 2:
                page += '<td><a href="{}/game?id={}">Game over</a></td>'.format(app_root, game.id)
                page += '<td>' + players_scores + '</td>'
            elif game.is_players_turn(session_user):  # Playing, player's turn
                page += '<td><a href="{}/game?id={}">My turn</a></td>'.format(app_root, game.id)
                page += '<td>' + players_scores + '</td>'
            else:  # Playing, not player's turn
                page += '<td><a href="{}/game?id={}">Awaiting Turn</a></td>'.format(app_root, game.id)
                page += '<td>' + players_scores + '</td>'
            page += '</tr>\n'
        page += '</table>'
        page += '<p><a href="{}/newgame">Start a New Game</a></p>'.format(app_root)
        ts1 = max(game.ts for game in games) if games else None

        page += '<h2>Games accepting players</h2>\n'
        page += '<table><tr><th>Game</th><th>Goal</th><th>Join</th><th>State</th><th>Players</th></tr>\n'
        games = [
            Pyramid(i, p, g, 0, ts, t, db.connection)
            for i, p, g, ts, t in db.get_registering_games_by_user(session_user)
            ]
        for game in games:
            page += '<tr><td>{}</td><td>{}</td><td><a href="{}/join?id={}">join</a></td>'.format(
                game.id, game.goal, app_root, game.id
            )
            page += '<td>{} of {} players</td>'.format(len(game.players), game.num_players, game.id)
            page += '<td>' + ', '.join([p['name'] for p in game.players]) + '</td>'
            page += '</tr>\n'
        page += '</table>'
        ts2 = max(game.ts for game in games) if games else None

        page += '''
<script>
    function callback(event) {{
        if (event.target.readyState == 4 && event.target.responseText != '{} {}') {{
            window.location = '{}'
        }}
    }}
    function timeFunc(event) {{
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.addEventListener("readystatechange", callback)
        xmlhttp.open("GET", "{}/updated_games", true)
        xmlhttp.setRequestHeader("Content-Type", "text/plain")
        xmlhttp.send()
    }}
    setInterval(timeFunc, 1000)
</script>'''.format(ts1, ts2, app_root, app_root)

        start_response('200 OK', headers)
        return [(page + '</body></html>').encode()]

    # ----- Check if game list changed -------------------------------------------

    elif path_info == '/updated_games':
        if not session:
            start_response('200 OK', headers)
            return ['No session'.encode()]

        ts1, ts2 = db.updated_games(session_user)

        start_response('200 OK', headers)
        return ['{} {}'.format(ts1, ts2).encode()]

    # ----- Register new game ---------------------------------------------------------------
    # ***** MODIFY THIS PART TO ASK FOR NUMBER OF PLAYERS AND RECEIVE NUMBER OF PLAYERS *****

    elif path_info == '/newgame':
        if not session:
            start_response('200 OK', headers)
            return ['No session'.encode()]

        if 'goal' in params:
            db.new_game(2, params['goal'][0], session_user)
            headers.append(('Location', app_root))
            start_response('303 See Other', headers)
            return []

        page += '''
<h2>Create New Game</h2>
<form>
    <h3>Play until score:</h3>
    <input type="radio" name="goal" value="1">1<br>
    <input type="radio" name="goal" value="3">3<br>
    <input type="radio" name="goal" value="5">5<br>
    <input type="radio" name="goal" value="10" checked>10<br>
    <input type="radio" name="goal" value="20">20<br>
    <input type="radio" name="goal" value="100">100<br>
    <input type="submit" value="Create">
</form>
</body></html>'''

        start_response('200 OK', headers)
        return [page.encode()]

    # ----- Join game -----------------------------------------

    elif path_info == '/join':
        if not session:
            start_response('200 OK', headers)
            return ['No session'.encode()]

        game_id = params['id'][0]
        db.join_game(game_id, session_user)

        headers.append(('Location', app_root))
        start_response('303 See Other', headers)
        return []

    # ----- Quit game -----------------------------------------

    elif path_info == '/quit':
        if not session:
            start_response('200 OK', headers)
            return ['No session'.encode()]

        game_id = params['id'][0]
        db.quit_game(game_id, session_user)

        headers.append(('Location', app_root))
        start_response('303 See Other', headers)
        return []

    # ----- Game ------------------------------------------------------------

    elif path_info == '/game':
        if not session:
            start_response('200 OK', headers)
            return ['No session'.encode()]

        game_id = params['id'][0]

        (players, goal, state, ts, turns) = db.get_game_by_id(game_id)
        game = Pyramid(game_id, players, goal, state, ts, turns, db.connection)
        if game.state == 0:  # Error: cannot view game, it is still registering players
            start_response('200 OK', headers)
            return [(page + 'Still registering players</body></html>').encode()]

        if 'move' in params:  # Player came here by making a move
            game.add_player_move(session_user, params['move'][0])

        page += '<a href="{}">Home</a>'.format(app_root)
#       page += ' | <a href="{}/game?id={}">Refresh</a>'.format(app_root, game_id)
        page += '<h3>Game {} -- Play to {}</h3>'.format(game.id, game.goal)

        if game.state == 2:
            page += '<p>Game over</p>'
        elif game.is_players_turn(session_user):
            page += '<p>Your move: '
            move_template = '<a href="{}/game?id={}&amp;move={}">{}</a>'
            move_links = [
                move_template.format(app_root, game.id, mval, mname) for mval, mname in game.valid_moves(session_user)
                ]
            page += ' | '.join(move_links)
        else:
            page += '<p>Wait for your turn</p>'

        page += '<table>\n<tr><th>&nbsp;</th>'
        for p in game.players:
            page += '<th>{}</th>'.format(p['name']) if p['playing'] else '<th><s>{}</s></th>'.format(p['name'])
        page += '</tr>\n<tr style="background-color: silver"><td>Round</td>'
        for p in game.players:
            page += '<td>{} p</td>'.format(p['score'])
        page += '</tr>\n'

        for index, turn in enumerate(reversed(game.decorated_moves(session_user))):
            page += '<tr><td>{}</td>'.format(len(game.turns) - index)
            for move, winner in turn:
                if winner:
                    page += '<td style="background-color:lightgreen">{}</td>'.format(move)
                else:
                    page += '<td>{}</td>'.format(move)
            page += '</tr>\n'

        page += '</table>'

        if game.state == 1:
            page += '''
<script>
    function callback(event) {{
        if (event.target.readyState == 4 && event.target.responseText != '{}') {{
            window.location = '{}/game?id={}'
        }}
    }}
    function timeFunc(event) {{
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.addEventListener("readystatechange", callback)
        xmlhttp.open("GET", "{}/updated_game?id={}", true)
        xmlhttp.setRequestHeader("Content-Type", "text/plain")
        xmlhttp.send()
    }}
    setInterval(timeFunc, 1000)
</script>'''.format(game.ts, app_root, game.id, app_root, game.id)

        start_response('200 OK', headers)
        return [(page + '</body></html>').encode()]

    # ----- Check if game changed --------------------------------------

    elif path_info == '/updated_game':
        if not session:
            start_response('200 OK', headers)
            return ['No session'.encode()]

        start_response('200 OK', headers)
        p, g, s, ts, t = db.get_game_by_id(params['id'][0])
        return ['{}'.format(ts).encode()]

    # ----- Dump tables ------------------------------------------------

    elif path_info == '/dump':
        users, games, players = db.dump()

        page += '<a href="{}">Home</a>'.format(app_root)
        page += ' | <a href="{}/clear_games">Clear games and players</a>'.format(app_root)
        page += ' | <a href="{}/clear_all">Clear all</a>'.format(app_root)

        page += '<h2>Table "user"</h2>\n'
        page += '<p>Contains all registered users and their passwords.</p>\n'
        page += '<table><tr><th>name</th><th>password</th></tr>\n'
        for name, password in users:
            page += '<tr><td>{}</td><td>{}</td></tr>\n'.format(name, password)
        page += '</table>\n'

        page += '<h2>Table "game"</h2>\n'
        page += '<p>One row for every game.</p>\n'
        page += '<table><tr><th>rowid</th><th>players</th><th>goal</th><th>state</th><th>ts</th><th>turns</th></tr>\n'
        for rowid, numplayers, goal, state, ts, turns in games:
            page += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(
                rowid, numplayers, goal, state, ts, turns
            )
        page += '</table>\n'

        page += '<h2>Table "player"</h2>\n'
        page += '<p>Connects players with games. One row for every player in a game.</p>\n'
        page += '<table><tr><th>rowid</th><th>game_id</th><th>user_name</th><th>score</th><th>playing</th></tr>\n'
        for rowid, game_id, user_name, score, playing in players:
            page += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(
                rowid, game_id, user_name, score, playing
            )
        page += '</table>\n'

        page += '</body></html>'

        start_response('200 OK', headers)
        return [page.encode()]

    # ----- Clear tables --------------------------------------

    elif path_info == '/clear_games':
        db.clear_tables(False)
        headers.append(('Location', '{}/dump'.format(app_root)))
        start_response('303 See Other', headers)
        return []

    elif path_info == '/clear_all':
        db.clear_tables(True)
        headers.append(('Location', '{}/dump'.format(app_root)))
        start_response('303 See Other', headers)
        return []

    # ----- Unknown web app ----------------------------------------------------------

    else:
        start_response('200 OK', headers)
        return [(page + 'Unknown Web app {}</body></html>'.format(path_info)).encode()]

httpd = wsgiref.simple_server.make_server('', 8000, application)
httpd.serve_forever()
