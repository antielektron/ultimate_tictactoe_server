from database_connection import DatabaseConnection, SQLInjectionError, get_sql_time
from user import User
import datetime
import uuid


class SessionManager(object):
    def __init__(self, session_lifespan_timedelta):
        self.session_lifespan_timedelta = session_lifespan_timedelta

    def get_session_by_id(self, session_id):
        query = f"SELECT * FROM sessions WHERE id='{session_id}'"
        return DatabaseConnection.global_single_query(query)

    def touch_session(self, session_id):
        query = f"UPDATE sessions SET last_seen='{datetime.datetime.now()}' WHERE id='{session_id}'"
        DatabaseConnection.global_single_execution(query)

    def get_session_by_registered_user(self, user_name):
        query = f"SELECT * FROM sessions WHERE registered_user='{user_name}'"
        return DatabaseConnection.global_single_query(query)

    def get_session_by_temp_user(self, user_name):
        query = f"SELECT * FROM sessions WHERE temp_user='{user_name}'"
        return DatabaseConnection.global_single_query(query)

    def create_session_for_registered_user(self, user_name):
        new_id = uuid.uuid4().hex
        # check if already existent (but should not be the case)
        if len(DatabaseConnection.global_single_query(f"SELECT id FROM sessions WHERE id='{new_id}'")) > 0:
            # okay, next try:
            return self.create_session_for_registered_user(user_name)
        
        # delete other active sessions:
        query = f"DELETE FROM sessions WHERE registered_user='{user_name}'"
        DatabaseConnection.global_single_execution(query)

        query = f"INSERT INTO sessions (id, registered_user, temp_user, last_seen) VALUES ( '{new_id}', '{user_name}', NULL, '{datetime.datetime.now()}')"
        DatabaseConnection.global_single_execution(query)
        return new_id

    def create_session_for_temp_user(self, user_name):
        new_id = uuid.uuid4().hex
        # check if already existent (but should not be the case)
        if len(DatabaseConnection.global_single_query(f"SELECT id FROM sessions WHERE id='{new_id}'")) > 0:
            # okay, next try:
            return self.create_session_for_registered_user(user_name)
        
        # delete other active sessions:
        query = f"DELETE FROM sessions WHERE temp_user='{user_name}'"
        DatabaseConnection.global_single_execution(query)
        
        query = f"INSERT INTO sessions (id, registered_user, temp_user, last_seen) VALUES ( '{new_id}', NULL, '{user_name}', '{datetime.datetime.now()}')"
        DatabaseConnection.global_single_execution(query)
        return new_id

    def delete_session(self, session_id):
        query = f"DELETE FROM sessions WHERE id='{session_id}'"
        DatabaseConnection.global_single_execution(query)

    def revoke_inactive_sessions(self):
        revoke_time = datetime.datetime.now() - self.session_lifespan_timedelta
        query = f"SELECT * from sessions WHERE last_seen < '{get_sql_time(revoke_time)}'"
        revoked_sessions = DatabaseConnection.global_single_query(query)
        query = f"DELETE FROM sessions WHERE last_seen < '{get_sql_time(revoke_time)}'"
        DatabaseConnection.global_single_execution(query)
        return revoked_sessions
