# ultimate_tictactoe_server

a python server backend for ultimate tic-tac-toe.

communication with the web client is done by a (far from any standard and almost random) json protocol:



## new version:

**json match state:**

```json
{
    complete_field: '[[...],[...],...]',
    global_field: '[[...],[...],...]',
    last_move: {
        "sub_x": "...",
        "sub_y": "...",
        "x": "...",
        "y": "..."
    }
    game_over: <true | false>,
    is_draw: <true | false>,
    player_won: <null | <player_name>>,
    current_player: <null | <player_name>>,
    player_a: "...",
    player_b: "..."
}
```



**match**:

```json
{
    "type": "match_update",
    "data": {
        "id": "...",
        "revoke_time": <revoke_time>,
        "ranked": "<true | false">,
        "match_state": <null| <match_state>>
    }
}
```





**new temp session**

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



keep pw null for requesting a temporary session (will be deleted after one hour of inactivity and matches are not ranked)



```json
{
    "type": "login",
    "data": {
   		"name": "<player_name>",
   		"pw": "<password> | null"
    }
}
```

response:

```json
{
    "type": "login_response",
    "data": {
        "success": <true|false>,
        "id": "<session-id>",
        "registered": <true | false>,
        "msg": "..."
    }
}
```





**match_request**:

client (or server for sending invites)

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

(also send on match start and send for all matches after login)

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

