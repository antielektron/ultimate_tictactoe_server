import datetime

cert_file = None
key_file = None

server_port = 5556

db_host = "127.0.0.1"
db_port = 3306

db_user = None
db_pw = None
db_db = None

db_charset = 'utf8mb4'

elo_start_value = 1000
elo_default_k = 20

# revoke times:
account_revoke_time = datetime.timedelta(days=45)
session_revove_time = datetime.timedelta(days=20)
temporary_session_revoke_time = datetime.timedelta(hours=1)
match_revoke_time = datetime.timedelta(days=7)

revoke_check_interval = datetime.timedelta(hours=1)

# field dimension (warning: this constant is not constantly used)
n = 3
