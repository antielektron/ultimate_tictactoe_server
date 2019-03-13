from database_connection import DatabaseConnection, SQLInjectionError, get_sql_time
from user import User
import datetime
import uuid
import settings
from match import Match


class MatchManager(object):
    def __init__(self):
        pass

    def get_match(self, id):
        query = f"SELECT * FROM matches WHERE id='{id}'"
        result = DatabaseConnection.global_single_query(query)
        if len(result) == 0:
            return None
        match = Match(n=settings.n, match_id=id, player_a_name=result[0]['user_a'],
                      player_b_name=result[0]['user_b'], json_state=result[0]['match_state'])
        return match

    def get_matches_for_user(self, user_name):
        query = f"SELECT * FROM matches WHERE user_a='{user_name}' OR user_b='{user_name}'"
        return DatabaseConnection.global_single_query(query)

    def create_new_match(self, user_a, user_b):
        match_id = uuid.uuid4().hex
        # check if already existent (but should not be the case)
        if len(DatabaseConnection.global_single_query(f"SELECT id FROM matches WHERE id='{match_id}'")) > 0:
            return self.create_new_match(user_a, user_b)

        match = Match(n=settings.n, match_id=match_id, player_a_name=user_a, player_b_name=user_b)
        now = datetime.datetime.now()
        query = f"INSERT INTO matches (id, user_a, user_b, match_state, active_user, last_active) VALUES ('{match_id}', '{user_a}', '{user_b}', '{match.to_json_state()}', '{match.get_current_player()}','{get_sql_time(now)}')"
        DatabaseConnection.global_single_execution(query)
        return match
    
    def update_match(self, match_id, match):
        now = get_sql_time(datetime.datetime.now())
        query = f"UPDATE matches SET match_state='{match.to_json_state()}', active_user='{match.get_current_player()}', last_active='{now}' WHERE id='{match_id}'"
        DatabaseConnection.global_single_execution(query)
    
    def delete_match(self, match_id):
        query = f"DELETE FROM matches WHERE id='{match_id}'"
        DatabaseConnection.global_single_execution(query)

