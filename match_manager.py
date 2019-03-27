from database_connection import DatabaseConnection, SQLInjectionError, get_sql_time
from user import User
import datetime
import uuid
import settings
from match import Match

from tools import debug


class MatchManager(object):
    def __init__(self):
        pass

    def get_match(self, id):
        query = "SELECT * FROM matches WHERE id=%s"
        result = DatabaseConnection.global_single_query(query, (id))
        if len(result) == 0:
            return None
        match = Match(n=settings.n, match_id=id, player_a_name=result[0]['user_a'],
                      player_b_name=result[0]['user_b'], json_state=result[0]['match_state'])
        return match

    def get_matches_for_user(self, user_name):
        query = "SELECT * FROM matches WHERE user_a=%s OR user_b=%s"
        return DatabaseConnection.global_single_query(query, (user_name, user_name))

    def create_new_match(self, user_a, user_b):
        match_id = uuid.uuid4().hex
        # check if already existent (but should not be the case)
        if len(DatabaseConnection.global_single_query("SELECT id FROM matches WHERE id=%s", (match_id))) > 0:
            return self.create_new_match(user_a, user_b)

        match = Match(n=settings.n, match_id=match_id,
                      player_a_name=user_a, player_b_name=user_b)
        now = datetime.datetime.now()
        query = "INSERT INTO matches (id, user_a, user_b, match_state, active_user, last_active) VALUES (%s, %s, %s, %s, %s,%s)"
        DatabaseConnection.global_single_execution(
            query, (match_id, user_a, user_b, match.to_json_state(), match.get_current_player(), get_sql_time(now)))
        return match

    def update_match(self, match_id, match):
        now = get_sql_time(datetime.datetime.now())
        query = "UPDATE matches SET match_state=%s, active_user=%s, last_active=%s WHERE id=%s"
        DatabaseConnection.global_single_execution(
            query, (match.to_json_state(), match.get_current_player(), now, match_id))

    def apply_move(self, move_data):
        match = self.get_match(move_data['id'])
        if match is None:
            return None

        if not match.move(move_data):
            debug("error applying match move")
            return None

        self.update_match(move_data['id'], match)
        debug("updated match")
        return match

    def is_match(self, player_a, player_b):
        query = "SELECT * FROM matches WHERE (user_a=%s AND user_b=%s) OR (user_a=%s AND user_b=%s)"
        return len(DatabaseConnection.global_single_query(query, (player_a, player_b, player_b, player_a)))

    def delete_match(self, match_id):
        query = "DELETE FROM matches WHERE id=%s"
        DatabaseConnection.global_single_execution(query, (match_id))
