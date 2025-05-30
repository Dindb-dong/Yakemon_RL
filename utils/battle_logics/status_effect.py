from typing import List, Dict, Optional, Literal, Tuple, Union
from p_models.move_info import MoveInfo
from p_models.status import StatusState
from context.battle_store import store
from context.duration_store import duration_store
from utils.battle_logics.update_battle_pokemon import change_hp, remove_status
import random

SideType = Literal["my", "enemy"]

def apply_status_effect_before(
    status: List[StatusState],
    current_rate: float,
    move: MoveInfo,
    side: SideType
) -> Dict[str, Union[float, bool]]:
    state = store.get_state()
    my_team = state["my_team"]
    enemy_team = state["enemy_team"]
    active_my = state["active_my"]
    active_enemy = state["active_enemy"]
    
    active_team = my_team if side == "my" else enemy_team
    active_index = active_my if side == "my" else active_enemy
    can_act = True
    
    for s in status:
        if s == "풀죽음":
            if not can_act:
                break
            store.add_log(f"{active_team[active_index].base.name}은/는 풀이 죽어서 기술 사용에 실패했다!")
            print(f"{active_team[active_index].base.name}은/는 풀이 죽어서 기술 사용에 실패했다!")
            can_act = False
            
        elif s == "잠듦":
            print(f"잠듦 체크")
            sleep_list = duration_store.get_effects(side)
            sleep_effect = next((e for e in sleep_list if e['name'] == "잠듦"), None)
            
            if not sleep_effect or not sleep_effect['remaining_turn']:
                duration_store.remove_effect("잠듦", side)
                store.update_pokemon(side, active_index, lambda p: remove_status(p, "잠듦"))
                store.add_log(f"🏋️‍♂️ {active_team[active_index].base.name}은/는 잠에서 깼다!")
                print(f"🏋️‍♂️ {active_team[active_index].base.name}은/는 잠에서 깼다!")
            else:
                remaining = sleep_effect['remaining_turn']
                recovery_chance = 0
                
                if remaining == 2:
                    recovery_chance = 1/300
                elif remaining == 1:
                    recovery_chance = 1/200
                elif remaining <= 0:
                    recovery_chance = 1
                    
                if random.random() < recovery_chance:
                    duration_store.remove_effect("잠듦", side)
                    store.update_pokemon(side, active_index, lambda p: remove_status(p, "잠듦"))
                    store.add_log(f"🏋️‍♂️ {active_team[active_index].base.name}은/는 잠에서 깼다!")
                    print(f"🏋️‍♂️ {active_team[active_index].base.name}은/는 잠에서 깼다!")
                else:
                    can_act = False
                    duration_store.add_effect({
                        "name": "잠듦",
                        "remaining_turn": sleep_effect['remaining_turn'] - 1,
                        "owner_index": sleep_effect['owner_index']
                    }, side)
                    
        elif s == "마비":
            print(f"마비 체크")
            if not can_act:
                break
            if random.random() < 0.25:
                can_act = False
                store.add_log(f"{active_team[active_index].base.name}은/는 몸이 저렸다!")
                print(f"{active_team[active_index].base.name}은/는 몸이 저렸다!")
            else:
                can_act = True
                
        elif s == "얼음":
            print(f"얼음 체크")
            if random.random() < 0.2 or move.type == "불":
                store.update_pokemon(side, active_index, lambda p: remove_status(p, "얼음"))
                store.add_log(f"🏋️‍♂️ {active_team[active_index].base.name}의 얼음이 녹았다!")
                print(f"{active_team[active_index].base.name}의 얼음이 녹았다!")
                can_act = True
            else:
                store.add_log(f"☃️ {active_team[active_index].base.name}은/는 얼어있다!")
                print(f"{active_team[active_index].base.name}은/는 얼어있다!")
                can_act = False
                
        elif s == "혼란":
            print(f"혼란 체크")
            recovered = duration_store.decrement_confusion_turn(side, active_index)
            if recovered:
                can_act = True
                store.add_log(f"🏋️‍♂️ {active_team[active_index].base.name}은/는 혼란에서 깼다!")
                print(f"{active_team[active_index].base.name}은/는 혼란에서 깼다!")
            else:
                store.add_log(f"😵‍💫 {active_team[active_index].base.name}은/는 혼란에 빠져있다!")
                print(f"{active_team[active_index].base.name}은/는 혼란에 빠져있다!")
                if random.random() < 0.33:
                    can_act = False
                    self_damage = 40 * active_team[active_index].base.attack
                    durability = (active_team[active_index].base.defense * active_team[active_index].base.hp) / 0.411
                    final_damage = min(
                        active_team[active_index].current_hp,
                        round((self_damage / durability) * active_team[active_index].base.hp)
                    )
                    store.update_pokemon(side, active_index, lambda p: change_hp(p, -final_damage))
                    store.add_log(f"😵‍💫 {active_team[active_index].base.name}은/는 스스로를 공격했다!")
                    print(f"{active_team[active_index].base.name}은/는 스스로를 공격했다!")
                else:
                    can_act = True
                    
        elif s == "화상":
            if not can_act:
                break
            if move.category == "물리":
                current_rate *= 0.5
                
        elif s == "소리기술사용불가":
            if not can_act:
                break
            if move.affiliation == "소리":
                store.add_log(f"{active_team[active_index].base.name}은/는 소리기술 사용에 실패했다!")
                print(f"{active_team[active_index].base.name}은/는 소리기술 사용에 실패했다!")
                can_act = False
    return {
        "rate": current_rate,
        "is_hit": can_act
    } 