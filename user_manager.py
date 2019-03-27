from database_connection import DatabaseConnection, SQLInjectionError
from user import User
import datetime
import hashlib
import uuid


class UserManager(object):
    def __init__(self):
        pass

    def get_user(self, user_name):
        query = "SELECT name, last_seen FROM users where name=%s"
        return DatabaseConnection.global_single_query(query, (user_name))

    def delete_user(self, user_name):
        query = "DELETE FROM users where name=%s"
        DatabaseConnection.global_single_execution(query, (user_name))

        # remove from friends:
        query = "DELETE FROM friends WHERE user=%s"
        DatabaseConnection.global_single_execution(query, (user_name))

        query = "DELETE FROM friends WHERE friend=%s"
        DatabaseConnection.global_single_execution(query, (user_name))

    def verify_user(self, user_name, pw):
        query = "SELECT * FROM users where name=%s"
        users = DatabaseConnection.global_single_query(query, (user_name))
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
        query = "INSERT INTO users (name, pw_hash, pw_salt, last_seen) VALUES ( %s, %s, %s, %s)"
        DatabaseConnection.global_single_execution(query, (user_name, pw_hash, pw_salt, datetime.datetime.now()))
    
    def touch_user(self, user_name):
        matches = self.get_user(user_name)
        assert len(matches) == 1
        query = "UPDATE users SET last_seen=%s WHERE name=%s"
        DatabaseConnection.global_single_execution(query, (datetime.datetime.now(), user_name))
    
    def add_friend_to_user(self, user_name, friend_name):
        if len(self.get_user(friend_name)) > 0:
            query = "INSERT INTO friends (user, friend) VALUES ( %s, %s)"
            DatabaseConnection.global_single_execution(query, (user_name, friend_name))
            return True
        return False
    
    def get_friends_for_user(self, user_name):
        query = "SELECT friend FROM friends WHERE user=%s"
        tmp = DatabaseConnection.global_single_query(query, (user_name))
        friends = set()
        for entry in tmp:
            friends.add(entry['friend'])
        return friends
    
    def remove_friend_from_user(self, user_name, friend_name):
        query = "DELETE FROM friends WHERE user=%s AND friend=%s"
        DatabaseConnection.global_single_execution(query, (user_name, friend_name))

    def get_all_users(self):
        query = "SELECT name, last_seen FROM users"
        return DatabaseConnection.global_single_query(query)

