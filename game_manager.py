#!/usr/bin/env python3

import asyncio
import websockets
import json

player_id_queue = set()
sockets = {}

player_games = {}


async def register_user(id, socket):

    if id in player_id_queue:
        return False

    player_id_queue.add(id)
    sockets[id] = socket

    await matchmaking()

    return True


async def unregister_user(id):
    if id in player_id_queue:
        player_id_queue.remove(id)
        del(sockets[id])

    elif id in player_games:
        # we have an active game and have to end it
        await player_games[id]._on_end_game(id)
        del(player_games[id])


async def process_message(id, json):
    if id in player_games:
        await player_games[id].processPlayerMessage(id, json)


async def create_new_match():
    p_a = player_id_queue.pop()
    p_b = player_id_queue.pop()

    s_a = sockets[p_a]
    s_b = sockets[p_b]

    del(sockets[p_a])
    del(sockets[p_b])

    new_game = GameManager(p_a, p_b, p_a, s_a, s_b)

    player_games[p_a] = new_game
    player_games[p_b] = new_game

    await new_game.startMatch()


async def matchmaking():
    if len(player_id_queue) < 2:
        # we need at least 2 users for that
        return

    else:
        asyncio.ensure_future(create_new_match())


class GameManager(object):
    def __init__(self, player_a_id, player_b_id, start_player, socket_a, socket_b):
        self.player_a_id = player_a_id
        self.player_b_id = player_b_id

        self.socket_a = socket_a
        self.socket_b = socket_b

        self.current_player = start_player

        self.game_finished = False

    async def startMatch(self):

        print("match starts")

        start_msg_a = {
            'type': 'game_starts',
            'data': {
                'msg': '...',
                'opponent_name': self.player_b_id,
                'is_first_move': True
            }
        }

        start_msg_b = {
            'type': 'game_starts',
            'data': {
                'msg': '...',
                'opponent_name': self.player_a_id,
                'is_first_move': False
            }
        }

        await self.socket_a.send(json.dumps(start_msg_a))
        await self.socket_b.send(json.dumps(start_msg_b))

        print("start message send to all players")

    async def processPlayerMessage(self, player_id, json_str):
        if len(json_str) > 4096:
            # something is fishy here
            print("received strange message from client")
        
        print("received message: " + json_str)

        try:
            json_dict = json.loads(json_str)
            type = json_dict['type']
            data = json_dict['data']

            if type == "move":
                await self._on_move(player_id, data)

            elif type == "end_game":
                await self._on_end_game(player_id)

        except Exception as e:
            print("" + str(e) + ": received wrong formated message")

    async def _on_move(self, player_id, move_data):
        response = {'type': 'move_response'}
        response_data = {}

        opponent_response = {'type': 'move'}
        opponent_response_data = {}

        opponent_response_data['sub_x'] = move_data['sub_x']
        opponent_response_data['sub_y'] = move_data['sub_y']
        opponent_response_data['x'] = move_data['x']
        opponent_response_data['y'] = move_data['y']
        opponent_response['data'] = opponent_response_data

        if player_id == self.current_player:

            is_a = (self.player_a_id == player_id)
            current_socket = self.socket_a if is_a else self.socket_b
            opponent_socket = self.socket_b if is_a else self.socket_a

            response_data['success'] = True
            response_data['msg'] = "move successful"

            response['data'] = response_data

            await opponent_socket.send(json.dumps(opponent_response))
            await current_socket.send(json.dumps(response))

            # switch player
            self.current_player = self.player_b_id if is_a else self.player_a_id

        else:
            print("received move from wrong player")

            is_a = (self.player_a_id == player_id)
            current_socket = self.socket_a if is_a else self.socket_b

            response_data["success"] = False
            response_data["msg"] = "not your turn!"

            response['data'] = response_data

            await current_socket.send(json.dumps(response))

    async def _on_end_game(self, player_id):

        if self.game_finished:
            return

        is_a = (self.player_a_id == player_id)
        opponent_socket = self.socket_b if is_a else self.socket_a

        opponent_response = {'type': 'end_game'}
        opponent_response['data'] = {'msg': 'game closed by opponent'}

        await opponent_socket.send(json.dumps(opponent_response))

        self.game_finished = True
