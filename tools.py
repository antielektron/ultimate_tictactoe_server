import datetime
from settings import elo_default_k


def debug(msg: str) -> None:
    print("[" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "]: " + msg)


def elo_p_win(player_elo: int, opponent_elo: int) -> float:
    return (1 / (1 + 10**((opponent_elo - player_elo)/400)))


def elo_update(old_elo: int, single_game_result: float, expected_result: float, k: float = elo_default_k) -> int:
    new_elo = old_elo + k * (single_game_result - expected_result)
    return round(new_elo)
