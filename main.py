import asyncio
import websockets
from settings import *
import ssl

import traceback

from session_manager import SessionManager
from connection_handler import Connection, ConnectionHandler
from match_manager import MatchManager
from user_manager import UserManager
from database_connection import DatabaseConnection
import datetime

from tools import debug

um = UserManager(account_revoke_time)
sm = SessionManager(session_revove_time, temporary_session_revoke_time)
mm = MatchManager(um, match_revoke_time)
ch = ConnectionHandler(sm, um, mm, revoke_check_interval)


DatabaseConnection(db_host,
                   db_port,
                   db_user,
                   db_pw,
                   db_db,
                   db_charset)


async def socket_worker(websocket, path):
    connection = None

    try:
        raw_msg = await websocket.recv()

        connection = await ch.new_connection(websocket, raw_msg)

        if connection is None:
            return

        debug("successfull logged in user: " + connection.user_name)

        async for m in websocket:
            await ch.handle_message(connection, m)

    except websockets.ConnectionClosed as e:
        # nothing suspicious here
        pass

    except Exception as e:
        # TODO: each disconnect is an exception so far
        if connection is not None:
            debug("catched exception in worker for user: " +
                  connection.user_name + ": " + str(e))
        else:
            debug("catched exception in worker for unknown user: " + str(e))

        debug(traceback.debug_exc())

    finally:
        id = None
        if connection:
            id = connection.user_name
            await ch.disconnect(connection)
            await connection.close()

        if connection is None:
            id = "unknown_user"
        debug("close connection to user: " + id)

if cert_file is not None and key_file is not None:
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(cert_file, keyfile=key_file)

    start_server = websockets.serve(
        socket_worker, host='', port=server_port, ssl=ssl_context)

else:
    start_server = websockets.serve(
        socket_worker, host='', port=server_port)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
