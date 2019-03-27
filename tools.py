import datetime


def debug(msg):
    print("[" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "]: " + msg)
