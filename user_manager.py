from database_connection import DatabaseConnection, SQLInjectionError
from user import User
import datetime
import hashlib
import uuid
from settings import elo_start_value


class UserManager(object):
    def __init__(self):
        pass

    def get_user(self, user_name):
        query = "SELECT name, last_seen FROM users where name=%s"
        return DatabaseConnection.global_single_query(query, (user_name))

    def delete_user(self, user_name):

        # remove from friends:
        query = "DELETE FROM friends WHERE user=%s"
        DatabaseConnection.global_single_execution(query, (user_name))

        query = "DELETE FROM friends WHERE friend=%s"
        DatabaseConnection.global_single_execution(query, (user_name))

        # remove from sessions:
        query = "DELETE FROM sessions WHERE registered_user=%s"
        DatabaseConnection.global_single_execution(query, (user_name))

        # remove from matches:
        query = "DELETE FROM matches WHERE user_a=%s OR user_b=%s"
        DatabaseConnection.global_single_execution(query, (user_name, user_name))

        # finally remove user

        query = "DELETE FROM users where name=%s"
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
        query = "INSERT INTO users (name, pw_hash, pw_salt, last_seen, elo) VALUES ( %s, %s, %s, %s, %s)"
        DatabaseConnection.global_single_execution(
            query, (user_name, pw_hash, pw_salt, datetime.datetime.now(), elo_start_value))

    def touch_user(self, user_name):
        matches = self.get_user(user_name)
        assert len(matches) == 1
        query = "UPDATE users SET last_seen=%s WHERE name=%s"
        DatabaseConnection.global_single_execution(
            query, (datetime.datetime.now(), user_name))

    def update_elo(self, user_name, new_elo):
        query = "UPDATE users SET elo=%s WHERE name=%s"
        DatabaseConnection.global_single_execution(query, (new_elo, user_name))

    def get_elo(self, user_name):
        query = "SELECT elo FROM users WHERE name=%s"
        q = DatabaseConnection.global_single_query(query, (user_name))
        if len(q) > 0:
            return q[0]['elo']

        return None

    def get_average_elo(self):
        query = "SELECT AVG(elo) AS average FROM users"
        q = DatabaseConnection.global_single_query(query)
        if len(q) > 0:
            return float(q[0]['average'])

        return None
    
    def get_highscores(self, n, list_offset):
        query = "SELECT name, elo FROM users ORDER BY elo DESC LIMIT %s OFFSET %s"
        q = DatabaseConnection.global_single_query(query, (n, list_offset))
        names = []
        elos = []
        for entry in q:
            names.append(entry['name'])
            elos.append(int(entry['elo']))
        
        return names, elos
    
    def get_rank_for_user(self, user_name):
        query = "SELECT Count(*)+1 as rank  from users where elo >(SELECT elo from users WHERE name=%s)"
        q = DatabaseConnection.global_single_query(query, (user_name))
        return int(q[0]['rank'])

    def add_friend_to_user(self, user_name, friend_name):
        if len(self.get_user(friend_name)) > 0:
            query = "INSERT INTO friends (user, friend) VALUES ( %s, %s)"
            DatabaseConnection.global_single_execution(
                query, (user_name, friend_name))
            return True
        return False

    def get_friends_for_user(self, user_name):
        query = "SELECT friend FROM friends WHERE user=%s"
        tmp = DatabaseConnection.global_single_query(query, (user_name))
        friends = set()
        for entry in tmp:
            friends.add(entry['friend'])
        return list(friends)

    def get_friends_and_elos_for_user(self, user_name):
        query = "SELECT friends.friend AS friend, users.elo AS elo FROM friends JOIN users ON friends.friend=users.name WHERE friends.user=%s"
        tmp = DatabaseConnection.global_single_query(query, (user_name))
        friends = []
        elos = []
        for entry in tmp:
            friends.append(entry['friend'])
            elos.append(entry['elo'])
        return friends, elos

    def remove_friend_from_user(self, user_name, friend_name):
        query = "DELETE FROM friends WHERE user=%s AND friend=%s"
        DatabaseConnection.global_single_execution(
            query, (user_name, friend_name))

    def get_all_users(self):
        query = "SELECT name, last_seen FROM users"
        return DatabaseConnection.global_single_query(query)
