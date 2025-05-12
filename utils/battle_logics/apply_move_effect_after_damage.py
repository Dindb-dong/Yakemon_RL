from p_models.battle_pokemon import BattlePokemon
from context.battle_store import store
from context.battle_store import SideType
from utils.battle_logics.rank_effect import calculate_rank_effect
from utils.battle_logics.update_battle_pokemon import change_hp, change_rank, add_status
from utils.battle_logics.switch_pokemon import switch_pokemon
from utils.battle_logics.get_best_switch_index import get_best_switch_index
from utils.battle_logics.apply_none_move_damage import apply_recoil_damage
from typing import Optional, Literal
import random
from utils.battle_logics.apply_after_damage import apply_defensive_ability_effect_after_multi_damage

async def apply_move_effect_after_multi_damage(
    side: SideType,
    attacker: BattlePokemon,
    defender: BattlePokemon,
    used_move,
    applied_damage: Optional[int] = None,
    watch_mode: Optional[bool] = False,
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
    demerit_effects = getattr(used_move, "demeritEffects", None)

    if used_move.cannot_move:
        store.update_pokemon(side, active_mine, lambda p: p.deepcopy(cannot_move=True))
        add_log(f"💥 {attacker.base.name}은 피로로 인해 다음 턴 움직일 수 없다!")

    # 유턴 처리
    if used_move.u_turn and "교체불가" not in attacker.status:
        available_indexes = [
            i for i, p in enumerate(mine_team) if i != active_mine and p.current_hp > 0
        ]
        if available_indexes:
            best_index = get_best_switch_index(side)
            await switch_pokemon(side, best_index, baton_touch)

    # 자폭류 처리
    if used_move.self_kill:
        store.update_pokemon(side, active_mine, lambda p: change_hp(p, -p.base.hp))
        add_log(f"🤕 {attacker.base.name}은/는 반동으로 기절했다...!")

    # 디메리트 효과
    if demerit_effects:
        for demerit in demerit_effects:
            if demerit and random.random() < demerit.get("chance", 0):
                if demerit.get("recoil") and applied_damage:
                    updated_pokemon = await apply_recoil_damage(attacker, demerit["recoil"], applied_damage)
                    store.update_pokemon(side, active_mine, lambda _: updated_pokemon)
                for sc in demerit.get("statChange", []):
                    store.update_pokemon(
                        side, active_mine,
                        lambda p: change_rank(p, sc["stat"], sc["change"])
                    )
                    add_log(f"🔃 {attacker.base.name}의 {sc['stat']}이(가) {sc['change']}랭크 변했다!")

    # 부가효과
    if used_move.target == "opponent" and (attacker.base.ability is None or attacker.base.ability.name != "우격다짐"):
        roll = random.random() * 2 if (attacker.base.ability and attacker.base.ability.name == "하늘의은총") else random.random()
        for eff in effect or []:
            if roll < eff.get("chance", 0):
                if eff.get("heal") and not applied_damage:
                    heal = attacker.base.hp * eff["heal"] if eff["heal"] < 1 else calculate_rank_effect(defender.rank['attack']) * defender.base.attack
                    store.update_pokemon(side, active_mine, lambda p: change_hp(p, heal))
                    add_log(f"➕ {attacker.base.name}은 체력을 회복했다!")
                    print("apply_move_effect_after_damage.py") # 맞은 포켓몬의 체력이 회복되는 오류 확인 위한 디버깅
                for sc in eff.get("statChange", []):
                    target_side = (
                        side if sc["target"] == "self"
                        else opponent_side
                    )
                    index = active_mine if target_side == side else active_opponent
                    store.update_pokemon(target_side, index, lambda p: change_rank(p, sc["stat"], sc["change"]))
                    add_log(f"🔃 {attacker.base.name}의 {sc['stat']}이(가) {sc['change']}랭크 변했다!")
                if "status" in eff:
                    store.update_pokemon(opponent_side, active_opponent, lambda p: add_status(p, eff["status"], opponent_side, nullification))
                    add_log(f"{defender.base.name}은 {eff['status']} 상태가 되었다!")

    # 강제 교체
    if used_move.exile:
        alive_opponents = [
            i for i, p in enumerate(mirrored_team) if i != active_opponent and p.current_hp > 0
        ]
        if alive_opponents:
            new_index = random.choice(alive_opponents)
            await switch_pokemon(opponent_side, new_index, baton_touch)
            add_log(f"💨 {defender.base.name}은(는) 강제 교체되었다!")