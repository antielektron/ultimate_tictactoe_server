from database_connection import DatabaseConnection, SQLInjectionError, get_sql_time
from user_manager import UserManager
from user import User
import datetime
import uuid
import settings
from match import Match

from tools import debug, elo_p_win, elo_update


class MatchManager(object):
    def __init__(self, user_manager: UserManager, match_lifespan_timedelta: datetime.timedelta):
        self.user_manager = user_manager
        self.match_lifespan_timedelta = match_lifespan_timedelta

    def get_match(self, id: str) -> Match:
        query = "SELECT * FROM matches WHERE id=%s"
        result = DatabaseConnection.global_single_query(query, (id))
        if len(result) == 0:
            return None

        revoke_time = result[0]['last_active'] + self.match_lifespan_timedelta
        match = Match(n=settings.n, match_id=id, revoke_time=revoke_time, player_a_name=result[0]['user_a'],
                      player_b_name=result[0]['user_b'], json_state=result[0]['match_state'])
        return match

    def get_matches_for_user(self, user_name: str) -> list:
        query = "SELECT * FROM matches WHERE user_a=%s OR user_b=%s"
        return DatabaseConnection.global_single_query(query, (user_name, user_name))

    def create_new_match(self, user_a: str, user_b: str) -> Match:
        match_id = uuid.uuid4().hex
        # check if already existent (but should not be the case)
        if len(DatabaseConnection.global_single_query("SELECT id FROM matches WHERE id=%s", (match_id))) > 0:
            return self.create_new_match(user_a, user_b)

        now = datetime.datetime.now()
        match = Match(n=settings.n, match_id=match_id, revoke_time=now + self.match_lifespan_timedelta,
                      player_a_name=user_a, player_b_name=user_b)
        
        query = "INSERT INTO matches (id, user_a, user_b, match_state, active_user, last_active) VALUES (%s, %s, %s, %s, %s,%s)"
        DatabaseConnection.global_single_execution(
            query, (match_id, user_a, user_b, match.to_json_state(), match.get_current_player(), get_sql_time(now)))
        return match

    def update_match(self, match_id: str, match: Match, update_in_db=True) -> None:

        if (update_in_db):
            now = get_sql_time(datetime.datetime.now())
            query = "UPDATE matches SET match_state=%s, active_user=%s, last_active=%s WHERE id=%s"
            DatabaseConnection.global_single_execution(
                query, (match.to_json_state(), match.get_current_player(), now, match_id))

        # check whether we have to update the elo values (game over triggered by the last move)
        if match.game_over:
            if match.player_won is not None:

                player_won = match.player_won
                player_lost = match.player_a_name if player_won == match.player_b_name else match.player_b_name

                elo_won = self.user_manager.get_elo(player_won)
                elo_lost = self.user_manager.get_elo(player_lost)

                # calculate elo values:
                p_won = elo_p_win(elo_won, elo_lost)
                p_lost = 1 - p_won

                new_elo_won = elo_update(elo_won, 1, p_won)
                new_elo_lost = elo_update(elo_lost, 0, p_lost)

                self.user_manager.update_elo(player_won, new_elo_won)
                self.user_manager.update_elo(player_lost, new_elo_lost)

                debug(
                    f"Match {match_id} is won by {player_won} over {player_lost}. Update elo-rankings: {elo_won}->{new_elo_won} and {elo_lost}->{new_elo_lost}")

            elif match.is_draw:

                elo_a = self.user_manager.get_elo(match.player_a_name)
                elo_b = self.user_manager.get_elo(match.player_b_name)

                p_a_wins = elo_p_win(elo_a, elo_b)
                p_b_wins = 1 - p_a_wins

                new_elo_a = elo_update(elo_a, 0.5, p_a_wins)
                new_elo_b = elo_update(elo_b, 0.5, p_b_wins)

                self.user_manager.update_elo(match.player_a_name, new_elo_a)
                self.user_manager.update_elo(match.player_b_name, new_elo_b)

                debug(
                    f"{match_id} between {match.player_a_name} and {match.player_b_name} ended in draw. Update elo-rankings: {elo_a}->{new_elo_a} and {elo_b}->{new_elo_b}")

            else:
                # someone aborted a match. TODO: apply some penalty to the ranking
                pass

    def apply_move(self, move_data: dict) -> Match:
        match = self.get_match(move_data['id'])
        if match is None:
            return None

        if not match.move(move_data):
            debug("error applying match move")
            return None

        self.update_match(move_data['id'], match)
        debug("updated match")
        return match

    def is_match(self, player_a, player_b) -> bool:
        query = "SELECT * FROM matches WHERE (user_a=%s AND user_b=%s) OR (user_a=%s AND user_b=%s)"
        return len(DatabaseConnection.global_single_query(query, (player_a, player_b, player_b, player_a))) > 0

    def delete_match(self, match_id: str) -> None:
        query = "DELETE FROM matches WHERE id=%s"
        DatabaseConnection.global_single_execution(query, (match_id))

    def check_matches_lifespan(self):
        time_now = datetime.datetime.now()
        time_revoke = time_now - self.match_lifespan_timedelta

        query = "SELECT * FROM matches WHERE last_active < %s"
        tmp = DatabaseConnection.global_single_query(
            query, (get_sql_time(time_revoke)))

        for entry in tmp:
            revoke_time = entry['last_active'] + self.match_lifespan_timedelta
            match = Match(n=settings.n, match_id=entry['id'], revoke_time=revoke_time, player_a_name=entry['user_a'],
                          player_b_name=entry['user_b'], json_state=entry['match_state'])

            if (not match.game_over):
                match.game_over = True

                # check who is the current player who did not make the move in time:
                match.player_won = match.player_b_name if match.is_player_a else match.player_a_name

                self.update_match(entry['id'], match, False)

        # delete matches from db:

        debug("deleting revoked sessions: " + str(tmp))

        query = "DELETE FROM matches WHERE last_active < %s"
        tmp = DatabaseConnection.global_single_execution(
            query, (get_sql_time(time_revoke)))
