"""Main web application."""

import wsgiref.simple_server
import urllib.parse
import http.cookies
import sqlite3


def application(e, start_response):

    headers = [('Content-Type', 'text/html; charset=utf-8')]
    app_root = urllib.parse.urlunsplit((e['wsgi.url_scheme'], e['HTTP_HOST'], e['SCRIPT_NAME'], '', ''))
    params = urllib.parse.parse_qs(e['QUERY_STRING'])
    path_info = e['PATH_INFO']
    connection = sqlite3.connect('game.db')
    cursor = connection.cursor()

    # ----- If user has valid session cookie set session = True --------------------

    session = False
    session_user = None
    cookies = http.cookies.SimpleCookie()
    if 'HTTP_COOKIE' in e:
        cookies.load(e['HTTP_COOKIE'])
        if 'session' in cookies:
            session_user, session_pass = cookies['session'].value.split(':')
            cursor.execute('SELECT name FROM user WHERE name = ? AND password = ?', [session_user, session_pass])
            session = True if cursor.fetchone() else False

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
            cursor.execute('SELECT name FROM user WHERE name = ? AND password = ?', [param_user, param_pass])
            if cursor.fetchone():
                headers.append(('Set-Cookie', 'session={}:{}'.format(param_user, param_pass)))
                headers.append(('Location', app_root))
                start_response('303 See Other', headers)
                return []
            else:
                start_response('200 OK', headers)
                page += login_register_form
                return [(page + 'Wrong username or password</body></html>').encode()]

        elif param_do == 'Register' and param_user and param_pass:
            cursor.execute('SELECT name FROM user WHERE name = ?', [param_user])
            if cursor.fetchone():  # Username taken
                start_response('200 OK', headers)
                page += login_register_form
                return [(page + 'Username {} is taken.</body></html>'.format(param_user)).encode()]

            cursor.execute('INSERT INTO user (name, password) VALUES (?, ?)', [param_user, param_pass])
            connection.commit()

            headers.append(('Set-Cookie', 'session={}:{}'.format(param_user, param_pass)))
            headers.append(('Location', app_root))
            start_response('303 See Other', headers)
            return []

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
        else:
            start_response('200 OK', headers)
            page += 'Logged in {} | <a href="{}/logout">Log out</a></body></html>'.format(session_user, app_root)
            return [page.encode()]

    # ----- Dump tables ------------------------------------------------

    elif path_info == '/dump':
        cursor.execute('SELECT name, password FROM user')
        users = cursor.fetchall()

        page += '<a href="{}">Home</a>'.format(app_root)
        page += ' | <a href="{}/clear_all">Clear users</a>'.format(app_root)

        page += '<h2>Table "user"</h2>\n'
        page += '<p>Contains all registered users and their passwords.</p>\n'
        page += '<table><tr><th>name</th><th>password</th></tr>\n'
        for name, password in users:
            page += '<tr><td>{}</td><td>{}</td></tr>\n'.format(name, password)
        page += '</table>\n'

        page += '</body></html>'

        start_response('200 OK', headers)
        return [page.encode()]

    # ----- Clear tables --------------------------------------

    elif path_info == '/clear_all':
        cursor.execute('DELETE FROM user')
        connection.commit()

        headers.append(('Location', '{}/dump'.format(app_root)))
        start_response('303 See Other', headers)
        return []

    # ----- Unknown web app ----------------------------------------------------------

    else:
        start_response('200 OK', headers)
        return [(page + 'Unknown Web app {}</body></html>'.format(path_info)).encode()]

httpd = wsgiref.simple_server.make_server('', 8000, application)
httpd.serve_forever()
