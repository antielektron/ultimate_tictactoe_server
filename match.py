
import numpy as np
import json
import base64

from tools import debug

# decoder/encoder took from: https://stackoverflow.com/a/19271311


def Base64Encode(ndarray):
    return json.dumps([str(ndarray.dtype), base64.b64encode(ndarray), ndarray.shape])


def Base64Decode(jsonDump):
    loaded = json.loads(jsonDump)
    dtype = np.dtype(loaded[0])
    arr = np.frombuffer(base64.decodestring(loaded[1]), dtype)
    if len(loaded) > 2:
        return arr.reshape(loaded[2])
    return arr


def SimpleEncode(ndarray):
    return json.dumps(ndarray.tolist())


def SimpleDecode(jsonDump):
    return np.array(json.loads(jsonDump))


class Match(object):

    FIELD_EMPTY = 0
    FIELD_USER_A = 1
    FIELD_USER_B = 2
    FIELD_DRAW = 3

    def __init__(self, n, match_id, player_a_name, player_b_name, json_state=None):
        self.n = n
        self.id = match_id
        self.complete_field = np.zeros(shape=(n*n, n*n), dtype=int)
        self.global_field = np.zeros(shape=(n, n), dtype=int)
        self.player_won = None
        self.is_draw = False
        self.game_over = False
        self.last_move = None
        self.is_player_a = True
        self.player_a_name = player_a_name
        self.player_b_name = player_b_name

        if json_state is not None:
            self.from_json_state(json_state)

    def from_json_state(self, json_state):
        match_obj = json.loads(json_state)
        self.complete_field = np.array(match_obj['complete_field'], dtype=int)
        self.global_field = np.array(match_obj['global_field'], dtype=int)
        self.player_won = match_obj['player_won']
        self.game_over = match_obj['game_over']
        self.last_move = match_obj['last_move']
        self.is_player_a = match_obj['active_player'] == self.player_a_name

        # draw state w.r.t backward compability
        self.is_draw = match_obj['is_draw'] if 'is_draw' in match_obj else False

    def to_json_state(self):
        return json.dumps(self.to_dict_state())
    
    def to_dict_state(self):
        return {
            'complete_field': self.complete_field.tolist(),
            'global_field': self.global_field.tolist(),
            'last_move': self.last_move,
            'game_over': self.game_over,
            'player_won': self.player_won,
            'active_player': self.player_a_name if self.is_player_a else self.player_b_name,
            'player_a': self.player_a_name,
            'player_b': self.player_b_name,
            'is_draw': self.is_draw
        }

    def switch_player_names(self):
        tmp = self.player_a_name
        self.player_a_name = self.player_b_name
        self.player_b_name = tmp

    def get_current_player(self):
        return self.player_a_name if self.is_player_a else self.player_b_name

    def is_move_valid(self, sub_x, sub_y, x, y):
        if sub_x < 0 or sub_x >= self.n:
            return False
        if sub_y < 0 or sub_y >= self.n:
            return False

        if x < 0 or x >= self.n:
            return False
        if y < 0 or y >= self.n:
            return False

        if (self.last_move is not None):
            last_x = self.last_move['x']
            last_y = self.last_move['y']
            last_sub_x = self.last_move['sub_x']
            last_sub_y = self.last_move['sub_y']

            if sub_x != last_x and self.global_field[last_y, last_x] == Match.FIELD_EMPTY:
                # user is not allowed to place everywhere! wrong move!
                return False

            if sub_y != last_y and self.global_field[last_y, last_x] == Match.FIELD_EMPTY:
                return False

        if self.complete_field[sub_y * self.n + y][sub_x * self.n + x] != Match.FIELD_EMPTY:
            return False

        return True

    def is_full(self, field):
        return not field.__contains__(Match.FIELD_EMPTY)

    def check_win(self, field, x, y):
        is_col = True
        is_row = True
        is_main_diag = False
        is_sec_diag = False

        val = field[y, x]

        for i in range(self.n):
            if (field[i, x] != val):
                is_col = False
                break

        for i in range(self.n):
            if (field[y, i] != val):
                is_row = False
                break

        if x == y:
            is_main_diag = True
            for i in range(self.n):
                if field[i, i] != val:
                    is_main_diag = False
                    break

        if x + y == self.n - 1:
            is_sec_diag = True
            for i in range(self.n):
                if field[i, self.n - i - 1] != val:
                    is_sec_diag = False
                    break

        return is_col or is_row or is_main_diag or is_sec_diag

    def move(self, move_dict):
        sub_x = int(move_dict['sub_x'])
        sub_y = int(move_dict['sub_y'])
        x = int(move_dict['x'])
        y = int(move_dict['y'])

        abs_x = sub_x * self.n + x
        abs_y = sub_y * self.n + y

        player_mark = Match.FIELD_USER_A if self.is_player_a else Match.FIELD_USER_B

        if not self.is_move_valid(sub_x, sub_y, x, y):
            debug("invalid move")
            return False

        # else: move!
        self.complete_field[abs_y, abs_x] = player_mark

        # encode move:
        self.last_move = {'sub_x': sub_x, 'sub_y': sub_y, 'x': x, 'y': y}

        # check whether this indicates changes in the global field:
        if self.global_field[sub_y, sub_x] != Match.FIELD_EMPTY:
            debug("field not empty")
            return False

        subgrid = self.complete_field[sub_y * self.n: (
            sub_y + 1) * self.n, sub_x * self.n: (sub_x + 1) * self.n]

        if self.check_win(subgrid, x, y):
            self.global_field[sub_y, sub_x] = player_mark
            if self.check_win(self.global_field, sub_x, sub_y):
                self.game_over = True
                self.player_won = self.player_a_name if self.is_player_a else self.player_b_name

        elif self.is_full(subgrid):
            self.global_field[sub_y, sub_x] = Match.FIELD_DRAW
            if self.is_full(self.global_field):
                self.game_over = True
                self.player_won = None
                self.is_draw = True

        self.is_player_a = not self.is_player_a

        return True
