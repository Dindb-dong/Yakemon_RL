from typing import Dict, List, Union, Optional, Literal
from p_models.ability_info import AbilityInfo
from p_models.move_info import MoveInfo
from p_models.battle_pokemon import BattlePokemon
from context.battle_store import BattleStoreState, store
from utils.battle_logics.apply_after_damage import (
    apply_after_damage,
    apply_defensive_ability_effect_after_multi_damage,
    apply_move_effect_after_multi_damage
)
from utils.battle_logics.apply_end_turn import apply_end_turn_effects
from utils.battle_logics.calculate_order import calculate_order
from utils.battle_logics.damage_calculator import calculate_move_damage
from utils.battle_logics.get_best_switch_index import get_best_switch_index
from utils.battle_logics.switch_pokemon import switch_pokemon
from utils.battle_logics.helpers import has_ability
from utils.battle_logics.update_battle_pokemon import (
    set_ability,
    set_types,
    use_move_pp
)
from utils.battle_logics.pre_damage_calculator import pre_calculate_move_damage
import random

BattleAction = Union[MoveInfo, dict[Literal["type", "index"], Union[str, int]], None]

async def battle_sequence(
    my_action: BattleAction,
    enemy_action: BattleAction,
    watch_mode: Optional[bool] = None
) -> dict[str, Union[bool, int]]:
    state: BattleStoreState = store.get_state()
    active_enemy = state["active_enemy"]
    active_my = state["active_my"]
    my_team = state["my_team"]
    enemy_team = state["enemy_team"]
    
    # 현재 활성화된 포켓몬
    current_pokemon = my_team[active_my]
    target_pokemon = enemy_team[active_enemy]
    move_list: List[MoveInfo] = [move for move in current_pokemon.base.moves]
    pre_damage_list: List[tuple] = [
        (
            pre_calculate_move_damage(move.name, "my", active_my, attacker=current_pokemon, defender=target_pokemon),
            1 if move.demerit_effects else 0,
            1 if move.effects else 0
        )
        for move in move_list
    ]
    # pre_damage_list를 battle_store에 저장
    store.set_pre_damage_list(pre_damage_list)
    print(f"pre_damage_list (before actions): {pre_damage_list}")
    
    def is_move_action(action: BattleAction) -> bool:
        return isinstance(action, MoveInfo)

    def is_switch_action(action: BattleAction) -> bool:
        return isinstance(action, dict) and action.get("type") == "switch"

    result = {}

    # === 0. 한 쪽만 null ===
    if my_action is None and enemy_action is not None:
        store.add_log("🙅‍♂️ 내 포켓몬은 행동할 수 없었다...")
        print("🙅‍♂️ 내 포켓몬은 행동할 수 없었다...")
        store.update_pokemon("my", active_enemy, lambda p: p.copy_with(cannot_move=False))
        if is_move_action(enemy_action):
            result: dict[str, Union[bool, int]] = await handle_move("enemy", enemy_action, active_enemy, watch_mode)
        elif is_switch_action(enemy_action):
            await switch_pokemon("enemy", enemy_action["index"])
        await apply_end_turn_effects()
        return result if result else {"was_null": False, "was_effective": 0}

    if enemy_action is None and my_action is not None:
        store.add_log("🙅‍♀️ 상대 포켓몬은 행동할 수 없었다...")
        print("🙅‍♀️ 상대 포켓몬은 행동할 수 없었다...")
        store.update_pokemon("enemy", active_my, lambda p: p.copy_with(cannot_move=False))
        if is_move_action(my_action):
            await handle_move("my", my_action, active_my, watch_mode)
        elif is_switch_action(my_action):
            await switch_pokemon("my", my_action["index"])
        await apply_end_turn_effects()
        return {"was_null": False, "was_effective": 0}

    if enemy_action is None and my_action is None:
        store.add_log("😴 양측 모두 행동할 수 없었다...")
        print("😴 양측 모두 행동할 수 없었다...")
        store.update_pokemon("my", active_enemy, lambda p: p.copy_with(cannot_move=False))
        store.update_pokemon("enemy", active_my, lambda p: p.copy_with(cannot_move=False))
        await apply_end_turn_effects()
        return {"was_null": False, "was_effective": 0}

    store.add_log("우선도 및 스피드 계산중...")
    print("우선도 및 스피드 계산중...")

    who_is_first = await calculate_order(
        my_action if is_move_action(my_action) else None,
        enemy_action if is_move_action(enemy_action) else None
    )

    # === 1. 둘 다 교체 ===
    if is_switch_action(my_action) and is_switch_action(enemy_action):
        if who_is_first == "my":
            await switch_pokemon("my", my_action["index"])
            await switch_pokemon("enemy", enemy_action["index"])
        else:
            await switch_pokemon("enemy", enemy_action["index"])
            await switch_pokemon("my", my_action["index"])
        await apply_end_turn_effects()
        return {"was_null": False, "was_effective": 0}

    # === 2. 한 쪽만 교체 ===
    if is_switch_action(my_action):
        await switch_pokemon("my", my_action["index"])
        if is_move_action(enemy_action):
            if enemy_action.name == "기습":
                store.add_log("enemy의 기습은 실패했다...")
                print("enemy의 기습은 실패했다...")
            else:
                print('나는 교체, 상대는 공격!')
                result: dict[str, Union[bool, int]] = await handle_move("enemy", enemy_action, store.get_active_index("enemy"), watch_mode, True)
        await apply_end_turn_effects()
        return result if result else {"was_null": False, "was_effective": 0}

    if is_switch_action(enemy_action):
        await switch_pokemon("enemy", enemy_action["index"])
        if is_move_action(my_action):
            if my_action.name == "기습":
                store.add_log("my의 기습은 실패했다...")
                print("my의 기습은 실패했다...")
            else:
                print('상대는 교체, 나는 공격!')
                await handle_move("my", my_action, store.get_active_index("my"), watch_mode, True)
        await apply_end_turn_effects()
        return {"was_null": False, "was_effective": 0}

    # === 3. 둘 다 기술 ===
    if is_move_action(my_action) and is_move_action(enemy_action):
        if who_is_first == "my":
            if my_action.name == "기습" and enemy_action.category == "변화":
                # 내 기습 실패 -> 상대만 공격함
                store.add_log("my의 기습은 실패했다...")
                print("my의 기습은 실패했다...")
                result: dict[str, Union[bool, int]] = await handle_move("enemy", enemy_action, store.get_active_index("enemy"), watch_mode, True)
            elif enemy_action.name == "기습":
                # 상대 기습보다 내 선공기가 먼저였으면 실패 -> 나만 공격함
                store.add_log("enemy의 기습은 실패했다...")
                print("enemy의 기습은 실패했다...")
                await handle_move("my", my_action, store.get_active_index("my"), watch_mode)
            else:  # 그 외의 일반적인 경우들
                print('내 선공!')
                await handle_move("my", my_action, store.get_active_index("my"), watch_mode)
                # 상대가 쓰러졌는지 확인
                opponent_pokemon = store.get_team("enemy")
                current_defender = opponent_pokemon[store.get_active_index("enemy")]
                if current_defender and current_defender.current_hp <= 0:
                    await apply_end_turn_effects()
                    return result if result else {"was_null": False, "was_effective": 0}
                result: dict[str, Union[bool, int]] = await handle_move("enemy", enemy_action, active_enemy, watch_mode, True)
        else:  # 상대가 선공일 경우
            if enemy_action.name == "기습" and my_action.category == "변화":
                # 상대 기습 실패, 내 기술만 작동
                store.add_log("enemy의 기습은 실패했다...")
                print("enemy의 기습은 실패했다...")
                await handle_move("my", my_action, store.get_active_index("my"), watch_mode, True)
            elif my_action.name == "기습":  # 내 기습이 상대보다 느림 -> 상대 기습만 작동
                store.add_log("my의 기습은 실패했다...")
                print("my의 기습은 실패했다...")
                result: dict[str, Union[bool, int]] = await handle_move("enemy", enemy_action, store.get_active_index("enemy"), watch_mode)
            else: # 일반적인 경우 
                print('상대의 선공!')
                result: dict[str, Union[bool, int]] = await handle_move("enemy", enemy_action, store.get_active_index("enemy"), watch_mode)

                # 내가 쓰러졌는지 확인
                opponent_pokemon = store.get_team("my")
                current_defender = opponent_pokemon[store.get_active_index("my")]
                if current_defender and current_defender.current_hp <= 0:
                    await apply_end_turn_effects()
                    return result
                await handle_move("my", my_action, active_my, watch_mode, True)

    await apply_end_turn_effects()
    return result if result else {"was_null": False, "was_effective": 0}

async def handle_move(
    side: Literal["my", "enemy"],
    move: MoveInfo,
    current_index: int,
    watch_mode: Optional[bool] = None,
    was_late: Optional[bool] = None
) -> dict[str, Union[bool, int]]:
    state: BattleStoreState = store.get_state()
    my_team: List[BattlePokemon] = state["my_team"]
    enemy_team: List[BattlePokemon] = state["enemy_team"]
    active_my = state["active_my"]
    active_enemy = state["active_enemy"]

    is_multi_hit = any(effect.multi_hit for effect in (move.effects or []))
    is_double_hit = any(effect.double_hit for effect in (move.effects or []))
    is_triple_hit = move.name in ["트리플킥", "트리플악셀"]

    attacker = my_team[active_my] if side == "my" else enemy_team[active_enemy]
    defender = enemy_team[active_enemy] if side == "my" else my_team[active_my]
    active_index = active_my if side == "my" else active_enemy

    if attacker and attacker.current_hp > 0:
        print(f"{side}의 {attacker.base.name}이 {move.name}을 사용하려 한다!")
    # 현재 활성화된 포켓몬이 아닌 경우 실행하지 않음
    if current_index != active_index:
        store.add_log(f"⚠️ {attacker.base.name}는 현재 활성화된 포켓몬이 아닙니다!")
        print(f"⚠️ {attacker.base.name}는 현재 활성화된 포켓몬이 아닙니다!")
        return {"was_null": False, "was_effective": 0}

    opponent_side = "enemy" if side == "my" else "my"

    if is_triple_hit:  # 트리플악셀, 트리플킥
        hit_count = get_hit_count(move)

        # 리베로, 변환자재
        if attacker and attacker.base.ability and has_ability(attacker.base.ability, ["리베로", "변환자재"]):
            store.update_pokemon(side, active_index, lambda p: set_types(p, [move.type]))
            store.update_pokemon(side, active_index, lambda p: set_ability(p, AbilityInfo(0, '없음')))
            store.add_log(f"🔃 {attacker.base.name}의 타입은 {move.type}타입으로 변했다!")
            print(f"{attacker.base.name}의 타입은 {move.type}타입으로 변했다!")

        for i in range(hit_count):
            # 매 턴마다 최신 defender 상태 확인
            state: BattleStoreState = store.get_state()
            opponent_pokemon: list[BattlePokemon] = state[f"{opponent_side}_team"]
            current_defender: BattlePokemon = opponent_pokemon[
                active_enemy if side == "my" else active_my
            ]

            if current_defender.current_hp <= 0:
                return {"success": True, "was_null": False, "was_effective": 0}

            current_power = move.power + (10 * i if move.name == "트리플킥" else 20 * i)
            result: dict[Literal["success", "damage", "was_null", "was_effective"], Union[bool, int]] = await calculate_move_damage(
                move_name=move.name,
                side=side,
                current_index=current_index,
                override_power=current_power,
                was_late=was_late,
                is_multi_hit=is_triple_hit
            )

            store.update_pokemon(
                side,
                active_index,
                lambda p: use_move_pp(p, move.name, defender.base.ability == "프레셔" if defender.base.ability else False)
            )

            if result and result["success"]:
                state: BattleStoreState = store.get_state()
                opponent_pokemon: list[BattlePokemon] = state[f"{opponent_side}_team"]
                current_defender1: BattlePokemon = opponent_pokemon[
                    active_enemy if side == "my" else active_my
                ]
                await apply_after_damage(side, attacker, current_defender1, move, result["damage"] if "damage" in result else 0, watch_mode, True)
                await apply_defensive_ability_effect_after_multi_damage(side, attacker, defender, move, result["damage"] if "damage" in result else 0, watch_mode)
            else:
                break

        return {"was_null": result.get("was_null", False), "was_effective": result.get("was_effective", 0)}

    elif is_double_hit or is_multi_hit:  # 첫타 맞으면 다 맞춤
        # 리베로, 변환자재
        if attacker and attacker.base.ability and has_ability(attacker.base.ability, ["리베로", "변환자재"]):
            store.update_pokemon(side, active_index, lambda p: set_types(p, [move.type]))
            store.update_pokemon(side, active_index, lambda p: set_ability(p, None))
            store.add_log(f"{attacker.base.name}의 타입은 {move.type}타입으로 변했다!")
            print(f"{attacker.base.name}의 타입은 {move.type}타입으로 변했다!")

        result: dict[Literal["success", "damage", "was_null", "was_effective"], Union[bool, int]] = await calculate_move_damage(move_name=move.name, side=side, current_index=current_index, was_late=was_late)
        print("1번째 타격!")
        if result and result["success"]:
            if not result.get("is_hit", True):  # is_hit이 False면 빗나간 것
                store.add_log(f"🚫 {attacker.base.name}의 공격은 빗나갔다!")
                print(f"{attacker.base.name}의 공격은 빗나갔다!")
                return {"was_null": result.get("was_null", False), "was_effective": result.get("was_effective", 0)}
                
            if result.get("was_null"):
                store.add_log(f"🚫 {attacker.base.name}의 공격은 효과가 없었다...")
                print(f"{attacker.base.name}의 공격은 효과가 없었다...")
                return {"was_null": result.get("was_null", False), "was_effective": result.get("was_effective", 0)}
                
            state: BattleStoreState = store.get_state()
            opponent_pokemon: list[BattlePokemon] = state[f"{opponent_side}_team"]
            current_defender: BattlePokemon = opponent_pokemon[
                active_enemy if side == "my" else active_my
            ]   
            await apply_after_damage(side, attacker, current_defender, move, result["damage"] if "damage" in result else 0, watch_mode, True)
            hit_count = get_hit_count(move)
            print(hit_count)
            for i in range(hit_count - 1):
                # 매 턴마다 최신 defender 상태 확인
                opponent_pokemon: list[BattlePokemon] = state[f"{opponent_side}_team"]
                current_defender: BattlePokemon = opponent_pokemon[
                    active_enemy if side == "my" else active_my
                ]
                if current_defender.current_hp <= 0:
                    break
                print(f"{i + 2}번째 타격!")
                result: dict[Literal["success", "damage", "was_null", "was_effective"], Union[bool, int]] = await calculate_move_damage(
                    move_name=move.name,
                    side=side,
                    current_index=current_index,
                    is_always_hit=True,
                    was_late=was_late,
                    is_multi_hit=True
                )

                if result and result["success"]:
                    if result.get("was_null"):
                        break  # 효과가 없는 경우 후속 타격 중단
                        
                    current_defender = store.get_state()[f"{opponent_side}_team"][
                        active_enemy if side == "my" else active_my
                    ]
                    await apply_after_damage(side, attacker, current_defender, move, result["damage"] if "damage" in result else 0, watch_mode, True)
                    await apply_defensive_ability_effect_after_multi_damage(side, attacker, defender, move, result["damage"] if "damage" in result else 0, watch_mode)
                else:
                    break

            current_defender1 = store.get_state()[f"{opponent_side}_team"][
                active_enemy if side == "my" else active_my
            ]
            await apply_move_effect_after_multi_damage(side, attacker, current_defender1, move, result["damage"] if "damage" in result else 0) #, watch_mode
            store.add_log(f"📊 총 {hit_count}번 맞았다!")
            print(f"총 {hit_count}번 맞았다!")

        return {"was_null": result.get("was_null", False), "was_effective": result.get("was_effective", 0)}

    else:  # 그냥 다른 기술들
        # 리베로, 변환자재
        if attacker and attacker.base.ability and has_ability(attacker.base.ability, ["리베로", "변환자재"]):
            store.update_pokemon(side, active_index, lambda p: set_types(p, [move.type]))
            store.update_pokemon(side, active_index, lambda p: set_ability(p, None))
            store.add_log(f"🔃 {attacker.base.name}의 타입은 {move.type}타입으로 변했다!")
            print(f"{attacker.base.name}의 타입은 {move.type}타입으로 변했다!")

        result: dict[Literal["success", "damage", "was_null", "was_effective"], Union[bool, int]] = await calculate_move_damage(move_name=move.name, side=side, current_index=current_index, was_late=was_late)
        if result and result["success"]:
            if not result.get("is_hit", True):  # is_hit이 False면 빗나간 것
                store.add_log(f"🚫 {attacker.base.name}의 공격은 빗나갔다!")
                print(f"{attacker.base.name}의 공격은 빗나갔다!")
                return {"was_null": result.get("was_null", False), "was_effective": result.get("was_effective", 0)}
            if result.get("was_null"):
                store.add_log(f"🚫 {attacker.base.name}의 공격은 효과가 없었다...")
                print(f"{attacker.base.name}의 공격은 효과가 없었다...")
                return {"was_null": result.get("was_null", False), "was_effective": result.get("was_effective", 0)}

            if defender and defender.base.ability and defender.base.ability.name == "매직가드" and move.category == "변화":
                store.add_log(f"{defender.base.name}은 매직가드로 피해를 입지 않았다!")
                print(f"{defender.base.name}은 매직가드로 피해를 입지 않았다!")
                await apply_after_damage(side, attacker, defender, move, result["damage"] if "damage" in result else 0, watch_mode)
                return {"was_null": result.get("was_null", False), "was_effective": result.get("was_effective", 0)}

            current_defender = store.get_state()[f"{opponent_side}_team"][
                active_enemy if side == "my" else active_my
            ]   
            await apply_after_damage(side, attacker, current_defender, move, result["damage"] if "damage" in result else 0, watch_mode)

        return {"was_null": result.get("was_null", False), "was_effective": result.get("was_effective", 0)}

async def remove_fainted_pokemon(side: Literal["my", "enemy"]) -> None:
    next_index = get_best_switch_index(side)
    if next_index != -1:
        print(f"{side}의 포켓몬이 쓰러졌다! 교체 중...")
        await switch_pokemon(side, next_index)

def get_hit_count(move: MoveInfo) -> int:
    hit_count = 0
    for effect in (move.effects or []):
        if effect.double_hit:
            print("2회 공격 시도")
            hit_count = 2
        if effect.triple_hit:
            print("3회 공격 시도")
            hit_count = 3
        if effect.multi_hit:
            print("다회 공격 시도")

    if hit_count > 0:
        return hit_count

    if move.name == "스킬링크":
        return 5

    rand = random.random()
    if rand < 0.15:
        return 5
    if rand < 0.30:
        return 4
    if rand < 0.65:
        return 3
    return 2
