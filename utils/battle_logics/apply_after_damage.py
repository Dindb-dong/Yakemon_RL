from p_models.battle_pokemon import BattlePokemon
from context.battle_store import store
from p_models.move_info import MoveInfo
from utils.battle_logics.update_battle_pokemon import add_status, change_hp, change_rank, set_types
from p_models.rank_state import RankState
from utils.battle_logics.switch_pokemon import switch_pokemon
from utils.battle_logics.get_best_switch_index import get_best_switch_index
from utils.battle_logics.rank_effect import calculate_rank_effect
from utils.battle_logics.apply_none_move_damage import apply_recoil_damage
from utils.battle_logics.update_environment import set_weather
import asyncio
from context.battle_store import SideType
from typing import Literal, Optional, List, Dict
import random

async def apply_defensive_ability_effect_after_multi_damage(
    side: Literal["my", "enemy"],
    attacker: BattlePokemon,
    defender: BattlePokemon,
    used_move: MoveInfo,
    applied_damage: Optional[int] = None,
    watch_mode: Optional[bool] = False,
    multi_hit: Optional[bool] = False
) -> None:
    """다중 데미지 후 방어 특성 효과 적용"""
    opponent_side = "enemy" if side == "my" else "my"
    active_opponent = store.state["active_enemy"] if side == "my" else store.state["active_my"]
    active_mine = store.state["active_my"] if side == "my" else store.state["active_enemy"]

    ability = defender.base.ability
    if not ability or not ability.defensive:
        return

    for category in ability.defensive:
        if category == "weather_change":
            if ability.name == "모래뿜기":
                set_weather("모래바람")
                store.add_log(f"🏜️ {defender.base.name}의 특성으로 날씨가 모래바람이 되었다!")
        elif category == "rank_change":
            if ability.name == "증기기관" and used_move.type in ["물", "불"]:
                if defender.current_hp > 0:
                    store.add_log(f"{defender.base.name}의 특성 {ability.name} 발동!")
                    store.update_pokemon(opponent_side, active_opponent,
                                          lambda p: change_rank(p, "speed", 6))
            elif ability.name == "깨어진갑옷" and used_move.is_touch:
                if defender.current_hp > 0:
                    store.add_log(f"{defender.base.name}의 특성 {ability.name} 발동!")
                    store.update_pokemon(opponent_side, active_opponent,
                                          lambda p: change_rank(p, "speed", 2))
                    store.update_pokemon(opponent_side, active_opponent,
                                          lambda p: change_rank(p, "defense", -1))
            elif ability.name == "정의의마음" and used_move.type == "악":
                if defender.current_hp > 0:
                    store.add_log(f"{defender.base.name}의 특성 {ability.name} 발동!")
                    store.update_pokemon(opponent_side, active_opponent,
                                          lambda p: change_rank(p, "attack", 1))
            elif ability.name == "지구력" and (applied_damage or 0) > 0 and not multi_hit:
                if defender.current_hp > 0:
                    store.add_log(f"{defender.base.name}의 특성 {ability.name} 발동!")
                    store.update_pokemon(opponent_side, active_opponent,
                                          lambda p: change_rank(p, "defense", 1))

async def apply_after_damage(side: str, attacker: BattlePokemon, defender: BattlePokemon,
                            used_move: MoveInfo, applied_damage: int = 0,
                            watch_mode: bool = False, multi_hit: bool = False):

    opponent_side = "enemy" if side == "my" else "my"

    await apply_defensive_ability_effect_after_multi_damage(
        side, attacker, defender, used_move, applied_damage, watch_mode, multi_hit
    )

    await apply_offensive_ability_effect_after_damage(
        side, attacker, defender, used_move, applied_damage, watch_mode, multi_hit
    )

    await apply_move_effect_after_damage(
        side, attacker, defender, used_move, applied_damage, watch_mode, multi_hit
    )

    await apply_panic_uturn(
        opponent_side, attacker, defender, used_move, applied_damage, watch_mode, multi_hit
    )

async def apply_panic_uturn(side: str, attacker: BattlePokemon, defender: BattlePokemon,
                            used_move: MoveInfo, applied_damage: int = 0, watch_mode: bool = False,
                            multi_hit: bool = False):
    """
    기술 사용 후 방어측 포켓몬이 '위기회피' 특성을 가질 경우 자동/수동 교체를 수행함.
    - side는 공격자 기준 상대방 진영.
    """
    team = store.get_team(side)
    active_index = store.get_active_index(side)
    defender = team[active_index]

    if (defender.base.ability and defender.base.ability.name == "위기회피"
        and defender.current_hp > 0
        and defender.current_hp <= defender.base.hp / 2):

        print(f"🛡️ {defender.base.name}의 특성 '위기회피' 발동!")

        available_indexes = [
            i for i, p in enumerate(team)
            if i != active_index and p.current_hp > 0
        ]

        if not available_indexes:
            print("⚠️ 위기회피 가능 포켓몬 없음 (교체 생략)")
            return

        switch_index = get_best_switch_index(side)
        await switch_pokemon(side, switch_index)
        
async def apply_move_effect_after_multi_damage(
    side: SideType,
    attacker: BattlePokemon,
    defender: BattlePokemon,
    used_move: MoveInfo,
    applied_damage: Optional[int] = None,
):

    opponent_side = "enemy" if side == "my" else "my"
    my_team = store.get_team(side)
    enemy_team = store.get_team(opponent_side)
    active_my = store.get_active_index(side)
    active_enemy = store.get_active_index(opponent_side)
    add_log = store.add_log

    active_mine = active_my if side == "my" else active_enemy
    active_opponent = active_enemy if side == "my" else active_my
    mine_team = my_team if side == "my" else enemy_team
    mirrored_team = enemy_team if side == "my" else my_team
    baton_touch = used_move.name == "배턴터치"
    nullification = attacker.base.ability and attacker.base.ability.name == "부식"
    effect = getattr(used_move, "effects", None)
    demerit_effects = getattr(used_move, "demerit_effects", None)

    if used_move.cannot_move:
        store.update_pokemon(side, active_mine, lambda p: p.deepcopy(cannot_move=True))
        store.add_log(f"💥 {attacker.base.name}은 피로로 인해 다음 턴 움직일 수 없다!")
        print(f"피로 효과 적용: {attacker.base.name}은 피로로 인해 다음 턴 움직일 수 없다!")

    # 유턴 처리
    if used_move.u_turn and "교체불가" not in attacker.status:
        available_indexes = [
            i for i, p in enumerate(mine_team) if i != active_mine and p.current_hp > 0
        ]
        if available_indexes:
            best_index = get_best_switch_index(side)
            await switch_pokemon(side, best_index, baton_touch)
            store.add_log(f"💨 {attacker.base.name}이(가) 교체되었습니다!")
            print(f"유턴 효과 적용: {attacker.base.name}이(가) 교체되었습니다!")

    # 자폭류 처리
    if used_move.self_kill:
        store.update_pokemon(side, active_mine, lambda p: change_hp(p, -p.base.hp))
        store.add_log(f"🤕 {attacker.base.name}은/는 반동으로 기절했다...!")
        print(f"자폭 효과 적용: {attacker.base.name}은/는 반동으로 기절했다...!")

    # 디메리트 효과
    if demerit_effects:
        for demerit in demerit_effects:
            if demerit and random.random() < demerit.chance:
                if demerit.recoil and applied_damage:
                    result = await apply_recoil_damage(attacker, demerit.recoil, applied_damage)
                    store.update_pokemon(side, active_mine, lambda _: result)
                    recoil_damage = int(applied_damage * demerit.recoil)
                    store.add_log(f"🤕 {attacker.base.name}이(가) 반동 데미지 {recoil_damage}를 입었다!")
                    print(f"반동 데미지 적용: {attacker.base.name}이(가) 반동 데미지 {recoil_damage}를 입었다!")
                for sc in demerit.stat_change:
                    store.update_pokemon(
                        side, active_mine,
                        lambda p: change_rank(p, sc.stat, sc.change)
                    )
                    store.add_log(f"🔃 {attacker.base.name}의 {sc.stat}이(가) {sc.change}랭크 변했다!")
                    print(f"디메리트 효과 적용: {attacker.base.name}의 {sc.stat}이(가) {sc.change}랭크 변했다!")

    # 부가효과
    if used_move.target == "opponent" and (attacker.base.ability is None or attacker.base.ability.name != "우격다짐"):
        roll = random.random() * 2 if (attacker.base.ability and attacker.base.ability.name == "하늘의은총") else random.random()
        for eff in effect or []:
            if roll < (eff.chance if eff.chance is not None else 0):
                if eff.heal and not applied_damage:
                    heal = attacker.base.hp * eff.heal if eff.heal < 1 else calculate_rank_effect(defender.rank['attack']) * defender.base.attack
                    store.update_pokemon(side, active_mine, lambda p: change_hp(p, heal))
                    store.add_log(f"➕ {attacker.base.name}은 체력을 회복했다!")
                    print(f"체력 회복 효과 적용: {attacker.base.name}이(가) 체력을 회복했다!")
                for sc in eff.stat_change:
                    target_side = (
                        side if sc.target == "self"
                        else opponent_side
                    )
                    index = active_mine if target_side == side else active_opponent
                    store.update_pokemon(target_side, index, lambda p: change_rank(p, sc.stat, sc.change))
                    store.add_log(f"🔃 {attacker.base.name}의 {sc.stat}이(가) {sc.change}랭크 변했다!")
                    print(f"부가효과 적용: {attacker.base.name}의 {sc.stat}이(가) {sc.change}랭크 변했다!")
                if eff.status:
                    store.update_pokemon(opponent_side, active_opponent, lambda p: add_status(p, eff.status, opponent_side, nullification))
                    store.add_log(f"{defender.base.name}은 {eff.status} 상태가 되었다!")
                    print(f"상태이상 효과 적용: {defender.base.name}이(가) {eff.status} 상태가 되었다!")

    # 강제 교체
    if used_move.exile:
        alive_opponents = [
            i for i, p in enumerate(mirrored_team) if i != active_opponent and p.current_hp > 0
        ]
        if alive_opponents:
            new_index = random.choice(alive_opponents)
            await switch_pokemon(opponent_side, new_index, baton_touch)
            store.add_log(f"💨 {defender.base.name}은(는) 강제 교체되었다!")
            print(f"강제 교체 효과 적용: {defender.base.name}이(가) 강제 교체되었다!")

async def apply_offensive_ability_effect_after_damage(
    side: Literal["my", "enemy"],
    attacker,
    defender,
    used_move,
    applied_damage: Optional[int] = None,
    watch_mode: Optional[bool] = False,
    multi_hit: Optional[bool] = False
):
    opponent_side = "enemy" if side == "my" else "my"
    active_opponent = store.state["active_enemy"] if side == "my" else store.state["active_my"]
    ability = attacker.base.ability

    if not ability or not ability.offensive:
        return

    for category in ability.offensive:
        if category == "status_change":
            if ability.name == "독수" and used_move.is_touch:
                if random.random() < 0.3:
                    store.update_pokemon(opponent_side, active_opponent, lambda p: add_status(p, "독", opponent_side))
                    store.add_log(f"🦂 {defender.base.name}은(는) 독수 특성으로 독 상태가 되었다!")
                    print(f"특성 효과 적용: {defender.base.name}이(가) 독수 특성으로 독 상태가 되었다!")

async def apply_move_effect_after_damage(
    side: Literal["my", "enemy"],
    attacker: BattlePokemon,
    defender: BattlePokemon,
    used_move: MoveInfo,
    applied_damage: Optional[int] = None,
    watch_mode: bool = False,
    multi_hit: bool = False,
):
    opponent_side = "enemy" if side == "my" else "my"
    state = store.get_state()
    active_opp = state["active_enemy"] if side == "my" else state["active_my"]
    active_mine = state["active_my"] if side == "my" else state["active_enemy"]
    my_team = state["my_team"]
    enemy_team = state["enemy_team"]
    mine_team = my_team if side == "my" else enemy_team
    opp_team = enemy_team if side == "my" else my_team
    enemy_pokemon = my_team[state["active_my"]] if side == "enemy" else enemy_team[state["active_enemy"]]
    baton_touch = used_move.name == "배턴터치"
    nullification = attacker.base.ability and attacker.base.ability.name == "부식"

    if used_move.cannot_move:
        store.update_pokemon(side, active_mine, lambda p: p.deepcopy(cannot_move=True))
        store.add_log(f"💥 {attacker.base.name}은 피로로 인해 다음 턴 움직일 수 없다!")
        print(f"피로 효과 적용: {attacker.base.name}은 피로로 인해 다음 턴 움직일 수 없다!")

    # 유턴: UI 없이 자동 교체
    if used_move.u_turn and "교체불가" not in attacker.status:
        alive_opp = [i for i, p in enumerate(opp_team) if p.current_hp > 0 and i != active_opp]
        if side == "my" and not alive_opp and enemy_pokemon.current_hp == 0:
            return
        if side == "enemy" and not alive_opp and enemy_pokemon.current_hp == 0:
            return

        available = [i for i, p in enumerate(mine_team) if p.current_hp > 0 and i != active_mine]
        if available:
            switch_index = get_best_switch_index(side)
            await switch_pokemon(side, switch_index, baton_touch)
            print(f"유턴 효과 적용: {attacker.base.name}이(가) 교체되었습니다!")

    # 자폭류 처리
    if used_move.self_kill:
        store.update_pokemon(side, active_mine, lambda p: change_hp(p, -p.base.hp))
        store.add_log(f"🤕 {attacker.base.name}은/는 반동으로 기절했다...!")
        print(f"자폭 효과 적용: {attacker.base.name}은/는 반동으로 기절했다...!")

    # 디메리트 효과
    if used_move.demerit_effects:
        for demerit in used_move.demerit_effects:
            if demerit and random.random() < demerit.chance:
                if demerit.recoil and applied_damage:
                    result = await apply_recoil_damage(attacker, demerit.recoil, applied_damage)
                    store.update_pokemon(side, active_mine, lambda _: result)
                    recoil_damage = int(applied_damage * demerit.recoil)
                    store.add_log(f"🤕 {attacker.base.name}이(가) 반동 데미지 {recoil_damage}를 입었다!")
                    print(f"반동 데미지 적용: {attacker.base.name}이(가) 반동 데미지 {recoil_damage}를 입었다!")
                if demerit.stat_change:
                    for sc in demerit.stat_change:
                        store.update_pokemon(
                            side, active_mine,
                            lambda p: change_rank(p, sc.stat, sc.change)
                        )
                        store.add_log(f"🔃 {attacker.base.name}의 {sc.stat}이(가) {sc.change}랭크 변했다!")
                        print(f"디메리트 효과 적용: {attacker.base.name}의 {sc.stat}이(가) {sc.change}랭크 변했다!")

    # 부가효과
    if attacker.base.ability and attacker.base.ability.name != "우격다짐" and used_move.target == "opponent" and not multi_hit:
        roll = random.random() * (2 if attacker.base.ability.name == "하늘의은총" else 1)
        for effect in used_move.effects or []:
            if defender.base.ability and defender.base.ability.name == "매직미러" and used_move.category == "변화":
                if effect.status:
                    store.update_pokemon(side, active_mine, lambda p: add_status(p, effect.status, side))
                    store.add_log(f"🪞 {attacker.base.name}은/는 {effect.status} 상태가 되었다!")
                    print(f"상태이상 효과 적용: {defender.base.name}이(가) {effect.status} 상태가 되었다!")
                if effect.stat_change:
                    for sc in effect.stat_change:
                        store.update_pokemon(side, active_mine, lambda p: change_rank(p, sc.stat, sc.change))
                        store.add_log(f"🪞 {attacker.base.name}의 {sc.stat}이/가 {sc.change}랭크 변했다!")
                        print(f"부가효과 적용: {attacker.base.name}의 {sc.stat}이(가) {sc.change}랭크 변했다!")
                continue
            
            if roll < (effect.chance if effect.chance else 0):
                if effect.type_change:
                    store.update_pokemon(opponent_side, active_opp, lambda p: set_types(p, [effect.type_change]))
                if effect.heal and applied_damage is None:
                    heal_amt = attacker.base.hp * effect.heal if effect.heal < 1 else calculate_rank_effect(defender.rank['attack']) * defender.base.attack
                    store.update_pokemon(side, active_mine, lambda p: change_hp(p, heal_amt))
                    store.add_log(f"➕ {attacker.base.name}은/는 체력을 회복했다!")
                    print(f"체력 회복 효과 적용: {attacker.base.name}이(가) 체력을 회복했다!")
                if effect.stat_change:
                    for sc in effect.stat_change:
                        target_side = opponent_side if sc.target == "opponent" else side
                        active_idx = state["active_enemy"] if target_side == "enemy" else state["active_my"]
                        target_team = enemy_team if target_side == "enemy" else my_team
                        is_mirror = target_team[active_idx].base.ability and target_team[active_idx].base.ability.name == "미러아머"
                        if is_mirror and sc.target == "opponent":
                            target_side = side
                            active_idx = state["active_my"] if side == "my" else state["active_enemy"]
                            target_team = my_team if side == "my" else enemy_team
                            store.add_log("미러아머 발동!")

                        store.update_pokemon(target_side, active_idx, lambda p: change_rank(p, sc.stat, sc.change))
                        store.add_log(f"🔃 {target_team[active_idx].base.name}의 {sc.stat}이/가 {sc.change}랭크 변했다!")
                        print(f"부가효과 적용: {attacker.base.name}의 {sc.stat}이(가) {sc.change}랭크 변했다!")
                if effect.status:
                    skip = False
                    status = effect.status
                    if used_move.name == "매혹의보이스":
                        if not defender.had_rank_up:
                            skip = True
                    else:
                        t = defender.base.types
                        a = defender.base.ability.name if defender.base.ability else ""
                        if status == "화상" and "불" in t: skip = True
                        if status == "마비" and "전기" in t: skip = True
                        if status == "얼음" and "얼음" in t: skip = True
                        if status in ["독", "맹독"] and ("독" in t or "강철" in t or a == "면역"): skip = True
                        if status == "풀죽음" and a == "정신력": skip = True
                        if status == "잠듦" and a in ["불면", "의기양양", "스위트베일"]: skip = True
                        if status in ["도발", "헤롱헤롱"] and a == "둔감": skip = True
                        if status == "혼란" and a == "마이페이스": skip = True

                    if not skip:
                        store.update_pokemon(opponent_side, active_opp, lambda p: add_status(p, status, opponent_side, nullification))
                        print(f"상태이상 효과 적용: {defender.base.name}이(가) {status} 상태가 되었다!")

                if effect.heal and applied_damage and applied_damage > 0:
                    store.update_pokemon(side, active_mine, lambda p: change_hp(p, applied_damage * effect.heal))
                    store.add_log(f"➕ {attacker.base.name}은/는 체력을 회복했다!")
                    print(f"체력 회복 효과 적용: {attacker.base.name}이(가) 체력을 회복했다!")

    # 강제 교체
    if used_move.exile and defender.current_hp > 0:
        available = [i for i, p in enumerate(opp_team) if p.current_hp > 0 and i != active_opp]
        if available:
            idx = random.choice(available)
            await switch_pokemon(opponent_side, idx, baton_touch)
            store.add_log(f"💨 {opp_team[active_opp].base.name}은/는 강제 교체되었다!")
            print(f"강제 교체 효과 적용: {opp_team[active_opp].base.name}이(가) 강제 교체되었다!")