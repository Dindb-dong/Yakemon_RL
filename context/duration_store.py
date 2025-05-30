# context/duration_store.py
from typing import List, Dict, Literal, Optional, TYPE_CHECKING
from context.battle_store import store

if TYPE_CHECKING:
    from utils.battle_logics.update_battle_pokemon import remove_status, add_status

TimedEffect = Dict[str, any]
SideType = Literal["my", "enemy", "public", "my_env", "enemy_env"]

special_status = ["하품", "멸망의노래", "사슬묶기"]

class DurationStore:
    def __init__(self):
        self.my_effects: List[TimedEffect] = []
        self.enemy_effects: List[TimedEffect] = []
        self.public_effects: List[TimedEffect] = []
        self.my_env_effects: List[TimedEffect] = []
        self.enemy_env_effects: List[TimedEffect] = []
        
    def reset_all(self) -> None:
        print("duration_store: reset_all 호출")
        self.__init__()
        
    def add_effect(self, effect: TimedEffect, side: SideType):
        """효과 추가"""
        if side == "my":
            self.my_effects.append(effect)
            print(f"my의 효과 추가: {effect['name']}")
        elif side == "enemy":
            self.enemy_effects.append(effect)
            print(f"enemy의 효과 추가: {effect['name']}")
        elif side == "my_env":
            self.my_env_effects.append(effect)
            print(f"my_env의 효과 추가: {effect['name']}")
        elif side == "enemy_env":
            self.enemy_env_effects.append(effect)
            print(f"enemy_env의 효과 추가: {effect['name']}")
        else:
            self.public_effects.append(effect)
            print(f"public의 효과 추가: {effect['name']}")
    def remove_effect(self, effect: TimedEffect, side: SideType):
        """효과 제거"""
        if side == "my":
            if effect in self.my_effects:
                self.my_effects.remove(effect)
                print(f"my의 효과 제거: {effect['name']}")
        elif side == "enemy":
            if effect in self.enemy_effects:
                self.enemy_effects.remove(effect)
                print(f"enemy의 효과 제거: {effect['name']}")
        elif side == "my_env":
            if effect in self.my_env_effects:
                self.my_env_effects.remove(effect)
                print(f"my_env의 효과 제거: {effect['name']}")
        elif side == "enemy_env":
            if effect in self.enemy_env_effects:
                self.enemy_env_effects.remove(effect)
        else:
            if effect in self.public_effects:
                self.public_effects.remove(effect)
                print(f"public의 효과 제거: {effect['name']}")
    def get_effects(self, side: SideType) -> List[TimedEffect]:
        """효과 목록 반환"""
        if side == "my":
            return self.my_effects
        elif side == "enemy":
            return self.enemy_effects
        elif side == "my_env":
            return self.my_env_effects
        elif side == "enemy_env":
            return self.enemy_env_effects
        else:
            return self.public_effects
            
    def update_durations(self):
        """지속 시간 업데이트"""
        for effects in [self.my_effects, self.enemy_effects, self.public_effects, self.my_env_effects, self.enemy_env_effects]:
            for effect in effects[:]:
                if 'duration' in effect:
                    effect['duration'] -= 1
                    if effect['duration'] <= 0:
                        effects.remove(effect)
                        
    def clear_effects(self):
        """모든 효과 제거"""
        self.my_effects.clear()
        self.enemy_effects.clear()
        self.public_effects.clear()
        self.my_env_effects.clear()
        self.enemy_env_effects.clear()

    def decrement_turns(self):
        expired = {"my": [], "enemy": [], "public": [], "my_env": [], "enemy_env": []}

        def dec(effects: List[TimedEffect], side: SideType):
            print(f"\n=== {side}의 효과 처리 시작 ===")
            print(f"처리 전 효과 목록: {effects}")
            new_list = []
            for e in effects:
                if not isinstance(e, dict):
                    print(f"dict가 아닌 효과 발견: {e}")
                    continue
                
                print(f"처리 중인 효과: {e}")
                
                if e["name"] in special_status:
                    print(f"특수 상태 효과 처리: {e['name']}")
                    if self.decrement_special_effect(side, e["owner_index"], e["name"]):
                        expired[side].append(e["name"])
                        print(f"특수 상태 효과 만료: {e['name']}")
                    new_list.append(e)
                elif e["name"] == "잠듦" or e["name"] == "혼란":
                    print(f"잠듦/혼란 효과 유지: {e['name']}")
                    new_list.append(e)
                else:
                    if "remaining_turn" not in e:
                        print(f"remaining_turn이 없는 효과 발견: {e}")
                        continue
                        
                    e["remaining_turn"] -= 1
                    print(f"남은 턴 감소: {e['name']} -> {e['remaining_turn']}턴")
                    
                    if e["remaining_turn"] <= 0:
                        expired[side].append(e["name"])
                        print(f"효과 만료: {e['name']}")
                    else:
                        new_list.append(e)
                        print(f"효과 유지: {e['name']}")
            
            print(f"처리 후 효과 목록: {new_list}")
            print(f"=== {side}의 효과 처리 완료 ===\n")
            return new_list

        self.my_effects = dec(self.my_effects, "my")
        self.enemy_effects = dec(self.enemy_effects, "enemy")
        self.public_effects = dec(self.public_effects, "public")
        self.my_env_effects = dec(self.my_env_effects, "my_env")
        self.enemy_env_effects = dec(self.enemy_env_effects, "enemy_env")

        # 날씨, 필드, 룸 리셋
        for effect in expired["public"]:
            if effect in ["쾌청", "비", "모래바람", "싸라기눈"]:
                print(f"날씨 효과 만료: {effect}")
                store.set_public_env({"weather": None})
            elif effect in ["그래스필드", "미스트필드", "사이코필드", "일렉트릭필드"]:
                print(f"필드 효과 만료: {effect}")
                store.set_public_env({"field": None})
            elif effect in ["트릭룸", "매직룸", "원더룸"]:
                print(f"룸 효과 만료: {effect}")
                store.set_public_env({"room": None})

        return expired

    def transfer_effects(self, side: Literal["my", "enemy"], from_idx: int, to_idx: int): # 바톤터치
        effects = self.get_effects(side)
        transfer_list = [e for e in effects if e.get("owner_index") == from_idx]
        for eff in transfer_list:
            self.remove_effect(eff, side)
            self.add_effect({**eff, "owner_index": to_idx}, side)

    def decrement_special_effect(self, side: SideType, index: int, status: str, on_expire=None):
        effects = self.get_effects(side)

        effect = next((e for e in effects if e["name"] == status), None)
        if not effect:
            return False

        next_turn = effect["remaining_turn"] - 1
        if next_turn <= 0:
            self.remove_effect(effect, side)
            store.update_pokemon(side, index, lambda p: remove_status(p, status))
            if on_expire:
                on_expire()
            return True
        else:
            self.add_effect({"name": status, "remaining_turn": next_turn, "owner_index": index}, side)
            return False

    def decrement_yawn_turn(self, side: SideType, index: int):
        return self.decrement_special_effect(side, index, "하품", lambda: 
            store.update_pokemon(side, index, lambda p: add_status(p, "잠듦", side))
        )

    def decrement_confusion_turn(self, side: SideType, index: int):
        return self.decrement_special_effect(side, index, "혼란")

    def decrement_sleep_turn(self, side: SideType, index: int):
        return self.decrement_special_effect(side, index, "잠듦")

    def decrement_disable_turn(self, side: SideType, index: int):
        return self.decrement_special_effect(side, index, "사슬묶기", lambda: (
            store.update_pokemon(side, index, lambda p: p.copy_with(un_usable_move=None)),
            store.add_log("사슬묶기 상태가 풀렸다!")
        ))

# 싱글톤으로 관리
duration_store = DurationStore()