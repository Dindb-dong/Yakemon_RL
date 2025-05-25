from typing import List, Dict, Optional, Union, Literal, Tuple
from p_models.move_info import MoveInfo
from p_models.pokemon_info import PokemonInfo
from p_models.battle_pokemon import BattlePokemon
from p_models.types import WeatherType
from p_models.ability_info import AbilityInfo
from context.battle_store import store
from context.duration_store import duration_store
from utils.battle_logics.rank_effect import calculate_accuracy, calculate_critical, calculate_rank_effect
from utils.battle_logics.status_effect import apply_status_effect_before
from utils.battle_logics.calculate_type_effectiveness import calculate_type_effectiveness_with_ability, is_type_immune
from utils.battle_logics.helpers import has_ability
from utils.battle_logics.apply_before_damage import apply_defensive_ability_effect_before_damage, apply_offensive_ability_effect_before_damage
from utils.battle_logics.update_battle_pokemon import (
    add_status, change_hp, change_position, change_rank, remove_status,
    set_charging, set_had_missed, set_locked_move, set_protecting,
    set_received_damage, set_used_move, use_move_pp
)
from utils.battle_logics.update_environment import add_trap, set_field, set_room, set_screen, set_weather
from utils.battle_logics.apply_none_move_damage import apply_thorn_damage
from utils.apply_skin_type_effect import apply_skin_type_effect
from context.battle_environment import PublicBattleEnvironment
import random

SideType = Literal["my", "enemy"]

async def calculate_move_damage(
    move_name: str,
    side: SideType,
    current_index: int,
    is_always_hit: bool = False,
    additional_damage: Optional[int] = None,
    override_power: Optional[int] = None,
    was_late: bool = False,
    is_multi_hit: bool = False
) -> Dict:
    print("calculate_move_damage 호출 시작")
    # Get battle state
    state = store.get_state()
    my_team: List[BattlePokemon] = state["my_team"]
    enemy_team: List[BattlePokemon] = state["enemy_team"]
    active_my: int = state["active_my"]
    active_enemy: int = state["active_enemy"]
    active_index: int = active_my if side == "my" else active_enemy
    public_env: PublicBattleEnvironment = state["public_env"]
    if (current_index != active_index): # 강제교체 당해서 공격 못함
        return {"success": False}
    # Set attacker and defender based on side
    attacker: BattlePokemon = my_team[active_my] if side == "my" else enemy_team[active_enemy]
    defender: BattlePokemon = enemy_team[active_enemy] if side == "my" else my_team[active_my]
    my_pokemon: PokemonInfo = attacker.base 
    opponent_pokemon: PokemonInfo = defender.base
    opponent_side = "enemy" if side == "my" else "my"
    active_mine = active_my if side == "my" else active_enemy
    active_opponent = active_enemy if side == "my" else active_my
    team = my_team if side == "my" else enemy_team
    # Get move info and apply skin type effect
    move_info = get_move_info(my_pokemon, move_name)
    move_info = apply_skin_type_effect(move_info, my_pokemon.ability.name if my_pokemon.ability else None)
    # Get environment effects
    weather_effect = public_env.weather
    field_effect = public_env.field
    disaster_effect = public_env.disaster
    
    # Initialize variables
    types = 1.0  # Type effectiveness multiplier
    base_power = override_power if override_power is not None else move_info.power  # Base power
    print(f"base_power in damage_calculator: {base_power}")
    # Apply Technician ability
    if attacker.base.ability and attacker.base.ability.name == "테크니션" and base_power <= 60:
        base_power *= 1.5
    # Calculate power
    additional_damage = 0
    additional_damage += base_power if attacker.base.ability and attacker.base.ability.name == "테크니션" and base_power is not None else 0
    print(f"additional_damage in damage_calculator: {additional_damage}")
    power = (move_info.get_power(team, side, base_power) + (additional_damage or 0)
                if move_info.get_power else base_power + (additional_damage or 0))
    # Calculate accuracy
    accuracy = (move_info.get_accuracy(public_env, side)
                if move_info.get_accuracy else move_info.accuracy)
    # Initialize accuracy rate
    acc_rate = 1.0
    if defender.base.ability and defender.base.ability.name == "눈숨기" and weather_effect == "싸라기눈":
        acc_rate *= 0.8
    if defender.base.ability and defender.base.ability.name == "모래숨기" and weather_effect == "모래바람":
        acc_rate *= 0.8
    if attacker.base.ability and attacker.base.ability.name == "복안":
        acc_rate *= 1.3
    if attacker.base.ability and attacker.base.ability.name == "승리의별":
        acc_rate *= 1.1
    # Initialize other variables
    cri_rate = 0
    rate = 1.0
    if was_late and attacker.base.ability and attacker.base.ability.name == "애널라이즈":
        print("애널라이즈로 강화됐다!")
        rate *= 1.3
    is_hit = True
    is_critical = False
    was_effective = 0
    was_null = False
    message = None
    my_poke_rank = attacker.rank
    op_poke_rank = defender.rank
    my_poke_status = attacker.status
    
    # Calculate attack and defense stats
    attack_stat = my_pokemon.attack if move_info.category == "물리" else my_pokemon.sp_attack
    if move_name == "바디프레스":
        attack_stat = my_pokemon.defense
        print(f"{move_name} 효과 발동!")
    if move_name == "속임수":
        attack_stat = opponent_pokemon.attack
        print(f"{move_name} 효과 발동!")
    if attacker.base.ability and attacker.base.ability.name == "무기력" and attacker.current_hp <= (attacker.base.hp / 2):
        attack_stat *= 0.5
    defense_stat = opponent_pokemon.defense if move_info.category == "물리" else opponent_pokemon.sp_defense
    if move_name == "사이코쇼크":
        defense_stat = opponent_pokemon.defense
        print(f"{move_name} 효과 발동!")
    # Handle No Guard ability
    if (attacker.base.ability and attacker.base.ability.name == "노가드") or \
        (defender.base.ability and defender.base.ability.name == "노가드"):
        is_always_hit = True
        
    # Handle locked moves (like Outrage)
    if move_info.locked_move:
        store.update_pokemon(side, active_my if side == "my" else active_enemy, 
                            lambda p: p.copy_with(locked_move_turn=2 if random.random() < 0.5 else 1))
        store.update_pokemon(side, active_my if side == "my" else active_enemy, 
                            lambda p: set_locked_move(p, move_info))
    
    # 0-0. Check if defender is protecting
    if defender.is_protecting:
        store.add_log(f"{defender.base.name}는 방어중이여서 {attacker.base.name}의 공격은 실패했다!")
        print(f"{defender.base.name}는 방어중이여서 {attacker.base.name}의 공격은 실패했다!")
        
        if defender.used_move and defender.used_move.name == "니들가드" and move_info.is_touch:
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: apply_thorn_damage(p))
            
        elif defender.used_move and defender.used_move.name == "토치카" and move_info.is_touch:
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: add_status(p, "독", opponent_side))
            if not (attacker.base.ability and attacker.base.ability.name == "면역" or 
                    "독" in attacker.base.types or "강철" in attacker.base.types):
                print(f"{attacker.base.name}는 가시에 찔려 독 상태가 되었다!")
                store.add_log(f"{attacker.base.name}는 가시에 찔려 독 상태가 되었다!")
                
        elif defender.used_move and defender.used_move.name == "블로킹" and move_info.is_touch:
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: change_rank(p, "defense", -2))
            print(f"{attacker.base.name}는 방어가 크게 떨어졌다!!")
            store.add_log(f"{attacker.base.name}는 방어가 크게 떨어졌다!")
            
        return {"success": True}
    
    # 0-1. Check status effects
    if attacker.status:
        status_result = apply_status_effect_before(attacker.status, rate, move_info, side)
        rate = status_result["rate"]
        if not status_result["is_hit"]:
            store.add_log(f"🚫 {attacker.base.name}의 기술은 실패했다!")
            if (attacker.locked_move_turn or 0) > 0: # 기술 실패시 고정 해제처리
                store.update_pokemon(side, active_my if side == "my" else active_enemy, 
                                    lambda p: p.copy_with(locked_move_turn=0))
            return {"success": False}
        # 공격 성공 여부 (풀죽음, 마비, 헤롱헤롱, 얼음, 잠듦 등)
    
    # 0-2. Check if move is self-targeting or field effect
    if move_info.target in ["self", "none"]:
        apply_change_effect(move_info, side, defender.base, is_multi_hit)
        return {"success": True}
    
    # 0-3. Check charging moves
    if not (move_info.name == "솔라빔" and public_env.weather == "쾌청"):
        if move_info.charge_turn and not attacker.is_charging:
            store.update_pokemon(side, active_my if side == "my" else active_enemy,
                                lambda p: setattr(p, 'is_charging', True) or 
                                        setattr(p, 'charging_move', move_info) or
                                        setattr(p, 'position', move_info.position or None) or
                                        p)
            store.add_log(f"{attacker.base.name}은(는) 힘을 모으기 시작했다!")
            return {"success": True}
    
    # 0-4. Check position
    if defender.position is not None:
        position = defender.position
        if (position == "땅" and move_info.name in ["지진", "땅고르기", "땅가르기"]) or \
        (position == "하늘" and move_info.name in ["번개", "땅고르기"]):
            store.add_log(f"{attacker.base.name}은/는 {position}에 있는 상대를 공격하려 한다!")
        else:
            is_hit = False
    
    # 1. Get opponent's type
    opponnent_type = defender.base.types
    
    # 2. Handle type immunity abilities
    if my_pokemon.ability and has_ability(my_pokemon.ability, ["배짱", "심안"]):
        opponnent_type = [t for t in opponnent_type if not is_type_immune(t, move_info.type)]
        
    # 3. Handle ability ignoring abilities
    if my_pokemon.ability and has_ability(my_pokemon.ability, ["틀깨기", "터보블레이즈", "테라볼티지", "균사의힘"]):
        opponent_pokemon.ability = None  # 상대 특성 무효 처리. 실제 특성 메모리엔 영향 x.
        print("틀깨기 발동!")
        
    # 4. Calculate accuracy
    if not (is_always_hit or accuracy > 100):
        if attacker.base.ability and attacker.base.ability.name == "의욕" and move_info.category == "물리":
            accuracy *= 0.8
            
        hit_success = (not move_info.one_hit_ko and 
                    calculate_accuracy(acc_rate, accuracy, my_poke_rank['accuracy'] or 0, op_poke_rank['dodge'] or 0)) or \
                    (move_info.one_hit_ko and random.random() < 0.3) # 일격필살기일 경우 30% 확률로 적중
                
        if not hit_success:
            is_hit = False
            store.add_log(f"🚫 {attacker.base.name}의 공격은 빗나갔다!")
            print(f"{attacker.base.name}의 공격은 빗나갔다!")
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: set_had_missed(p, True))
            
            # Handle move demerit effects
            # 무릎차기, 점프킥 등 빗나가면 반동
            if move_info.demerit_effects:
                for effect in move_info.demerit_effects:
                    if effect.fail:
                        dmg = effect.fail
                        store.update_pokemon(side, active_my if side == "my" else active_enemy,
                                          lambda p: change_hp(p, -(p.base.hp * dmg)))
                        store.add_log(f"🤕 {attacker.base.name}은 반동으로 데미지를 입었다...")
            
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: set_used_move(p, move_info))
            store.update_pokemon(side, active_my if side == "my" else active_enemy,
                            lambda p: use_move_pp(p, move_name, defender.base.ability.name == "프레셔" if defender.base.ability else False, is_multi_hit))
            store.update_pokemon(side, active_my if side == "my" else active_enemy,
                            lambda p: set_charging(p, False, None))
            store.update_pokemon(side, active_my if side == "my" else active_enemy,
                            lambda p: change_position(p, None))
            return {"success": True, "is_hit": False}  # 빗나갔을 때 is_hit: False 반환
    
    # 5-1. Calculate type effectiveness
    if is_hit and move_info.target == "opponent":  # 상대를 대상으로 하는 기술일 경우
        # 상대가 타입 상성 무효화 특성 있을 경우 미리 적용
        if move_info.category == "변화":  # 상대를 때리는 변화기술일 경우 무효 로직
            if move_info.type == "풀" and "풀" in opponent_pokemon.types:
                types *= 0
            if defender.base.ability and defender.base.ability.name == "미라클스킨":
                was_null = True
                store.add_log(f"🥊 {attacker.base.name}은/는 {move_info.name}을/를 사용했다!")
                print(f"{attacker.base.name}은/는 {move_info.name}을/를 사용했다!")
                store.add_log(f"🚫 {attacker.base.name}의 공격은 효과가 없었다...")
                print(f"{side} {attacker.base.name}의 공격은 효과가 없었다...")
                store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: set_used_move(p, move_info))
                store.update_pokemon(side, active_my if side == "my" else active_enemy, 
                                    lambda p: use_move_pp(p, move_name, defender.base.ability.name == "프레셔" if defender.base.ability else False, is_multi_hit))
                store.update_pokemon(opponent_side, active_enemy if side == "my" else active_my, 
                                    lambda p: change_rank(p, "dodge", 2))
                return {"success": True, "was_null": was_null}
        elif opponent_pokemon.ability and opponent_pokemon.ability.defensive:  # 상대 포켓몬이 방어적 특성 있을 경우
            for category in opponent_pokemon.ability.defensive:
                if category in ["damage_nullification", "type_nullification", "damage_reduction"]:
                    if move_info.name == "프리즈드라이" and move_info.type == "노말":
                        move_info.type = "프리즈드라이"
                    # 노말스킨 있어도 프리즈드라이, 플라잉프레스의 타입은 계속 적용됨
                    if move_info.name == "플라잉프레스":
                        print("플라잉프레스 타입상성 적용")
                        fighting_move = move_info.copy(type="격투")
                        flying_move = move_info.copy(type="비행")
                        fighting_effect = apply_defensive_ability_effect_before_damage(fighting_move, side)
                        flying_effect = apply_defensive_ability_effect_before_damage(flying_move, side)
                        types *= fighting_effect * flying_effect
                    else:  # 일반적인 경우
                        types *= apply_defensive_ability_effect_before_damage(move_info, side)
        
        # 방어적 특성이 없는 경우
        if move_info.name == "프리즈드라이" and move_info.type == "노말":
            move_info.type = "프리즈드라이"
        # 노말스킨 있어도 프리즈드라이, 플라잉프레스의 타입은 계속 적용됨
        if move_info.name == "플라잉프레스":
            print("플라잉프레스 타입상성 적용")
            fighting_move = move_info.copy(type="격투")
            flying_move = move_info.copy(type="비행")
            fighting_effect = apply_defensive_ability_effect_before_damage(fighting_move, side)
            flying_effect = apply_defensive_ability_effect_before_damage(flying_move, side)
            types *= fighting_effect * flying_effect
        else:
            types *= calculate_type_effectiveness_with_ability(my_pokemon, opponent_pokemon, move_info)
    
        if move_info.category == "변화" and is_hit:  # 변화기술일 경우
            if my_pokemon.ability and my_pokemon.ability.name == "짓궂은마음" and "악" in opponent_pokemon.types:
                types = 0
            if types == 0:
                was_null = True
                store.add_log(f"🥊 {attacker.base.name}은/는 {move_info.name}을/를 사용했다!")
                print(f"{attacker.base.name}은/는 {move_info.name}을/를 사용했다!")
                store.add_log(f"🚫 {attacker.base.name}의 공격은 효과가 없었다...")
                print(f"{side} {attacker.base.name}의 공격은 효과가 없었다...")
                store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: set_used_move(p, move_info))
                store.update_pokemon(side, active_my if side == "my" else active_enemy, 
                                    lambda p: use_move_pp(p, move_name, defender.base.ability.name == "프레셔" if defender.base.ability else False, is_multi_hit))
                return {"success": True, "was_null": was_null}
            if move_info.name == "아픔나누기":
                print("아픔나누기~~")
                my_hp = attacker.current_hp
                enemy_hp = defender.current_hp
                total_hp = my_hp + enemy_hp
                new_hp = total_hp // 2
                store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: change_hp(p, new_hp - my_hp))
                store.update_pokemon(opponent_side, active_enemy if side == "my" else active_my, lambda p: change_hp(p, new_hp - enemy_hp))
            
            store.add_log(f"🥊 {attacker.base.name}은/는 {move_info.name}을/를 사용했다!")
            print(f"{attacker.base.name}은/는 {move_info.name}을/를 사용했다!")
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: set_used_move(p, move_info))
            store.update_pokemon(side, active_my if side == "my" else active_enemy, 
                                lambda p: use_move_pp(p, move_name, defender.base.ability.name == "프레셔" if defender.base.ability else False, is_multi_hit))
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: set_charging(p, False, None))
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: change_position(p, None))
            return {"success": True}  # 변화기술은 성공으로 처리
        
        store.add_log(f"🥊 {attacker.base.name}은/는 {move_name}을/를 사용했다!")
        print(f"{attacker.base.name}은/는 {move_name}을/를 사용했다!")
        if types >= 4:
            was_effective = 2
            store.add_log(f"👍 {side} {attacker.base.name}의 공격은 효과가 매우 굉장했다!")
            print(f"{side} {attacker.base.name}의 공격은 효과가 매우 굉장했다!")
        if 2 <= types < 4:
            was_effective = 1
            store.add_log(f"👍 {side} {attacker.base.name}의 공격은 효과가 굉장했다!")
            print(f"{side} {attacker.base.name}의 공격은 효과가 굉장했다!")
        if 0 < types <= 0.25:
            was_effective = -2
            store.add_log(f"👎 {attacker.base.name}의 공격은 효과가 매우 별로였다...")
            print(f"{side} {attacker.base.name}의 공격은 효과가 매우 별로였다...")
        if 0.25 < types <= 0.5:
            was_effective = -1
            store.add_log(f"👎 {attacker.base.name}의 공격은 효과가 별로였다...")
            print(f"{side} {attacker.base.name}의 공격은 효과가 별로였다...")
        if types == 0:
            was_null = True
            store.add_log(f"🚫 {attacker.base.name}의 공격은 효과가 없었다...")
            print(f"{side} {attacker.base.name}의 공격은 효과가 없었다...")
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: set_used_move(p, move_info))
            store.update_pokemon(side, active_my if side == "my" else active_enemy, 
                                lambda p: use_move_pp(p, move_name, defender.base.ability.name == "프레셔" if defender.base.ability else False, is_multi_hit))
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: set_charging(p, False, None))
            store.update_pokemon(side, active_my if side == "my" else active_enemy, lambda p: change_position(p, None))
            return {"success": True, "was_null": was_null}
    
    # 5-2. Handle one-hit KO moves
    if move_info.one_hit_ko:
        if defender.base.ability and defender.base.ability.name == "옹골참":
            was_null = True
            store.update_pokemon(side, active_mine, lambda p: set_used_move(p, move_info))
            store.update_pokemon(side, active_mine, 
                                lambda p: use_move_pp(p, move_name, defender.base.ability.name == "프레셔" if defender.base.ability else False, is_multi_hit))
            store.add_log(f"🚫 {attacker.base.name}의 공격은 상대의 옹골참으로 인해 통하지 않았다!")
            return {"success": True, "damage": 0, "was_null": was_null}  # 일격필살기 무효화
            
        store.update_pokemon(opponent_side, active_opponent, lambda p: change_hp(p, -p.base.hp))
        store.update_pokemon(opponent_side, active_opponent, lambda p: set_received_damage(p, p.base.hp))
        store.update_pokemon(side, active_mine, 
                            lambda p: use_move_pp(p, move_name, defender.base.ability.name == "프레셔" if defender.base.ability else False, is_multi_hit))
        store.update_pokemon(side, active_mine, lambda p: set_had_missed(p, False))
        store.update_pokemon(side, active_mine, lambda p: set_used_move(p, move_info))
        store.update_pokemon(side, active_mine, lambda p: set_charging(p, False, None))
        store.update_pokemon(side, active_mine, lambda p: change_position(p, None))
        store.add_log(f"💥 {opponent_pokemon.name}은/는 일격필살기에 쓰러졌다!")
        return {"success": True, "damage": defender.current_hp, "is_hit": True, "was_null": was_null, "was_effective": 0}
        
    # 5-3. Apply same type bonus and previous miss bonus
    if move_info.type in my_pokemon.types or (move_info.type == "프리즈드라이" and "얼음" in my_pokemon.types):
        if my_pokemon.ability and my_pokemon.ability.name == "적응력":
            types *= 2
        else:
            types *= 1.5
            
    if move_info.boost_on_missed_prev and attacker.had_missed:
        # 전 턴에 빗나갔을때 뻥튀기되는 기술 적용
        rate *= 8 / 5

    # 6-1. 날씨 효과 적용
    if weather_effect:  # 날씨 있을 때만
        if weather_effect == "쾌청" and move_info.type == "물":
            print("해가 쨍쨍해서 물 기술이 약해졌다!")
            rate *= 0.5
        if weather_effect == "비" and move_info.type == "불":
            print("비가 와서 불 기술이 약해졌다!")
            rate *= 0.5
        if weather_effect == "모래바람":
            if "바위" in opponent_pokemon.types and move_info.category == "특수":  # 날씨가 모래바람이고 상대가 바위타입일 경우
                print("상대의 특수방어가 강화됐다!")
                rate *= 2 / 3
        elif weather_effect == "싸라기눈":
            if "얼음" in opponent_pokemon.types and move_info.category == "물리":  # 날씨가 싸라기눈이고 상대가 얼음타입일 경우
                print("상대의 방어가 강화됐다!")
                rate *= 2 / 3

    # 6-2. 필드 효과 적용
    if field_effect and "비행" not in my_pokemon.types and not (my_pokemon.ability and my_pokemon.ability.name == "부유"):
        # 필드가 깔려있고, 내 포켓몬이 땅에 있는 포켓몬일 때
        if field_effect == "그래스필드":
            if move_info.type == "풀":
                print("그래스필드에서 기술이 강화됐다!")
                rate *= 1.3
            elif move_info.name in ["지진", "땅고르기"]:
                rate *= 0.5
        elif field_effect == "사이코필드":
            if move_info.type == "에스퍼":
                rate *= 1.3
        elif field_effect == "일렉트릭필드":
            if move_info.type == "전기":
                rate *= 1.3

    # 6-3. 재앙 효과 적용
    if disaster_effect:
        if "재앙의검" in disaster_effect and move_info.category == "물리":
            defense_stat *= 0.75
        elif "재앙의구슬" in disaster_effect and move_info.category == "특수":
            defense_stat *= 0.75
        elif "재앙의그릇" in disaster_effect and move_info.category == "특수":
            attack_stat *= 0.75
        elif "재앙의목간" in disaster_effect and move_info.category == "물리":
            attack_stat *= 0.75

    # 6-4. 빛의장막, 리플렉터, 오로라베일 적용
    enemy_env_effects = duration_store.get_effects("enemy_env")
    my_env_effects = duration_store.get_effects("my_env")
    env_effects = enemy_env_effects if side == "my" else my_env_effects

    def has_active_screen(name: str) -> bool:
        return any(effect["name"] == name for effect in env_effects)

    # 깨트리기, 사이코팽 등 스크린 파괴 기술
    if move_info.effects and any(effect.break_screen for effect in move_info.effects):
        screen_list = ["리플렉터", "빛의장막", "오로라베일"]
        for screen_name in screen_list:
            if screen_name and has_active_screen(screen_name):
                duration_store.remove_effect(opponent_side, screen_name)  # 턴 감소가 아닌 즉시 삭제
                store.add_log(f"💥 {screen_name}이 {'상대' if side == 'my' else '내'} 필드에서 깨졌다!")

    # 벽 통과하는 기술이나 틈새포착이 아닐 경우
    if not (my_pokemon.ability and my_pokemon.ability.name == "틈새포착"):
        # 물리 기술이면 리플렉터나 오로라베일 적용
        if move_info.category == "물리" and (has_active_screen("리플렉터") or has_active_screen("오로라베일")):
            rate *= 0.5
            store.add_log("🧱 장막 효과로 데미지가 줄었다!")
            print("장막효과 적용됨")

        # 특수 기술이면 라이트스크린이나 오로라베일 적용
        if move_info.category == "특수" and (has_active_screen("빛의장막") or has_active_screen("오로라베일")):
            rate *= 0.5
            store.add_log("🧱 장막 효과로 데미지가 줄었다!")
            print("장막효과 적용됨")

    # 7. 공격 관련 특성 적용 (배율)
    rate *= apply_offensive_ability_effect_before_damage(move_info, side, was_effective)

    # 8. 상대 방어 특성 적용 (배율)
    # 만약 위에서 이미 types가 0이더라도, 나중에 곱하면 어차피 0 돼서 상관없음.
    rate *= apply_defensive_ability_effect_before_damage(move_info, side, was_effective)

    # 9. 급소 적용
    if (my_pokemon.ability and my_pokemon.ability.name == "무모한행동" and 
        any(status in ["독", "맹독"] for status in my_poke_status)):
        is_critical = True
        
    if (opponent_pokemon.ability and 
        opponent_pokemon.ability.name in ["전투무장", "조가비갑옷"]):
        cri_rate = 0
        is_critical = False  # 무조건 급소 안 맞음
        
    is_critical = calculate_critical(move_info.critical_rate + cri_rate, 
                                    my_pokemon.ability, 
                                    my_poke_rank['critical'] if my_poke_rank else 0)

    if is_critical:
        if my_pokemon.ability and my_pokemon.ability.name == "스나이퍼":
            rate *= 2.25  # 스나이퍼는 급소 데미지 2배
            my_poke_rank['attack'] = max(0, my_poke_rank['attack'])
            my_poke_rank['sp_attack'] = max(0, my_poke_rank['sp_attack'])
            # 급소 맞출 시에는 내 공격 랭크 다운 무효
            store.add_log(f"👍 {move_name}은/는 급소에 맞았다!")
            print(f"{move_name}은/는 급소에 맞았다!")
        else:
            rate *= 1.5  # 그 외에는 1.5배
            my_poke_rank['attack'] = max(0, my_poke_rank['attack'])
            my_poke_rank['sp_attack'] = max(0, my_poke_rank['sp_attack'])
            store.add_log(f"👍 {move_name}은/는 급소에 맞았다!")
            print(f"{move_name}은/는 급소에 맞았다!")

    # 10. 데미지 계산
    # 공격자가 천진일 때: 상대 방어 랭크 무시
    # 피격자가 천진일 때: 공격자 공격 랭크 무시
    # 랭크 적용
    if my_poke_rank['attack'] and move_info.category == "물리":
        if not (defender.base.ability and defender.base.ability.name == "천진"):
            if move_name == "바디프레스":
                attack_stat *= calculate_rank_effect(my_poke_rank['defense'])
                store.add_log(f"{attacker.base.name}의 방어 랭크 변화가 적용되었다!")
                print(f"{attacker.base.name}의 방어 랭크 변화가 적용되었다!")
            else:
                attack_stat *= calculate_rank_effect(my_poke_rank['attack'])
                store.add_log(f"{attacker.base.name}의 공격 랭크 변화가 적용되었다!")
                print(f"{attacker.base.name}의 공격 랭크 변화가 적용되었다!")

    if my_poke_rank['sp_attack'] and move_info.category == "특수":
        if not (defender.base.ability and defender.base.ability.name == "천진"):
            attack_stat *= calculate_rank_effect(my_poke_rank['sp_attack'])
            store.add_log(f"{attacker.base.name}의 특수공격 랭크 변화가 적용되었다!")
            print(f"{attacker.base.name}의 특수공격 랭크 변화가 적용되었다!")

    if op_poke_rank['defense'] and move_info.category == "물리":
        if not (attacker.base.ability and attacker.base.ability.name == "천진") and \
            not (move_info.effects and any(effect.rank_nullification for effect in move_info.effects)):
            # 공격자가 천진도 아니고, 기술이 랭크업 무시하는 기술도 아닐 경우에만 업데이트
            defense_stat *= calculate_rank_effect(op_poke_rank['defense'])
            store.add_log(f"{defender.base.name}의 방어 랭크 변화가 적용되었다!")
            print(f"{defender.base.name}의 방어 랭크 변화가 적용되었다!")

    if op_poke_rank['sp_defense'] and move_info.category == "특수":
        if not (attacker.base.ability and attacker.base.ability.name == "천진") and \
            not (move_info.effects and any(effect.rank_nullification for effect in move_info.effects)):
            defense_stat *= calculate_rank_effect(op_poke_rank['sp_defense'])
            store.add_log(f"{defender.base.name}의 특수방어 랭크 변화가 적용되었다!")
            print(f"{defender.base.name}의 특수방어 랭크 변화가 적용되었다!")

    # 11. 내구력 계산
    durability = (defense_stat * opponent_pokemon.hp) / 0.411
    print(f"{defender.base.name}의 내구력: {durability}")

    # 12. 결정력 계산
    effectiveness = attack_stat * power * rate * types
    print(f"{attacker.base.name}의 결정력: {effectiveness}")

    # 13. 최종 데미지 계산 (내구력 비율 기반)
    damage = min(defender.current_hp, 
                round((effectiveness / durability) * opponent_pokemon.hp))  # 소수점 반올림

    if move_info.counter:
        if move_info.name == "미러코트" and defender.used_move and defender.used_move.category == "특수":
            damage = (attacker.received_damage or 0) * 2
            print("반사데미지:", damage)
        if move_info.name == "카운터" and defender.used_move and defender.used_move.category == "물리":
            damage = (attacker.received_damage or 0) * 2
            print("반사데미지:", damage)
        if move_info.name == "메탈버스트" and (attacker.received_damage or 0) > 0:
            damage = (attacker.received_damage or 0) * 1.5
            print("반사데미지:", damage)

    if move_info.name == "목숨걸기":
        damage = attacker.current_hp

    # 14. 데미지 적용 및 이후 함수 적용
    if is_hit:
        # 데미지 적용
        if (defender.base.ability and defender.base.ability.name == "옹골참" and 
            defender.current_hp == defender.base.hp and damage >= defender.current_hp):
            print(f"{defender.base.name}의 옹골참 발동!")
            store.add_log(f"🔃 {defender.base.name}의 옹골참 발동!")
            store.update_pokemon(opponent_side, active_opponent, 
                                lambda p: change_hp(p, 1 - p.current_hp))
            store.update_pokemon(opponent_side, active_opponent,
                                lambda p: set_received_damage(p, p.base.hp - 1))
            store.update_pokemon(side, active_mine,
                                lambda p: use_move_pp(p, move_name, 
                                                defender.base.ability.name == "프레셔" if defender.base.ability else False, 
                                                is_multi_hit))
            store.update_pokemon(side, active_mine, lambda p: set_had_missed(p, False))
            store.update_pokemon(side, active_mine, lambda p: set_used_move(p, move_info))
            store.update_pokemon(side, active_mine, lambda p: set_charging(p, False, None))
            store.update_pokemon(side, active_mine, lambda p: change_position(p, None))
            return {"success": True, "damage": defender.current_hp - 1, "was_effective": was_effective, "was_null": was_null}

        if damage >= defender.current_hp:  # 쓰러뜨렸을 경우
            if move_info.name == "마지막일침":
                print(f"{move_info.name}의 부가효과 발동!")
                store.update_pokemon(side, active_mine, 
                                    lambda p: change_rank(p, "attack", 3))
                print(f"{attacker.base.name}의 공격이 3랭크 변했다!")
                store.add_log(f"🔃 {attacker.base.name}의 공격이 3랭크 변했다!")

            if attacker.base.ability and attacker.base.ability.name in ["자기과신", "백의울음"]:
                print("자기과신 발동!")
                store.add_log("자기과신 발동!")
                store.update_pokemon(side, active_mine, 
                                    lambda p: change_rank(p, "attack", 1))
            elif attacker.base.ability and attacker.base.ability.name == "흑의울음":
                store.update_pokemon(side, active_mine, 
                                    lambda p: change_rank(p, "sp_attack", 1))

            if "길동무" in defender.status:
                print(f"{side} 포켓몬은 상대에게 길동무로 끌려갔다...!")
                store.add_log(f"👻 {side} 포켓몬은 상대에게 길동무로 끌려갔다...!")
                store.update_pokemon(side, active_mine, 
                                    lambda p: change_hp(p, -p.base.hp))

        store.update_pokemon(opponent_side, active_opponent, 
                            lambda p: change_hp(p, -damage))
        store.update_pokemon(opponent_side, active_opponent,
                            lambda p: set_received_damage(p, damage))
        store.update_pokemon(side, active_mine,
                            lambda p: use_move_pp(p, move_name, 
                                            defender.base.ability.name == "프레셔" if defender.base.ability else False, 
                                            is_multi_hit))
        store.update_pokemon(side, active_mine, lambda p: set_had_missed(p, False))
        store.update_pokemon(side, active_mine, lambda p: set_used_move(p, move_info))
        store.update_pokemon(side, active_mine, lambda p: set_charging(p, False, None))
        store.update_pokemon(side, active_mine, lambda p: change_position(p, None))

        if move_info.locked_move:
            store.update_pokemon(side, active_mine, 
                                lambda p: p.copy_with(locked_move_turn=3 if random.random() < 0.5 else 2))

        return {"success": True, "damage": damage, "was_effective": was_effective, "was_null": was_null}

    return {"success": False, "was_null": False}

def apply_change_effect(
    move_info: MoveInfo,
    side: SideType,
    defender: Optional[PokemonInfo] = None,
    is_multi_hit: bool = False
) -> None:
    print("apply_change_effect 호출")
    state = store.get_state()
    my_team = state["my_team"]
    enemy_team = state["enemy_team"]
    active_my = state["active_my"]
    active_enemy = state["active_enemy"]
    
    active_team = my_team if side == "my" else enemy_team
    active_mine = active_my if side == "my" else active_enemy
    active_opponent = active_enemy if side == "my" else active_my
    opponent_side = "enemy" if side == "my" else "my"
    
    if move_info.category == "변화":
        if move_info.target == "self":  # 자신에게 거는 기술일 경우
            store.add_log(f"🥊 {side}는 {move_info.name}을/를 사용했다!")
            print(f"{side}는 {move_info.name}을/를 사용했다!")
            
            if move_info.name == "길동무":
                if active_team[active_mine].used_move and active_team[active_mine].used_move.name == "길동무":
                    print("연속으로 발동 실패...!")
                    store.add_log("연속으로 발동 실패...!")
                    # update_pokemon(side, active_mine, lambda p: set_used_move(p, None))  # 다음턴에 다시 길동무 사용 가능하도록
                    store.update_pokemon(side, active_mine, 
                                    lambda p: use_move_pp(p, move_info.name, defender.ability.name == "프레셔" if defender and defender.ability else False, is_multi_hit))
                    return
                else:
                    store.add_log(f"👻 {side}는 {move_info.name}을/를 사용했다!")
                    print(f"{side}는 {move_info.name}을/를 사용했다!")
                    store.update_pokemon(side, active_mine, lambda p: add_status(p, "길동무", side))
            
            if move_info.protect:
                if active_team[active_mine].used_move and active_team[active_mine].used_move.protect:
                    print("연속으로 방어 시도!")
                    store.add_log("연속으로 방어 시도!")
                    if random.random() < 0.5:
                        print("연속으로 방어 성공!")
                        store.add_log("연속으로 방어 성공!")
                        store.update_pokemon(side, active_mine, lambda p: set_protecting(p, True))
                    else:
                        print("연속으로 방어 실패...!")
                        store.add_log("연속으로 방어 실패...!")
                        store.update_pokemon(side, active_mine, lambda p: set_used_move(p, None))
                        store.update_pokemon(side, active_mine, 
                                        lambda p: use_move_pp(p, move_info.name, defender.ability.name == "프레셔" if defender and defender.ability else False, is_multi_hit))
                        return
                else:
                    store.update_pokemon(side, active_mine, lambda p: set_protecting(p, True))
            
            if move_info.effects:
                for effect in move_info.effects:
                    if effect.stat_change:  # 랭크업 기술일 경우
                        for stat_change in effect.stat_change:
                            store.update_pokemon(side, active_mine, 
                                            lambda p: change_rank(p, stat_change.stat, stat_change.change))
                            print(f"{active_team[active_mine].base.name}의 {stat_change.stat}이/가 {stat_change.change}랭크 변했다!")
                            store.add_log(f"🔃 {active_team[active_mine].base.name}의 {stat_change.stat}이/가 {stat_change.change}랭크 변했다!")
                    
                    if effect.heal and effect.heal > 0:
                        heal = effect.heal
                        store.update_pokemon(side, active_mine, 
                                          lambda p: change_hp(p, p.base.hp * heal))
                        print("damage_calculator.py") # 맞은 포켓몬의 체력이 회복되는 오류 확인 위한 디버깅
                    
                    if effect.status:
                        if effect.status == "잠듦" and not (
                            active_team[active_mine].base.ability and 
                            active_team[active_mine].base.ability.name in ["불면", "의기양양"]
                        ):
                            store.update_pokemon(side, active_mine, 
                                            lambda p: add_status(p, effect.status, side))
        
        elif move_info.target == "none":  # 필드에 거는 기술일 경우
            if move_info.trap:  # 독압정, 스텔스록 등
                add_trap(opponent_side, move_info.trap)
                store.add_log(f"🥊 {side}는 {move_info.name}을/를 사용했다!")
                print(f"{side}는 {move_info.name}을/를 사용했다!")
            
            if move_info.field:
                set_field(move_info.field)
                store.add_log(f"⛰️ {side}는 필드를 {move_info.name}로 바꿨다!")
                print(f"{side}는 필드를 {move_info.name}로 바꿨다!")
            
            if move_info.weather:
                set_weather(move_info.name)
                print(f"{side}는 날씨를 {move_info.weather}로 바꿨다!")
            
            if move_info.room:
                set_room(move_info.room)
            
            if move_info.screen:
                set_screen(side, move_info.screen)
    
    store.add_log(f"{side}는 {move_info.name}을/를 사용했다!")
    store.update_pokemon(side, active_mine, lambda p: set_used_move(p, move_info))
    store.update_pokemon(side, active_mine, 
                    lambda p: use_move_pp(p, move_info.name, defender.ability.name == "프레셔" if defender and defender.ability else False, is_multi_hit))

def get_move_info(my_pokemon: PokemonInfo, move_name: str) -> MoveInfo:
    print(f"pokemon: {my_pokemon.name}")
    state = store.get_state()
    my_team = state["my_team"]
    enemy_team = state["enemy_team"]
    
    # 현재 포켓몬이 어느 팀에 있는지 찾기
    battle_pokemon = None
    for pokemon in my_team:
        if pokemon.base.name == my_pokemon.name:
            battle_pokemon = pokemon
            break
    if battle_pokemon is None:
        for pokemon in enemy_team:
            if pokemon.base.name == my_pokemon.name:
                battle_pokemon = pokemon
                break
    
    for move in my_pokemon.moves:
        current_pp = move.pp
        if battle_pokemon and move.name in battle_pokemon.pp:
            current_pp = battle_pokemon.pp[move.name]
            print(f"- {move.name} (PP: {current_pp})")
        if move.name == move_name:
            if battle_pokemon and move_name in battle_pokemon.pp:
                move.pp = battle_pokemon.pp[move_name]
            return move
    raise ValueError(f"{my_pokemon.name}의 {move_name} 기술을 찾을 수 없습니다.") 