from database_connection import DatabaseConnection, SQLInjectionError, get_sql_time
from user import User
import datetime
import uuid

from tools import debug


class SessionManager(object):
    def __init__(self, session_lifespan_timedelta):
        self.session_lifespan_timedelta = session_lifespan_timedelta

    def get_session_by_id(self, session_id):
        query = "SELECT * FROM sessions WHERE id=%s"
        return DatabaseConnection.global_single_query(query, (session_id))

    def touch_session(self, session_id):
        query = "UPDATE sessions SET last_seen=%s WHERE id=%s"
        DatabaseConnection.global_single_execution(query, (datetime.datetime.now(), session_id))

    def get_session_by_registered_user(self, user_name):
        query = "SELECT * FROM sessions WHERE registered_user=%s"
        return DatabaseConnection.global_single_query(query, (user_name))

    def get_session_by_temp_user(self, user_name):
        query = "SELECT * FROM sessions WHERE temp_user=%s"
        return DatabaseConnection.global_single_query(query, (user_name))

    def create_session_for_registered_user(self, user_name):
        new_id = uuid.uuid4().hex
        # check if already existent (but should not be the case)
        if len(DatabaseConnection.global_single_query("SELECT id FROM sessions WHERE id=%s", (str(new_id)))) > 0:
            # okay, next try:
            return self.create_session_for_registered_user(user_name)

        # delete other active sessions:
        query = "DELETE FROM sessions WHERE registered_user=%s"
        DatabaseConnection.global_single_execution(query, (user_name))

        query = "INSERT INTO sessions (id, registered_user, temp_user, last_seen) VALUES ( %s, %s, NULL, %s)"
        DatabaseConnection.global_single_execution(query, (new_id, user_name, datetime.datetime.now()))

        return new_id

    def create_session_for_temp_user(self, user_name):
        new_id = uuid.uuid4().hex
        # check if already existent (but should not be the case)
        if len(DatabaseConnection.global_single_query("SELECT id FROM sessions WHERE id=%s", (new_id))) > 0:
            # okay, next try:
            return self.create_session_for_registered_user(user_name)

        # delete other active sessions:
        query = "DELETE FROM sessions WHERE temp_user=%s"
        DatabaseConnection.global_single_execution(query, (user_name))

        query = "INSERT INTO sessions (id, registered_user, temp_user, last_seen) VALUES ( %s, NULL, %s, %s)"
        DatabaseConnection.global_single_execution(query, (new_id, user_name, datetime.datetime.now()))
        return new_id

    def delete_session(self, session_id):
        query = "DELETE FROM sessions WHERE id=%s"
        DatabaseConnection.global_single_execution(query, (session_id))

    def revoke_inactive_sessions(self):
        revoke_time = datetime.datetime.now() - self.session_lifespan_timedelta
        query = "SELECT * from sessions WHERE last_seen < %s"
        revoked_sessions = DatabaseConnection.global_single_query(query, (get_sql_time(revoke_time)))
        query = "DELETE FROM sessions WHERE last_seen < %s"
        DatabaseConnection.global_single_execution(query, (get_sql_time(revoke_time)))
        debug("delete revoked sessions: " + str(revoked_sessions))
    

