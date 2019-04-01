# Ultimate TicTacToe Server

a python server backend for ultimate tic-tac-toe.

communication with the web client is done by a (far from any standard and almost random) json protocol:


## setup server

setup the database connection settings in `settings.py`. If files for a certificate are given, the websocket connection will be use the secured `wss://` websocket protocol instead of `ws://` (which is necessary if the client is accessed by `https://`). To create the necessary tables, the script `./create_database.py` can be used


## communication protocol with client

**json match state:**

```json
{
    "complete_field": '[[...],[...],...]',
    "global_field": '[[...],[...],...]',
    "last_move": {
        "sub_x": <int: xcoord of subfield of last move>,
        "sub_y": <int: ycoord of subfield of last move>,
        "x": <int: local xcoord in subfield of last move>,
        "y": <int: local ycoord in subfield of last move>
    }
    "game_over": <true | false>,
    "is_draw": <true | false>,
    "player_won": <null | <player_name>>,
    "current_player": <null | <player_name>>,
    "player_a": "...",
    "player_b": "..."
}
```

`complete_field` is of dimension 9x9, `global_field` of 3x3 (indicating the status of each subfield).
The possible values for a single field are

```
FIELD_EMPTY = 0
FIELD_USER_A = 1
FIELD_USER_B = 2
FIELD_DRAW = 3
```

**match**:

server sends this to every user which is participating in a match if it's updated

```json
{
    "type": "match_update",
    "data": {
        "id": "...",
        "revoke_time": <revoke_time>,
        "match_state": <null| <match_state>>
    }
}
```


**new temp session**

NOT IMPLEMENTED YET (and maybe never will be)

give the possibility to temporary login without a password

client

```json
{
    "type": "temp_session",
    "data": {
   		"name": "<player_name>"
    }
}
```

server response:

```json
{
    "type": "login_response",
    "data": {
        "success": <true|false>,
        "id": "<session-id>", 
        "msg": "..."
    }
}
```

**connect by session id**

reconnect with the session id from the last session

client

```json
{
    "type": "reconnect",
    "data": {
        "id": "<session-id>",
    }
}
```

server response:

```json
{
    "type": "reconnect_response",
    "data": {
        "success": <true|false>,
        "msg": "..."
    }
}
```

**login or register**:

login with username and password. If the username does not exist yet, a new account
is created automatically. After a successful login the server sends an elo update, friends update and match updates for each open match,.

client:

```json
{
    "type": "login",
    "data": {
   		"name": "<player_name>",
   		"pw": "<password>"
    }
}
```

server response:

```json
{
    "type": "login_response",
    "data": {
        "success": <true|false>,
        "id": "<session-id>", 
        "msg": "..."
    }
}
```


**match_request**:

will be send by clients. If `player` is `null` the player will be matched with the next (or previous)
player which sent a request without a player name

client:

```json
{
    "type": "match_request",
    "data": {
        "player": <null | <opponent_name>>
    }
}
```

server_response:

```json
{
    "type": "match_request_response",
    "data": {
        "success": <true|false>
        "msg": "..."
    }
}
```

**match_move**:

sending moves to the server. The server will answer with a match update.

client

```json
{
    "type": "move",
    "data": {
        "id": "match_id",
        "sub_x": "...",
        "sub_y": "...",
        "x": "...",
        "y": "..."
    }
}
```



**match update**

(is also sent on match start and send for all matches after login)

server:

```json
{
    "type": "match_update",
    "data": {
        "id": "<match_id>",
        "match_state": "<json match state>"
    }
}
```

**match close**

client:

```json
{
    "type": "end_match",
    "data": {
        "id": "<match_id>"
    }
}
```



**friend request**:

```json
{
    "type": "friend_request",
    "data" : {
        "user": "<friend>"
    }
}
```

response:

```json
{  
    "type": "friend_request_response",
    "data": {
        "success": <true|false>
        "msg": "..."
    }
}
```

**unfriend**:

```json
{
    "type": "unfriend_request",
    "data" : {
        "user": "<friend>"
    }
}
```

response:

```json
{  
    "type": "unfriend_request_response",
    "data": {
        "success": <true|false>
        "msg": "..."
    }
}
```



**friend update**:

is sent by server after a login or reconnect

```json
{
    "type": "friends_update",
    "data": {
        "friends": "<list of friends>",
        "elos": "<list of elo values>"
    }
}
```



**elo rank update**:

is sent by server after login, reconnect or a finished match

```json
{
    "type": "elo_update",
    "data": {
        "elo": <elo_value>,
        "rank": <rank>,
        "top_names": <list of top 100 names>,
        "top_elos": <list of top 100 elos>
    }
}
```

