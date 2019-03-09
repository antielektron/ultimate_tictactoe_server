# ultimate_tictactoe_server

a python server backend for ultimate tic-tac-toe.

communication with the web client is done by a (far from any standard and almost random) json protocol:



**register as player and in game queue:**

```json
{
    "type": "register",
    "data": {
        "id": "<player_id>",
   		"name": "<player_name>"
    }
}
```

response:

```JSON
{
    "type": "register_response",
    "data": {
        "success": true,
        "msg": "<additional info e.g. in case of error>"
    }
}
```



**message from server that game started**

```json
{
    "type": "game_starts",
    "data": {
        "msg": "...",
        "opponent_name": "...",
        "is_first_move": true
    }
}
```

note: `is_first_move` indicates whether the player or it's opponent begins



**move**

```json
{
    "type": "move",
    "data": {
        "sub_x": "...",
        "sub_y": "...",
        "x": "...",
        "y": "..."
    }
}
```

response:

```json
{
    "type": "move_response",
    "data": {
        "success": true,
        "msg": "..."
    }
}
```



**end game**

```json
{
    "type": "end_game",
    "data": {
        "msg": "..."
    }
}
```

(response?)