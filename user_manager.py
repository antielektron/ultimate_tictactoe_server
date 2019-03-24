from database_connection import DatabaseConnection, SQLInjectionError
from user import User
import datetime
import hashlib
import uuid


class UserManager(object):
    def __init__(self):
        pass

    def get_user(self, user_name):
        query = f"SELECT name, last_seen FROM users where name='{user_name}'"
        return DatabaseConnection.global_single_query(query)

    def delete_user(self, user_name):
        query = f"DELETE FROM users where name='{user_name}'"
        DatabaseConnection.global_single_execution(query)

        # remove from friends:
        query = f"DELETE FROM friends WHERE user='{user_name}'"
        DatabaseConnection.global_single_execution(query)

        query = f"DELETE FROM friends WHERE friend='{user_name}'"
        DatabaseConnection.global_single_execution(query)

    def verify_user(self, user_name, pw):
        query = f"SELECT * FROM users where name='{user_name}'"
        users = DatabaseConnection.global_single_query(query)
        if len(self.get_user(user_name)) == 0:
            return False

        user = users[0]
        pw_salt = user['pw_salt']
        stored_pw_hash = user['pw_hash']

        pw_hash = hashlib.sha512(pw.encode() + pw_salt.encode()).hexdigest()
        return stored_pw_hash == pw_hash

    def create_user(self, user_name, pw):
        assert len(self.get_user(user_name)) == 0
        pw_salt = uuid.uuid4().hex
        pw_hash = hashlib.sha512(pw.encode() + pw_salt.encode()).hexdigest()
        query = f"INSERT INTO users (name, pw_hash, pw_salt, last_seen) VALUES ( '{user_name}', '{pw_hash}', '{pw_salt}', '{datetime.datetime.now()}')"
        DatabaseConnection.global_single_execution(query)
    
    def touch_user(self, user_name):
        matches = self.get_user(user_name)
        assert len(matches) == 1
        query = f"UPDATE users SET last_seen='{datetime.datetime.now()}' WHERE name='{user_name}'"
        DatabaseConnection.global_single_execution(query)
    
    def add_friend_to_user(self, user_name, friend_name):
        if len(self.get_user(friend_name)) > 0:
            query = f"INSERT INTO friends (user, friend) VALUES ( '{user_name}', '{friend_name}')"
            DatabaseConnection.global_single_execution(query)
            return True
        return False
    
    def get_friends_for_user(self, user_name):
        query = f"SELECT friend FROM friends WHERE user='{user_name}'"
        tmp = DatabaseConnection.global_single_query(query)
        friends = set()
        for entry in tmp:
            friends.add(entry['friend'])
        return friends
    
    def remove_friend_from_user(self, user_name, friend_name):
        query = f"DELETE FROM friends WHERE user='{user_name}' AND friend='{friend_name}'"
        DatabaseConnection.global_single_execution(query)

    def get_all_users(self):
        query = "SELECT name, last_seen FROM users"
        return DatabaseConnection.global_single_query(query)

