import asyncio
import websockets
from settings import *
import ssl

import traceback

from game_manager import *
from session_manager import SessionManager
from connection_handler import Connection, ConnectionHandler
from match_manager import MatchManager
from user_manager import UserManager
from database_connection import DatabaseConnection
import datetime

um = UserManager()
sm = SessionManager(datetime.timedelta(hours=12))
mm = MatchManager()
ch = ConnectionHandler(sm, um, mm)


DatabaseConnection(db_host,
                   db_port,
                   db_user,
                   db_pw,
                   db_db,
                   db_charset)


async def new_socket_worker(websocket, path):
    connection = None

    print("new incomin connection")

    try:
        raw_msg = await websocket.recv()

        connection = await ch.new_connection(websocket, raw_msg)

        print(ch.open_connections_by_id)
        print(ch.open_connections_by_user)

        if connection is None:
            return
        
        async for m in websocket:
            await ch.handle_message(connection, m)

    except Exception as e:
        # TODO: each disconnect is an exception so far
        if connection is not None:
            print("catched exception in worker for user: " +
                  connection.user_name + ": " + str(e))
        else:
            print("catched exception in worker for unknown user: " + str(e))
        
        print(traceback.print_exc())

    finally:
        id = None
        if connection:
            id = connection.user_name
            print(ch.open_connections_by_id)
            await ch.disconnect(connection)
            await connection.close()

        if connection is None:
            id = "unknown_user"
        print("close connection to user: " + id)


async def socket_worker(websocket, path):

    registered = False
    id = None

    print("new connection")

    try:
        # get first message as register message
        raw_msg = await websocket.recv()

        msg = json.loads(raw_msg)

        if msg['type'] != 'register':
            print("got wrong registration")
            websocket.close()
            return

        id = msg['data']['id']

        registered = await register_user(id, websocket)

        register_response = {
            'type': 'register_response', 'data': {
                'success': True, 'msg': '...'}}

        if not registered:
            register_response['data']['success'] = False

            await websocket.send(json.dumps(register_response))
            websocket.close()
            return

        await websocket.send(json.dumps(register_response))

        print("successful redisterd user " + id)

        async for m in websocket:
            await process_message(id, m)

    except Exception as e:
        # TODO: each disconnect is an exception so far
        if id is not None:
            print("catched exception in worker for user: " + id + ": " + str(e))
        else:
            print("catched exception in worker for unknown user")
        

    finally:
        if registered:
            await unregister_user(id)

        if id is None:
            id = "unknown_user"
        print("close connection to user: " + id)


#ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
#ssl_context.load_cert_chain(cert_file, keyfile=key_file)

start_server = websockets.serve(
    new_socket_worker, host='', port=server_port)  # , ssl=ssl_context)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
