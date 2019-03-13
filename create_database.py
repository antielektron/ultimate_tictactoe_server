#!/usr/bin/env python3
# this script creates the necessary tables in the databse

import settings
from database_connection import DatabaseConnection


def create_tables():

    DatabaseConnection(settings.db_host,
                       settings.db_port,
                       settings.db_user,
                       settings.db_pw,
                       settings.db_db,
                       settings.db_charset)

    queries = [
        "DROP TABLE IF EXISTS matches",
        "DROP TABLE IF EXISTS sessions",
        "DROP TABLE IF EXISTS users",
        "CREATE TABLE users (name varchar(16) NOT NULL, pw_hash varchar(128) NOT NULL, pw_salt varchar(32) NOT NULL, last_seen datetime NOT NULL, PRIMARY KEY (name)) CHARACTER SET " + settings.db_charset,
        "CREATE TABLE matches (id varchar(32) NOT NULL, user_a varchar(16) NOT NULL, user_b varchar(16) NOT NULL, match_state varchar(4096) NOT NULL, active_user varchar(16), last_active datetime NOT NULL, FOREIGN KEY (user_a) REFERENCES users(name), FOREIGN KEY (user_b) REFERENCES users(name), FOREIGN KEY (active_user) REFERENCES users(name)) CHARACTER SET " + settings.db_charset,
        "CREATE TABLE sessions (id varchar(32) NOT NULL, registered_user varchar(16), temp_user varchar(16), last_seen datetime NOT NULL, PRIMARY KEY (id), FOREIGN KEY(registered_user) REFERENCES users(name)) CHARACTER SET " + settings.db_charset
    ]

    for query in queries:
        DatabaseConnection.global_single_execution(query)

    DatabaseConnection.global_close()


if __name__ == "__main__":
    create_tables()
