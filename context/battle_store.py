from typing import List, Optional, Dict, Callable, Literal
from copy import deepcopy

from p_models.battle_pokemon import BattlePokemon
from context.battle_environment import PublicBattleEnvironment, IndividualBattleEnvironment
from context.form_check_wrapper import with_form_check

SideType = Literal["my", "enemy"]

class BattleStore:
    def __init__(self):
        self.state = {
            "my_team": [],
            "enemy_team": [],
            "active_my": 0,
            "active_enemy": 0,
            "public_env": PublicBattleEnvironment(),
            "my_env": IndividualBattleEnvironment(),
            "enemy_env": IndividualBattleEnvironment(),
            "turn": 1,
            "logs": [],
            "is_switch_waiting": False,
            "switch_request": None,
            "win_count": 0,
            "enemy_roster": [],
        }

    def set_my_team(self, team: List[BattlePokemon]):
        self.state["my_team"] = team

    def set_enemy_team(self, team: List[BattlePokemon]):
        self.state["enemy_team"] = team

    def set_active_my(self, index: int):
        self.state["active_my"] = index

    def set_active_enemy(self, index: int):
        self.state["active_enemy"] = index

    def set_public_env(self, env_update: Dict):
        for key, value in env_update.items():
            if hasattr(self.state["public_env"], key):
                setattr(self.state["public_env"], key, value)

    def set_my_env(self, env_update: Dict):
        for key, value in env_update.items():
            if hasattr(self.state["my_env"], key):
                setattr(self.state["my_env"], key, value)

    def set_enemy_env(self, env_update: Dict):
        for key, value in env_update.items():
            if hasattr(self.state["enemy_env"], key):
                setattr(self.state["enemy_env"], key, value)

    def update_pokemon(self, side: SideType, index: int, updater: Callable[[BattlePokemon], BattlePokemon]):
        if side not in ["my", "enemy"]:
            raise ValueError("Invalid side type")
        team_key = "my_team" if side == "my" else "enemy_team"
        if not 0 <= index < len(self.state[team_key]):
            raise IndexError("Invalid pokemon index")
        team = self.state[team_key]
        team[index] = updater(team[index])
        self.state[team_key] = team

    def set_turn(self, turn: int):
        self.state["turn"] = turn

    def add_log(self, log: str):
        self.state["logs"].append(log)

    def set_switch_request(self, req: Dict):
        self.state["is_switch_waiting"] = True
        self.state["switch_request"] = req

    def clear_switch_request(self):
        self.state["is_switch_waiting"] = False
        self.state["switch_request"] = None

    def set_win_count(self, count: int):
        self.state["win_count"] = count

    def set_enemy_roster(self, roster: List[BattlePokemon]):
        self.state["enemy_roster"] = roster

    def reset_all(self):
        self.__init__()


BattleStoreWithFormCheck = with_form_check(BattleStore)
battle_store_instance = BattleStoreWithFormCheck()