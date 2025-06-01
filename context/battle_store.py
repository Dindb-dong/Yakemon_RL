from typing import List, Optional, Dict, Callable, Literal, Any, TypedDict
from copy import deepcopy

from p_models.battle_pokemon import BattlePokemon
from context.battle_environment import PublicBattleEnvironment, IndividualBattleEnvironment
from context.form_check_wrapper import with_form_check

SideType = Literal["my", "enemy"]

class BattleStoreState(TypedDict):
    my_team: List[BattlePokemon]
    enemy_team: List[BattlePokemon]
    active_my: int
    active_enemy: int
    public_env: PublicBattleEnvironment
    my_env: IndividualBattleEnvironment
    enemy_env: IndividualBattleEnvironment
    turn: int
    logs: List[str]
    is_switch_waiting: bool
    switch_request: Optional[Dict[str, Any]]
    pre_damage_list: List[tuple]

class BattleStore:
    def __init__(self) -> None:
        self.state: BattleStoreState = {
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
            "pre_damage_list": [],
        }
        
    def copy(self) -> "BattleStore":
        return deepcopy(self)

    def set_my_team(self, team: List[BattlePokemon]) -> None:
        self.state["my_team"] = team

    def set_enemy_team(self, team: List[BattlePokemon]) -> None:
        self.state["enemy_team"] = team
        
    def set_active_index(self, side: SideType, index: int) -> None:
        if side == "my":
            self.state["active_my"] = index
        else:
            self.state["active_enemy"] = index

    def set_active_my(self, index: int) -> None:
        self.state["active_my"] = index

    def set_active_enemy(self, index: int) -> None:
        self.state["active_enemy"] = index

    def set_public_env(self, env_update: Dict[str, Any]) -> None:
        for key, value in env_update.items():
            if hasattr(self.state["public_env"], key):
                setattr(self.state["public_env"], key, value)

    def set_my_env(self, env_update: Dict[str, Any]) -> None:
        for key, value in env_update.items():
            if hasattr(self.state["my_env"], key):
                setattr(self.state["my_env"], key, value)

    def set_enemy_env(self, env_update: Dict[str, Any]) -> None:
        for key, value in env_update.items():
            if hasattr(self.state["enemy_env"], key):
                setattr(self.state["enemy_env"], key, value)

    def update_pokemon(self, side: SideType, index: int, updater: Callable[[BattlePokemon], BattlePokemon]) -> None:
        if side not in ["my", "enemy"]:
            raise ValueError("Invalid side type")
        team_key = "my_team" if side == "my" else "enemy_team"
        if not 0 <= index < len(self.state[team_key]):
            raise IndexError("Invalid pokemon index")
        team = self.state[team_key]
        team[index] = updater(team[index])
        self.state[team_key] = team

    def set_turn(self, turn: int) -> None:
        self.state["turn"] = turn

    def add_log(self, log: str) -> None:
        self.state["logs"].append(log)

    def set_switch_request(self, req: Dict[str, Any]) -> None:
        self.state["is_switch_waiting"] = True
        self.state["switch_request"] = req

    def clear_switch_request(self) -> None:
        self.state["is_switch_waiting"] = False
        self.state["switch_request"] = None

    def set_win_count(self, count: int) -> None:
        self.state["win_count"] = count

    def set_enemy_roster(self, roster: List[BattlePokemon]) -> None:
        self.state["enemy_roster"] = roster

    def reset_all(self) -> None:
        print("battle_store: reset_all 호출")
        self.__init__()

    def get_state(self) -> Dict[str, Any]:
        return self.state
    
    def get_team(self, side: SideType) -> List[BattlePokemon]:
        return self.state["my_team"] if side == "my" else self.state["enemy_team"]

    def get_active_index(self, side: SideType) -> int:
        return self.state["active_my"] if side == "my" else self.state["active_enemy"]

    def set_pre_damage_list(self, pre_damage_list: List[tuple]) -> None:
        self.state["pre_damage_list"] = pre_damage_list

    def get_pre_damage_list(self) -> List[tuple]:
        return self.state["pre_damage_list"]

# 전역 인스턴스 생성
battle_store_instance = BattleStore()
store: BattleStore = with_form_check(lambda set_state, get_state, api: api)(
    lambda s: setattr(battle_store_instance, "state", s),
    lambda: battle_store_instance.get_state(),
    battle_store_instance
)