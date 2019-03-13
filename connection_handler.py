import asyncio
import websockets
import json
from session_manager import SessionManager
from user_manager import UserManager
from match_manager import MatchManager
from match import Match


def parse_message(msg: str):
    # TODO: make it more robust by validating each part of a message
    msg_obj = json.loads(msg)
    if "type" not in msg_obj or "data" not in msg_obj:
        print("got strange message")
        return None

    return msg_obj


class Connection(object):
    def __init__(self,
                 id,
                 user_name: str,
                 registered: bool,
                 websocket: websocket.WebSocketServerProtocol):
        self.id = id
        self.user_name = user_name
        self.websocket = websocket
        self.is_registered_user = registered


class ConnectionHandler(object):
    def __init__(self,
                 session_manager: SessionManager,
                 user_manager: UserManager,
                 match_manager: MatchManager):
        self.session_manager = session_manager
        self.user_manager = user_manager
        self.match_manager = match_manager

        self.open_connections_by_user = {}
        self.open_connections_by_id = {}

        self.match_queue = set()

    def reconnect_session(self,
                          socket: websockets.WebSocketServerProtocol,
                          session_id: str):
        # check whether id exists
        tmp = self.session_manager.get_session_by_id(session_id)
        if len(tmp) == 0:
            # session not available!
            return None

        session_obj = tmp[0]

        is_registerd = session_obj['registered_user'] is not None

        user_name = session_obj['registered_user'] if is_registerd else session_obj['temp_user']

        conn = Connection(id=session_id,
                          user_name=user_name,
                          registered=is_registerd,
                          websocket=socket)

        self.session_manager.touch_session(session_id)

        return conn

    def close_connection(self, conn: Connection):
        if conn.id in self.open_connections_by_id:
            del(self.open_connections_by_id[conn.id])
            del(self.open_connections_by_user[conn.user_name])
        conn.websocket.close()

    def close_session(self, id):
        tmp = self.session_manager.get_session_by_id(id)
        if len(tmp) == 0:
            return

        if id in self.open_connections_by_id:
            self.close_connection([id])

        self.session_manager.delete_session(id)

    def _add_connection(self, conn):
        self.open_connections_by_id[conn.id] = conn
        self.open_connections_by_user[conn.user] = conn

    def _del_connection(self, conn):
        del(self.open_connections_by_id[conn.id])
        del(self.open_connections_by_user[conn.user])

    async def new_connection(self,
                             socket: websockets.WebSocketServerProtocol,
                             login_msg: str):

        msg = parse_message(login_msg)

        if msg is None:
            return None

        if msg['type'] == 'reconnect':
            conn = self.reconnect_session(socket, msg['data']['id'])
            if conn is not None:
                self._add_connection(conn)
                await conn.websocket.send(json.dumps({
                    "type": "reconnect_response",
                    "data": {
                        "success": True,
                        "msg": ""
                    }
                }))
                return conn
            await conn.websocket.send(json.dumps({
                "type": "reconnect_response",
                "data": {
                    "success": False,
                    "msg": "session not available"
                }
            }))
            return None

        elif msg['type'] == 'temp_session':
            name = msg['data']['name']
            if len(self.session_manager.get_session_by_temp_user(name)) == 0:
                if len(self.user_manager.get_user(name)) == 0:
                    if len(msg['data']['name']) < 16 and ';' not in name and '\'' not in name and '\"' not in name:
                        id = self.session_manager.create_session_for_temp_user(
                            name)
                        conn = Connection(
                            id=id, user_name=name, registered=False, websocket=socket)
                        self._add_connection(conn)
                        await socket.send(json.dumps({
                            "type": "temp_session_response",
                            "data": {
                                "success": True,
                                "id": id,
                                "message": "logged in as temporary user " + name
                            }
                        }))
                        return conn

            await socket.send(json.dumps({
                "type": "temp_session_response",
                "data": {
                    "success": False,
                    "id": None,
                    "message": "user name not available"
                }
            }))
            return None

        elif msg['type'] == 'login':
            # TODO
            pass

        elif msg['type'] == 'register':
            # TODO
            pass

    async def _start_match(self, user_a, user_b):
        m = self.match_manager.create_new_match(user_a, user_b)
        state = m.to_json_state()
        if user_a in self.open_connections_by_user:
            await self.open_connections_by_user[user_a].websocket.send(
                json.dumps({
                    {
                        "type": "match_update",
                        "data": {
                            "id": m.id,
                            "match_state": state
                        }
                    }
                })
            )
        if user_b in self.open_connections_by_user:
            await self.open_connections_by_user[user_b].websocket.send(
                json.dumps({
                    {
                        "type": "match_update",
                        "data": {
                            "id": m.id,
                            "match_state": state
                        }
                    }
                })
            )

    async def _on_match_req(self, conn, data):
        if len(self.match_queue) > 0:
            # it's a match!
            user_a = self.match_queue.pop()
            self._start_match(user_a, conn.user_name)

        else:
            self.match_queue.append(conn.user_name)

    async def _on_match_move(self, conn, data):
        pass

    async def _on_match_close(self, conn, data):
        pass

    async def disconnect(self, conn):
        self._del_connection(conn)

    async def handle_message(self, conn, msg_str):
        msg = parse_message(msg_str)

        if msg is None:
            return None

        t = msg['type']

        self.user_manager.touch_user(conn.user_name)
        if t == "match_request":
            await self._on_match_req(conn, msg['data'])

        elif t == "move":
            await self._on_match_move(conn, msg['data'])

        elif t == "end_match":
            await self._on_match_close(conn, msg['data'])

        else:
            print("could not interpret message: " + msg_str)
