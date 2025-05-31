from typing import List, Dict, Optional, Literal
from p_models.move_info import MoveInfo
from p_models.pokemon_info import PokemonInfo
from p_models.battle_pokemon import BattlePokemon
from context.battle_store import store
from context.duration_store import duration_store
from utils.battle_logics.rank_effect import calculate_critical, calculate_rank_effect
from utils.battle_logics.calculate_type_effectiveness import calculate_type_effectiveness_with_ability, is_type_immune
from utils.battle_logics.helpers import has_ability
from utils.battle_logics.apply_before_damage import apply_defensive_ability_effect_before_damage, apply_offensive_ability_effect_before_damage
from utils.apply_skin_type_effect import apply_skin_type_effect
from context.battle_environment import PublicBattleEnvironment

SideType = Literal["my", "enemy"]

def pre_calculate_move_damage( # 배틀을 실행하기 전에 만약 다른 기술을 썼다면? 을 저장하는 함수 
    move_name: str,
    side: SideType,
    current_index: int,
    is_always_hit: bool = False,
    additional_damage: Optional[int] = None,
    override_power: Optional[int] = None,
    was_late: bool = False,
    is_multi_hit: bool = False,
    attacker: BattlePokemon = None,
    defender: BattlePokemon = None,
    my_rank: Dict = None,
    op_rank: Dict = None,
    heal_check: bool = False,
) -> float:
    # 일격기는 여기서 처리 안함 
    # Get battle state
    state = store.get_state()
    my_team: List[BattlePokemon] = state["my_team"]
    enemy_team: List[BattlePokemon] = state["enemy_team"]
    active_my: int = state["active_my"]
    active_enemy: int = state["active_enemy"]
    public_env: PublicBattleEnvironment = state["public_env"]
    # Set attacker and defender based on side
    my_pokemon: PokemonInfo = attacker.base
    opponent_pokemon: PokemonInfo = defender.base
    opponent_side = "enemy" if side == "my" else "my"
    active_mine = active_my if side == "my" else active_enemy
    active_opponent = active_enemy if side == "my" else active_my
    team = my_team if side == "my" else enemy_team
    # Get move info and apply skin type effect
    move_info = get_move_info(my_pokemon, move_name)
    move_list: List[MoveInfo] = [move for move in attacker.base.moves]
    # 남아있는 pp가 0 이상인 기술 필터링
    valid_damage_moves = [
        move for move in move_list 
        if attacker.pp.get(move.name, 0) > 0
    ]
    if move_info not in valid_damage_moves:
        return 0.0
    move_info = apply_skin_type_effect(move_info, my_pokemon.ability.name if my_pokemon.ability else None)
    # Get environment effects
    weather_effect = public_env.weather
    field_effect = public_env.field
    disaster_effect = public_env.disaster
    
    # Initialize variables
    types = 1.0  # Type effectiveness multiplier
    base_power = override_power if override_power is not None else move_info.power  # Base power
    # Apply Technician ability
    if attacker.base.ability and attacker.base.ability.name == "테크니션" and base_power <= 60:
        base_power *= 1.5
    # Calculate power
    additional_damage = 0
    additional_damage += base_power if attacker.base.ability and attacker.base.ability.name == "테크니션" and base_power is not None else 0
    power = (move_info.get_power(team, side, base_power) + (additional_damage or 0)
                if move_info.get_power else base_power + (additional_damage or 0))
    # Initialize other variables
    cri_rate = 0
    rate = 1.0
    if was_late and attacker.base.ability and attacker.base.ability.name == "애널라이즈":
        rate *= 1.3
    is_critical = False
    was_effective = 0
    was_null = False
    my_poke_rank = attacker.rank
    op_poke_rank = defender.rank
    my_poke_status = attacker.status
    
    # Calculate attack and defense stats
    attack_stat = my_pokemon.attack if move_info.category == "물리" else my_pokemon.sp_attack
    if move_name == "바디프레스":
        attack_stat = my_pokemon.defense
    if move_name == "속임수":
        attack_stat = opponent_pokemon.attack
    if attacker.base.ability and attacker.base.ability.name == "무기력" and attacker.current_hp <= (attacker.base.hp / 2):
        attack_stat *= 0.5
    defense_stat = opponent_pokemon.defense if move_info.category == "물리" else opponent_pokemon.sp_defense
    if move_name == "사이코쇼크":
        defense_stat = opponent_pokemon.defense
    
    # 0-1. Check status effects
    
    # 0-2. Check if move is self-targeting or field effect
    # if move_info.target in ["self"]:
    #     return apply_heal_effect(move_info, side)
    
    # 0-3. Check charging moves
    
    # 0-4. Check position
    if defender.position is not None:
        position = defender.position
        if (position == "땅" and move_info.name in ["지진", "땅고르기", "땅가르기"]) or \
        (position == "하늘" and move_info.name in ["번개", "폭풍"]):
            pass
        else:
            types *= 0
            return 0.0
    
    # 1. Get opponent's type
    opponnent_type = defender.base.types
    
    # 2. Handle type immunity abilities
    if my_pokemon.ability and has_ability(my_pokemon.ability, ["배짱", "심안"]):
        opponnent_type = [t for t in opponnent_type if not is_type_immune(t, move_info.type)]
        
    # 3. Handle ability ignoring abilities
    if my_pokemon.ability and has_ability(my_pokemon.ability, ["틀깨기", "터보블레이즈", "테라볼티지", "균사의힘"]):
        opponent_pokemon.ability = None  # 상대 특성 무효 처리. 실제 특성 메모리엔 영향 x.

    # 4. Calculate accuracy
    
    # 5-1. Calculate type effectiveness
    if move_info.target == "opponent":  # 상대를 대상으로 하는 기술일 경우
        # 상대가 타입 상성 무효화 특성 있을 경우 미리 적용
        if move_info.category == "변화":  # 상대를 때리는 변화기술일 경우 무효 로직
            if move_info.type == "풀" and "풀" in opponent_pokemon.types:
                types *= 0
            if defender.base.ability and defender.base.ability.name == "미라클스킨":
                return 0.0
        elif opponent_pokemon.ability and opponent_pokemon.ability.defensive:  # 상대 포켓몬이 방어적 특성 있을 경우
            for category in opponent_pokemon.ability.defensive:
                if category in ["damage_nullification", "type_nullification", "damage_reduction"]:
                    if move_info.name == "프리즈드라이" and move_info.type == "노말":
                        move_info.type = "프리즈드라이"
                    # 노말스킨 있어도 프리즈드라이, 플라잉프레스의 타입은 계속 적용됨
                    if move_info.name == "플라잉프레스":
                        fighting_move = move_info.copy(type="격투")
                        flying_move = move_info.copy(type="비행")
                        fighting_effect = apply_defensive_ability_effect_before_damage(fighting_move, side, pre_damage=True)
                        flying_effect = apply_defensive_ability_effect_before_damage(flying_move, side, pre_damage=True)
                        types *= fighting_effect * flying_effect
                    else:  # 일반적인 경우
                        types *= apply_defensive_ability_effect_before_damage(move_info, side, pre_damage=True)
        
        # 방어적 특성이 없는 경우
        if move_info.name == "프리즈드라이" and move_info.type == "노말":
            move_info.type = "프리즈드라이"
        # 노말스킨 있어도 프리즈드라이, 플라잉프레스의 타입은 계속 적용됨
        if move_info.name == "플라잉프레스":
            fighting_move = move_info.copy(type="격투")
            flying_move = move_info.copy(type="비행")
            fighting_effect = apply_defensive_ability_effect_before_damage(fighting_move, side, pre_damage=True)
            flying_effect = apply_defensive_ability_effect_before_damage(flying_move, side, pre_damage=True)
            types *= fighting_effect * flying_effect
        else:
            types *= calculate_type_effectiveness_with_ability(my_pokemon, opponent_pokemon, move_info)
    
        if move_info.category == "변화":  # 변화기술일 경우
            if my_pokemon.ability and my_pokemon.ability.name == "짓궂은마음" and "악" in opponent_pokemon.types:
                types = 0
                return 0.0
            if types == 0:
                return 0.0
            if move_info.name == "아픔나누기":
                print("pre_calc: 아픔나누기~~")
                my_hp = attacker.current_hp
                enemy_hp = defender.current_hp
                total_hp = my_hp + enemy_hp
                new_hp = total_hp // 2
                return enemy_hp - new_hp # 음수값 나올 수 있는게 맞음.
            return 0.0
        
    elif move_info.target in ["self", "none"]:  # 자신이나 필드를 대상으로 하는 기술일 경우
        return 0.0
    # 5-2. Handle one-hit KO moves
        
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
            rate *= 0.5
        if weather_effect == "비" and move_info.type == "불":
            rate *= 0.5
        if weather_effect == "모래바람":
            if "바위" in opponent_pokemon.types and move_info.category == "특수":  # 날씨가 모래바람이고 상대가 바위타입일 경우
                rate *= 2 / 3
        elif weather_effect == "싸라기눈":
            if "얼음" in opponent_pokemon.types and move_info.category == "물리":  # 날씨가 싸라기눈이고 상대가 얼음타입일 경우
                rate *= 2 / 3

    # 6-2. 필드 효과 적용
    if field_effect and "비행" not in my_pokemon.types and not (my_pokemon.ability and my_pokemon.ability.name == "부유"):
        # 필드가 깔려있고, 내 포켓몬이 땅에 있는 포켓몬일 때
        if field_effect == "그래스필드":
            if move_info.type == "풀":
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


    # 벽 통과하는 기술이나 틈새포착이 아닐 경우
    if not (my_pokemon.ability and my_pokemon.ability.name == "틈새포착"):
        # 물리 기술이면 리플렉터나 오로라베일 적용
        if move_info.category == "물리" and (has_active_screen("리플렉터") or has_active_screen("오로라베일")):
            rate *= 0.5

        # 특수 기술이면 라이트스크린이나 오로라베일 적용
        if move_info.category == "특수" and (has_active_screen("빛의장막") or has_active_screen("오로라베일")):
            rate *= 0.5

    # 7. 공격 관련 특성 적용 (배율)
    rate *= apply_offensive_ability_effect_before_damage(move_info, side, was_effective)

    # 8. 상대 방어 특성 적용 (배율)
    # 만약 위에서 이미 types가 0이더라도, 나중에 곱하면 어차피 0 돼서 상관없음.
    rate *= apply_defensive_ability_effect_before_damage(move_info, side, was_effective, pre_damage=True)

    # 9. 급소 적용
    # 급소 맞을 확률이 1/2 이상일 경우에만 작용하도록. 
    if ((my_poke_rank['critical'] if my_poke_rank else 0) + move_info.critical_rate + 
        (1 if my_pokemon.ability and my_pokemon.ability.name == "대운" else 0) 
        >= 2):
        print(f"pre_calc: 급소 적용")
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
            else:
                rate *= 1.5  # 그 외에는 1.5배
                my_poke_rank['attack'] = max(0, my_poke_rank['attack'])
                my_poke_rank['sp_attack'] = max(0, my_poke_rank['sp_attack'])

    # 10. 데미지 계산
    # 공격자가 천진일 때: 상대 방어 랭크 무시
    # 피격자가 천진일 때: 공격자 공격 랭크 무시
    # 랭크 적용
    if my_poke_rank['attack'] and move_info.category == "물리":
        if not (defender.base.ability and defender.base.ability.name == "천진"):
            if move_name == "바디프레스":
                attack_stat *= calculate_rank_effect(my_poke_rank['defense'])
            else:
                attack_stat *= calculate_rank_effect(my_poke_rank['attack'])

    if my_poke_rank['sp_attack'] and move_info.category == "특수":
        if not (defender.base.ability and defender.base.ability.name == "천진"):
            attack_stat *= calculate_rank_effect(my_poke_rank['sp_attack'])

    if op_poke_rank['defense'] and move_info.category == "물리":
        if not (attacker.base.ability and attacker.base.ability.name == "천진") and \
            not (move_info.effects and any(effect.rank_nullification for effect in move_info.effects)):
            # 공격자가 천진도 아니고, 기술이 랭크업 무시하는 기술도 아닐 경우에만 업데이트
            defense_stat *= calculate_rank_effect(op_poke_rank['defense'])

    if op_poke_rank['sp_defense'] and move_info.category == "특수":
        if not (attacker.base.ability and attacker.base.ability.name == "천진") and \
            not (move_info.effects and any(effect.rank_nullification for effect in move_info.effects)):
            defense_stat *= calculate_rank_effect(op_poke_rank['sp_defense'])

    # 11. 내구력 계산
    durability = (defense_stat * opponent_pokemon.hp) / 0.411

    # 12. 결정력 계산
    effectiveness = attack_stat * power * rate * types

    # 13. 최종 데미지 계산 (내구력 비율 기반)
    damage = min(defender.current_hp, 
                round((effectiveness / durability) * opponent_pokemon.hp))  # 소수점 반올림

    if move_info.name == "목숨걸기" and types != 0:
        damage = attacker.current_hp

    # 14. 데미지 적용 및 이후 함수 적용
    # 데미지 적용
    # 옹골참 처리
    if (defender.base.ability and defender.base.ability.name == "옹골참" and 
        defender.current_hp == defender.base.hp and damage >= defender.current_hp):
        print(f"pre_calc: {defender.base.name}의 옹골참 발동!")
        damage = defender.current_hp - 1

    return damage


# def apply_heal_effect( # 회복기술의 경우 회복량 뱉어내기 
#     move_info: MoveInfo,
#     side: SideType
# ) -> float:
#     print("apply_heal_effect 호출")
#     state = store.get_state()
#     my_team = state["my_team"]
#     enemy_team = state["enemy_team"]
#     active_my = state["active_my"]
#     active_enemy = state["active_enemy"]
#     heal = 0.0
#     active_team = my_team if side == "my" else enemy_team
#     active_mine = active_my if side == "my" else active_enemy
    
#     if move_info.category == "변화":
#         if move_info.target == "self":  # 자신에게 거는 기술일 경우
            
#             if move_info.effects:
#                 for effect in move_info.effects:
#                     if effect.heal and effect.heal > 0:
#                         heal = effect.heal * active_team[active_mine].base.hp
#                         print("pre_damage_calculator.py") # 맞은 포켓몬의 체력이 회복되는 오류 확인 위한 디버깅
#     return heal

def get_move_info(my_pokemon: PokemonInfo, move_name: str) -> MoveInfo:
    
    for move in my_pokemon.moves:
        if move.name == move_name:
            return move
    raise ValueError(f"pre_damage_calculator.py: {my_pokemon.name}의 {move_name} 기술을 찾을 수 없습니다.") 