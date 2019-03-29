import asyncio
import websockets
import json
from session_manager import SessionManager
from user_manager import UserManager
from match_manager import MatchManager
from match import Match

from tools import debug, elo_p_win, elo_update


def parse_message(msg: str):
    # TODO: make it more robust by validating each part of a message
    msg_obj = json.loads(msg)
    if "type" not in msg_obj or "data" not in msg_obj:
        debug("got strange message")
        return None

    return msg_obj


class Connection(object):
    def __init__(self,
                 id,
                 user_name: str,
                 registered: bool,
                 websocket: websockets.WebSocketServerProtocol):
        self.id = id
        self.user_name = user_name
        self.websocket = websocket
        self.is_registered_user = registered
        self.is_closed = False

    async def send(self, msg):
        try:
            await self.websocket.send(msg)
        except Exception as e:
            debug("error sending message to user " +
                  self.user_name + ". Reason: " + str(e))

    async def close(self):
        try:
            if self.is_closed:
                return
            self.websocket.close()
            self.is_closed = True

        except Exception as e:
            debug("error closing session to user " +
                  self.user_name + ". Reason: " + str(e))


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
        conn.close()

    def close_session(self, id):
        tmp = self.session_manager.get_session_by_id(id)
        if len(tmp) == 0:
            return

        if id in self.open_connections_by_id:
            self.close_connection([id])

        self.session_manager.delete_session(id)

    def _add_connection(self, conn):
        self.open_connections_by_id[conn.id] = conn
        self.open_connections_by_user[conn.user_name] = conn

    def _del_connection(self, conn):
        del(self.open_connections_by_id[conn.id])
        del(self.open_connections_by_user[conn.user_name])

    async def new_connection(self,
                             socket: websockets.WebSocketServerProtocol,
                             login_msg: str):
        msg = parse_message(login_msg)
        debug("new incomming connection...")
        if msg is None:
            return None

        if msg['type'] == 'reconnect':
            conn = self.reconnect_session(socket, msg['data']['id'])
            if conn is not None:
                self._add_connection(conn)
                await socket.send(json.dumps({
                    "type": "reconnect_response",
                    "data": {
                        "success": True,
                        "id": conn.id,
                        "user": conn.user_name,
                        "msg": ""
                    }
                }))
                await self.send_elo(conn)
                await self.send_friends(conn)
                await self._on_match_state_req(conn, None)
                return conn
            await conn.send(json.dumps({
                "type": "reconnect_response",
                "data": {
                    "success": False,
                    "id": conn.id,
                    "user": conn.user_name,
                    "msg": "session not available"
                }
            }))
            return None

        elif msg['type'] == 'temp_session':
            name = msg['data']['name'].lower()
            if len(self.session_manager.get_session_by_temp_user(name)) == 0:
                if len(self.user_manager.get_user(name)) == 0:
                    if len(msg['data']['name']) < 16 and ';' not in name and '\'' not in name and '\"' not in name:
                        id = self.session_manager.create_session_for_temp_user(
                            name)

                        conn = Connection(
                            id=id, user_name=name, registered=False, websocket=socket)

                        self._add_connection(conn)

                        await socket.send(json.dumps({
                            "type": "login_response",
                            "data": {
                                "success": True,
                                "id": id,
                                "msg": "logged in as temporary user " + name
                            }
                        }))

                        return conn

            await socket.send(json.dumps({
                "type": "login_response",
                "data": {
                    "success": False,
                    "id": None,
                    "msg": "user name not available"
                }
            }))
            return None

        elif msg['type'] == 'login':
            response_msg = ""
            success = False
            session_id = None
            name = None
            pw = None
            conn = None

            try:

                name = msg['data']['name'].lower()
                pw = msg['data']['pw']

                if len(name) <= 16 and len(pw) <= 32 and len(name) > 0 and len(pw) > 0:

                    users = self.user_manager.get_user(name)
                    if len(users) == 0:
                        # user does not exists:
                        self.user_manager.create_user(name, pw)
                        session_id = self.session_manager.create_session_for_registered_user(
                            name)
                        response_msg = "successful registered and logged in user " + name
                        success = True

                    elif self.user_manager.verify_user(name, pw):
                        session_id = self.session_manager.create_session_for_registered_user(
                            name)
                        response_msg = "successful logged in as user " + name
                        success = True

                    else:
                        response_msg = "invalid password for user " + name
                else:
                    response_msg = "invalid username or pw"

            except Exception as e:
                response_msg = "invalid username or pw"

            if success:
                conn = Connection(id=session_id, user_name=name,
                                  registered=True, websocket=socket)
                self._add_connection(conn)

            await socket.send(json.dumps({
                "type": "login_response",
                "data": {
                    "success": success,
                    "id": session_id,
                    "msg": response_msg
                }
            }))

            if success:
                await self.send_elo(conn)
                await self.send_friends(conn)
                await self._on_match_state_req(conn, None)

            return conn

        return None

    async def _start_match(self, user_a, user_b):
        m = self.match_manager.create_new_match(user_a, user_b)
        state = json.loads(m.to_json_state())
        if user_a in self.open_connections_by_user:
            await self.open_connections_by_user[user_a].websocket.send(
                json.dumps(
                    {
                        "type": "match_update",
                        "data": {
                            "id": m.id,
                            "match_state": state
                        }
                    }
                )
            )
        if user_b in self.open_connections_by_user:
            await self.open_connections_by_user[user_b].websocket.send(
                json.dumps(
                    {
                        "type": "match_update",
                        "data": {
                            "id": m.id,
                            "match_state": state
                        }
                    }
                )
            )

    async def _on_match_req(self, conn, data):
        n_open_matches = len(
            self.match_manager.get_matches_for_user(conn.user_name))

        if n_open_matches >= 5:
            await conn.websocket.send(
                json.dumps(
                    {
                        "type": "match_request_response",
                        "data": {
                            "success": False,
                            "msg": "you have too many active matches to search for a new one"
                        }
                    }
                )
            )
            return

        if data['player'] is None:
            if conn.user_name in self.match_queue:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "match_request_response",
                            "data": {
                                "success": False,
                                "msg": "you are already searching for a random match"
                            }
                        }
                    )
                )
                return

            if len(self.match_queue) > 0:
                # it's a match!
                user_a = self.match_queue.pop()
                await self._start_match(user_a, conn.user_name)

            else:
                if conn.user_name not in self.match_queue:
                    self.match_queue.add(conn.user_name)

            await conn.websocket.send(
                json.dumps(
                    {
                        "type": "match_request_response",
                        "data": {
                            "success": True,
                            "msg": "created match request"
                        }
                    }
                )
            )

        else:
            opponent = data['player'].lower()
            if opponent == conn.user_name:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "match_request_response",
                            "data": {
                                "success": False,
                                "msg": "you cannot play against yourself"
                            }
                        }
                    )
                )
                return
            try:
                if len(opponent) <= 16 and '\'' not in opponent and '"' not in opponent:
                    if len(self.user_manager.get_user(opponent)) > 0:

                        if len(self.match_manager.get_matches_for_user(conn.user_name)) >= 5:
                            await conn.websocket.send(
                                json.dumps(
                                    {
                                        "type": "match_request_response",
                                        "data": {
                                            "success": False,
                                            "msg": "player " + opponent + " has too many open matches"
                                        }
                                    }
                                )
                            )
                            return

                        if (self.match_manager.is_match(conn.user_name, opponent)):
                            await conn.websocket.send(
                                json.dumps(
                                    {
                                        "type": "match_request_response",
                                        "data": {
                                            "success": False,
                                            "msg": "you are already plaing against " + opponent
                                        }
                                    }
                                )
                            )
                            return

                        await self._start_match(conn.user_name, opponent)

                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "match_request_response",
                                    "data": {
                                        "success": True,
                                        "msg": "startet match against " + opponent
                                    }
                                }
                            )
                        )
                    else:
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "match_request_response",
                                    "data": {
                                        "success": False,
                                        "msg": "user " + opponent + " not found :("
                                    }
                                }
                            )
                        )

            except Exception as e:
                debug("error processing match request: " + str(data) + str(e))

    async def _on_match_state_req(self, conn, data):
        db_matches = self.match_manager.get_matches_for_user(conn.user_name)
        for db_match in db_matches:
            match = self.match_manager.get_match(db_match['id'])
            await conn.send(json.dumps({
                "type": "match_update",
                "data": {
                    "id": db_match['id'],
                    "match_state": json.loads(match.to_json_state())
                }
            }))
            if match.game_over:
                if match.player_won is None or match.player_won != conn.user_name:
                    self.match_manager.delete_match(match.id)

    async def _on_match_move(self, conn, data):

        match = None

        try:
            sub_x = int(data['sub_x'])
            sub_y = int(data['sub_y'])
            x = int(data['x'])
            y = int(data['y'])

            if type(sub_x) is int and type(sub_y) is int:
                if type(x) is int and type(y) is int:
                    if type(data['id']) is str:
                        match = self.match_manager.apply_move(data)

        finally:
            match_state = None
            if match is not None:
                match_state = match.to_json_state()

                debug(match_state)

                await conn.send(json.dumps({
                    'type': 'match_update',
                    'data': {
                        'id': match.id,
                        'match_state': json.loads(match_state)
                    }
                }))

                if match.game_over:
                    if match.is_draw or (match.player_won is not None):
                        # send rank update
                        await self.send_elo(conn)

                other_user = match.player_a_name if conn.user_name == match.player_b_name else match.player_b_name

                if other_user in self.open_connections_by_user:
                    other_conn = self.open_connections_by_user[other_user]
                    await other_conn.send(json.dumps({
                        'type': 'match_update',
                        'data': {
                            'id': match.id,
                            'match_state': json.loads(match_state)
                        }
                    }))
                    if match.game_over:
                        self.match_manager.delete_match(match.id)
                        if match.is_draw or (match.player_won is not None):
                            # send rank update
                            await self.send_elo(other_conn)

    async def _on_match_close(self, conn, data):
        match = None
        try:
            match_id = data['id']
            if type(match_id) is str:
                match = self.match_manager.get_match(match_id)

                if (match is None):
                    return

                if not match.game_over:
                    # check whether both player made a move. If so, the match is ranked as lost for the player who aborted the match
                    if match.complete_field.__contains__(Match.FIELD_USER_A) and match.complete_field.__contains__(Match.FIELD_USER_B):

                        # update rankings:
                        player_lost = conn.user_name
                        player_won = match.player_a_name if player_lost == match.player_b_name else match.player_b_name

                        elo_won = self.user_manager.get_elo(player_won)
                        elo_lost = self.user_manager.get_elo(player_lost)

                        # calculate elo values:
                        p_won = elo_p_win(elo_won, elo_lost)
                        p_lost = 1 - p_won

                        new_elo_won = elo_update(elo_won, 1, p_won)
                        new_elo_lost = elo_update(elo_lost, 0, p_lost)

                        self.user_manager.update_elo(player_won, new_elo_won)
                        self.user_manager.update_elo(player_lost, new_elo_lost)

                        await self.send_elo(conn)

                        if player_won in self.open_connections_by_user:
                            other_conn = self.open_connections_by_user[player_won]
                            await self.send_elo(other_conn)
                        
                        debug(
                            f"Match {match.id} is aborted by {player_lost} (against {player_won}). Update elo-rankings: {elo_won}->{new_elo_won} and {elo_lost}->{new_elo_lost}")

                match.game_over = True

                match_state = match.to_json_state()

                opponent = match.player_a_name if match.player_a_name != conn.user_name else match.player_b_name

                response = json.dumps({
                    'type': 'match_update',
                    'data': {
                        'id': match_id,
                        'match_state': json.loads(match_state)
                    }
                })

                if opponent in self.open_connections_by_user:
                    await self.open_connections_by_user[opponent].websocket.send(response)

                await conn.send(response)

                self.match_manager.delete_match(match_id)

        except Exception as e:
            match_state = None
            if match is not None:
                match_state = match.to_json_state()

            await conn.send(json.dumps({
                'type': 'match_update',
                'data': {
                    'match_state': json.loads(match_state)
                }
            }))

    async def _on_friend_request(self, conn, data):
        msg = "error in handling friend request"
        success = False
        try:
            friend = data['user'].lower()

            # check for user:
            if "\"" not in friend and "'" not in friend and ";" not in friend:
                if friend in self.user_manager.get_friends_for_user(conn.user_name):
                    success = False
                    msg = f"'{friend}' is already your friend"

                elif self.user_manager.add_friend_to_user(conn.user_name, friend):
                    success = True
                    msg = f"added '{friend}' as a friend"

                else:
                    success = False
                    msg = f"player '{friend}' not found"

            else:
                success = False
                msg = "misformated friend request"

        finally:
            await conn.send(json.dumps({
                'type': 'friend_request_response',
                'data': {
                    'success': success,
                    'msg': msg
                }
            }))

            if success:
                await self.send_friends(conn)

    async def _on_unfriend_request(self, conn, data):
        success = False
        msg = "error in handling unfriend request"
        try:
            friend = data['user'].lower()

            if "\"" not in friend and "'" not in friend and ";" not in friend:
                if friend not in self.user_manager.get_friends_for_user(conn.user_name):
                    success = False
                    msg = f"cannot end friendship with '{friend}': it's not one of your friends"
                else:
                    self.user_manager.remove_friend_from_user(
                        conn.user_name, friend)

                    success = True
                    msg = f"removed '{friend}' from your friend list"

        finally:
            await conn.send(json.dumps({
                'type': 'unfriend_request_response',
                'data': {
                    'success': success,
                    'msg': msg
                }
            }))

            if success:
                await self.send_friends(conn)

    async def send_friends(self, conn):

        friends, elos = self.user_manager.get_friends_and_elos_for_user(
            conn.user_name)

        await conn.send(json.dumps({
            'type': 'friends_update',
            'data': {
                'friends': friends,
                'elos': elos
            }
        }))

    async def send_elo(self, conn):
        await conn.send(json.dumps({
            'type': 'elo_update',
            'data': {
                'elo': self.user_manager.get_elo(conn.user_name)
            }
        }))

    async def disconnect(self, conn):
        self._del_connection(conn)

    async def handle_message(self, conn, msg_str):
        msg = parse_message(msg_str)

        debug("incoming message" + str(msg))

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

        elif t == "match_states_request":
            await self._on_match_state_req(conn, msg['data'])

        elif t == "friend_request":
            await self._on_friend_request(conn, msg['data'])

        elif t == "unfriend_request":
            await self._on_unfriend_request(conn, msg['data'])

        else:
            debug("could not interpret message: " + msg_str)
