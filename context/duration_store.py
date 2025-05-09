# context/duration_store.py
from typing import List, Dict, Literal, Optional
from context.battle_store import battle_store_instance as store
from utils.battle_logics.update_battle_pokemon import add_status, remove_status

TimedEffect = Dict[str, any]
SideType = Literal["my", "enemy", "public"]

special_status = ["하품", "멸망의노래", "사슬묶기"]

class DurationStore:
    def __init__(self):
        self.state = {
            "my_effects": [],
            "enemy_effects": [],
            "public_effects": [],
            "my_env_effects": [],
            "enemy_env_effects": [],
        }

    def add_effect(self, target: SideType, effect: TimedEffect):
        key = f"{target}Effects"
        effects = self.state.get(key, [])
        effects = [e for e in effects if e["name"] != effect["name"]] + [effect]
        self.state[key] = effects

    def remove_effect(self, target: SideType, effect_name: str):
        key = f"{target}Effects"
        effects = self.state.get(key, [])
        self.state[key] = [e for e in effects if e["name"] != effect_name]

    def add_env_effect(self, target: Literal["my", "enemy"], effect: TimedEffect):
        key = f"{target}EnvEffects"
        effects = self.state.get(key, [])
        effects = [e for e in effects if e["name"] != effect["name"]] + [effect]
        self.state[key] = effects

    def remove_env_effect(self, target: Literal["my", "enemy"], effect_name: str):
        key = f"{target}EnvEffects"
        effects = self.state.get(key, [])
        self.state[key] = [e for e in effects if e["name"] != effect_name]

    def decrement_turns(self):
        expired = {"my": [], "enemy": [], "public": [], "my_env": [], "enemy_env": []}

        def dec(effects, side):
            new_list = []
            for e in effects:
                if e["name"] in special_status:
                    if self.decrement_special_effect(side, e["owner_index"], e["name"]):
                        expired[side].append(e["name"])
                    new_list.append(e)
                elif e["name"] == "잠듦" or e["name"] == "혼란":
                    new_list.append(e)
                else:
                    e["remaining_turn"] -= 1
                    if e["remaining_turn"] <= 0:
                        expired[side].append(e["name"])
                    else:
                        new_list.append(e)
            return new_list

        self.state["my_effects"] = dec(self.state["my_effects"], "my")
        self.state["enemy_effects"] = dec(self.state["enemy_effects"], "enemy")
        self.state["public_effects"] = dec(self.state["public_effects"], "public")
        self.state["my_env_effects"] = dec(self.state["my_env_effects"], "my_env")
        self.state["enemy_env_effects"] = dec(self.state["enemy_env_effects"], "enemy_env")

        # 날씨, 필드, 룸 리셋
        for effect in expired["public"]:
            if effect in ["쾌청", "비", "모래바람", "싸라기눈"]:
                store.set_public_env({"weather": None})
            elif effect in ["그래스필드", "미스트필드", "사이코필드", "일렉트릭필드"]:
                store.set_public_env({"field": None})
            elif effect in ["트릭룸", "매직룸", "원더룸"]:
                store.set_public_env({"room": None})

        return expired

    def transfer_effects(self, side: Literal["my", "enemy"], from_idx: int, to_idx: int):
        key = "my_effects" if side == "my" else "enemy_effects"
        effects = self.state.get(key, [])
        transfer_list = [e for e in effects if e.get("owner_index") == from_idx]
        for eff in transfer_list:
            self.remove_effect(side, eff["name"])
            self.add_effect(side, {**eff, "owner_index": to_idx})

    def decrement_special_effect(self, side: SideType, index: int, status: str, on_expire=None):
        effects = self.state["my_effects"] if side == "my" else self.state["enemy_effects"]

        effect = next((e for e in effects if e["name"] == status), None)
        if not effect:
            return False

        next_turn = effect["remaining_turn"] - 1
        if next_turn <= 0:
            self.remove_effect(side, status)
            store.update_pokemon(side, index, lambda p: remove_status(p, status))
            if on_expire:
                on_expire()
            return True
        else:
            self.add_effect(side, {"name": status, "remaining_turn": next_turn, "owner_index": index})
            return False

    def decrement_yawn_turn(self, side, index):
        return self.decrement_special_effect(side, index, "하품", lambda: 
            store.update_pokemon(side, index, lambda p: add_status(p, "잠듦", side))
        )

    def decrement_confusion_turn(self, side, index):
        return self.decrement_special_effect(side, index, "혼란")

    def decrement_sleep_turn(self, side, index):
        return self.decrement_special_effect(side, index, "잠듦")

    def decrement_disable_turn(self, side, index):
        return self.decrement_special_effect(side, index, "사슬묶기", lambda: (
            store.update_pokemon(side, index, lambda p: p.deepcopy(un_usable_move=None)),
            store.add_log("사슬묶기 상태가 풀렸다!")
        ))

# 싱글톤으로 관리
duration_store = DurationStore()