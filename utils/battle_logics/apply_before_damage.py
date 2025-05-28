from p_models.move_info import MoveInfo
from context.battle_store import BattleStoreState, SideType, store
from utils.battle_logics.update_battle_pokemon import change_hp, change_rank

def apply_defensive_ability_effect_before_damage(used_move: MoveInfo, side: SideType, was_effective=None, pre_damage=False):
    state: BattleStoreState = store.get_state()
    enemy_team = state["enemy_team"]
    active_enemy = state["active_enemy"]
    my_team = state["my_team"]
    active_my = state["active_my"]

    defender = enemy_team[active_enemy] if side == "my" else my_team[active_my]

    ability = defender.base.ability
    opponent_side = "enemy" if side == "my" else "my"
    active_opponent = active_enemy if side == "my" else active_my

    rate = 1.0
    if ability and ability.defensive:
        for category in ability.defensive:
            name = ability.name
            if category == "type_nullification":
                if name in ["저수", "마중물", "건조피부"] and used_move.type == "물":
                    rate = 0
                    if name in ["저수", "건조피부"]:
                        if not pre_damage:
                            store.update_pokemon(opponent_side, active_opponent, lambda p: change_hp(p, round(p.base.hp / 4)))
                    elif name == "마중물":
                        if not pre_damage:
                            store.update_pokemon(opponent_side, active_opponent, lambda p: change_rank(p, "sp_attack", 1))
                elif name == "흙먹기" and used_move.type == "땅":
                    rate = 0
                    if not pre_damage:
                        store.update_pokemon(opponent_side, active_opponent, lambda p: change_hp(p, round(p.base.hp / 4)))
                elif name == "건조피부" and used_move.type == "불":
                    rate *= 1.25
                elif name == "타오르는불꽃" and used_move.type == "불":
                    rate = 0
                    stat = "attack" if defender.base.attack > defender.base.sp_attack else "sp_attack"
                    if not pre_damage:
                        store.update_pokemon(opponent_side, active_opponent, lambda p: change_rank(p, stat, 1))
                elif name == "피뢰침" and used_move.type == "전기":
                    rate = 0
                    if not pre_damage:
                        store.update_pokemon(opponent_side, active_opponent, lambda p: change_rank(p, "sp_attack", 1))
                        store.add_log(f"⚡ {defender.base.name}의 피뢰침 특성 발동!")
                elif name == "부유" and used_move.type == "땅":
                    rate = 0
                elif name == "초식" and used_move.type == "풀":
                    rate = 0
                    if not pre_damage:
                        store.update_pokemon(opponent_side, active_opponent, lambda p: change_rank(p, "attack", 1))
            elif category == "damage_nullification":
                if name == "방진" and used_move.affiliation == "가루":
                    rate = 0
                elif name == "방탄" and used_move.affiliation == "폭탄":
                    rate = 0
                elif name == "여왕의위엄" and used_move.priority > 0:
                    rate = 0
                elif name == "방음" and used_move.affiliation == "소리":
                    rate = 0
            elif category == "damage_reduction":
                if name == "이상한비늘" and defender.status and used_move.category == "물리":
                    rate = 2 / 3
                elif name == "두꺼운지방" and used_move.type in ["불", "얼음"]:
                    rate = 0.5
                elif name == "내열" and used_move.type == "불":
                    rate = 0.5
                elif name in ["하드록", "필터"] and (was_effective or 0) > 0:
                    rate = 0.75
                elif name == "펑크록" and used_move.affiliation == "소리":
                    rate = 0.5

    if rate < 1:
        print("방어적 특성이 적용되었다!")
    return rate


def apply_offensive_ability_effect_before_damage(used_move: MoveInfo, side: SideType, was_effective=None) -> float:
    state: BattleStoreState = store.get_state()
    my_team = state["my_team"]
    enemy_team = state["enemy_team"]
    active_my = state["active_my"]
    active_enemy = state["active_enemy"]
    public_env = state["public_env"]

    attacker = my_team[active_my] if side == "my" else enemy_team[active_enemy]
    ability = attacker.base.ability

    rate = 1.0
    if ability and ability.offensive:
        for category in ability.offensive:
            name = ability.name
            if category == "damage_buff":
                if name == "우격다짐" and used_move.effects:
                    rate *= 1.3
                if name == "이판사판" and any(d.recoil or d.fail for d in used_move.demerit_effects or []):
                    rate *= 1.2
                if name == "철주먹" and used_move.affiliation == "펀치":
                    rate *= 1.2
                if name == "단단한발톱" and used_move.is_touch:
                    rate *= 1.3
                if name == "맹화" and used_move.type == "불" and attacker.current_hp <= attacker.base.hp / 3:
                    rate *= 1.5
                if name == "급류" and used_move.type == "물" and attacker.current_hp <= attacker.base.hp / 3:
                    rate *= 1.5
                if name == "심록" and used_move.type == "풀" and attacker.current_hp <= attacker.base.hp / 3:
                    rate *= 1.5
                if name == "벌레의알림" and used_move.type == "벌레" and attacker.current_hp <= attacker.base.hp / 3:
                    rate *= 1.5
                if name == "의욕" and used_move.category == "물리":
                    rate *= 1.5
                if name == "적응력" and used_move.type in attacker.base.types:
                    rate *= 4 / 3
                if name == "메가런처" and used_move.affiliation == "파동":
                    rate *= 1.5
                if name == "수포" and used_move.type == "물":
                    rate *= 2
                if name == "색안경" and (was_effective or 0) < 0:
                    rate *= 2
                if name == "예리함" and used_move.affiliation == "베기":
                    rate *= 1.5
                if name == "옹골찬턱" and used_move.affiliation == "물기":
                    rate *= 1.5
                if name == "강철술사" and used_move.type == "강철":
                    rate *= 1.5
                if name == "펑크록" and used_move.affiliation == "소리":
                    rate *= 1.3
            elif category == "rank_buff":
                if name == "선파워" and public_env.weather == "쾌청" and used_move.category == "특수":
                    rate *= 1.5

    if rate > 1:
        print("공격적 특성이 적용되었다!")
    return rate