import pymysql.cursors
import sys


def get_sql_time(datetime_object):
    return datetime_object.strftime('%Y-%m-%d %H:%M:%S')


class SQLInjectionError(Exception):
    def __init__(self):

        # Call the base class constructor with the parameters it needs
        super().__init__("Detected possible SQL injection attack!")


class DatabaseConnection(object):
    """
    a singleton class for a global database connection
    """

    instance = None

    @staticmethod
    def global_cursor():
        assert DatabaseConnection.instance is not None
        return DatabaseConnection.instance.get_cursor()

    @staticmethod
    def global_close():
        assert DatabaseConnection.instance is not None
        DatabaseConnection.instance.close()

    @staticmethod
    def global_commit():
        assert DatabaseConnection.instance is not None
        DatabaseConnection.instance.commit()

    @staticmethod
    def global_single_query(query):
        if ';' in query:
            # Possible injection!
            raise SQLInjectionError()

        with DatabaseConnection.global_cursor() as c:
            c.execute(query)
            return c.fetchall()

    @staticmethod
    def global_single_execution(sql_statement):
        if ';' in sql_statement:
            # Possible injection detected!
            raise SQLInjectionError()

        with DatabaseConnection.global_cursor() as c:
            c.execute(sql_statement)
            DatabaseConnection.global_commit()

    def __init__(self,
                 host: str,
                 port: int,
                 user: str,
                 password: str,
                 db: str,
                 charset: str):

        assert DatabaseConnection.instance is None
        try:
            self.connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                db=db,
                charset=charset,
                cursorclass=pymysql.cursors.DictCursor)
            DatabaseConnection.instance = self
        except Exception as e:
            sys.stderr.write("could not connect to database '" +
                             str(db) +
                             "' at " +
                             user +
                             "@" +
                             host +
                             ":" +
                             str(port) +
                             "\nCheck the configuration in settings.py!\n")
            raise Exception('could not connec to database')

    def get_cursor(self):
        return self.connection.cursor()

    def close(self):
        self.connection.close()
        DatabaseConnection.instance = None

    def commit(self):
        self.connection.commit()

def test_connection():
    import settings
    DatabaseConnection(settings.db_host,
                       settings.db_port,
                       settings.db_user,
                       settings.db_pw,
                       settings.db_db,
                       settings.db_charset)