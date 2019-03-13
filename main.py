import asyncio
import websockets
from settings import *
import ssl

from game_manager import *


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

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(cert_file , keyfile=key_file)

start_server = websockets.serve(socket_worker, host='', port=server_port, ssl=ssl_context)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
