from typing import Dict, List, Union, Optional, TypedDict
from p_models.battle_pokemon import BattlePokemon
from p_models.move_info import MoveInfo
from utils.battle_logics.calculate_type_effectiveness import calculate_type_effectiveness_with_ability
from utils.type_relation import calculate_type_effectiveness
from utils.battle_logics.apply_before_damage import apply_offensive_ability_effect_before_damage
from utils.battle_logics.get_best_switch_index import get_best_switch_index
from utils.battle_logics.rank_effect import calculate_rank_effect
import random

def base_ai_choose_action(
    side: str,
    my_team: List[BattlePokemon],
    enemy_team: List[BattlePokemon],
    active_my: int,
    active_enemy: int,
    public_env: Dict,
    enemy_env: Dict,
    my_env: Dict,
    add_log: callable
) -> Union[MoveInfo, Dict[str, Union[str, int]], None]:
    """AI가 행동을 선택하는 기본 로직
    
    Args:
        side: 'my' 또는 'enemy'
        my_team: 내 팀 정보
        enemy_team: 상대 팀 정보
        active_my: 현재 활성화된 내 포켓몬 인덱스
        active_enemy: 현재 활성화된 상대 포켓몬 인덱스
        public_env: 공개된 환경 정보
        enemy_env: 상대방 환경 정보
        my_env: 내 환경 정보
        add_log: 로그 추가 함수
    
    Returns:
        선택된 행동 (기술 사용 또는 교체)
    """
    mine_team = my_team if side == 'my' else enemy_team
    active_index = active_my if side == 'my' else active_enemy
    opponent_team = enemy_team if side == 'my' else my_team
    my_pokemon = mine_team[active_my if side == 'my' else active_enemy]
    enemy_pokemon = opponent_team[active_enemy if side == 'my' else active_my]
    print(f"{side}의 포켓몬: {my_pokemon.base.name}")
    
    # 속도 계산
    user_speed = (enemy_pokemon.base.speed * 
                 calculate_rank_effect(enemy_pokemon.rank['speed']) * 
                (0.5 if '마비' in enemy_pokemon.status else 1))
    
    ai_speed = (my_pokemon.base.speed * 
                calculate_rank_effect(my_pokemon.rank['speed']) * 
                (0.5 if '마비' in my_pokemon.status else 1))
    
    is_ai_faster = ai_speed < user_speed if public_env['room'] == '트릭룸' else ai_speed > user_speed
    roll = random.random()
    ai_hp_ratio = my_pokemon.current_hp / my_pokemon.base.hp
    user_hp_ratio = enemy_pokemon.current_hp / enemy_pokemon.base.hp

    # 사용 가능한 기술 필터링
    usable_moves: List[MoveInfo] = []
    for move in my_pokemon.base.moves:
        # pp 다 쓴 기술 제외
        if my_pokemon.pp.get(move.name, 0) <= 0:
            continue
        # 사슬묶기 당한 기술 제외 
        if my_pokemon.un_usable_move and my_pokemon.un_usable_move.name == move.name:
            continue
        # 중복 상태이상 기술 제외
        if (move.target == 'opponent' and 
            move.power == 0 and 
            any(e.status and e.status in enemy_pokemon.status 
                for e in move.effects or [])):
            continue
        # 이미 쓴 스크린 기술 제외
        active_env = my_env if side == 'my' else enemy_env
        if move.screen and move.screen == active_env.get('screen'):
            continue
        # 땅 -> 비행처럼 무효 타입 제외
        if calculate_type_effectiveness_with_ability(my_pokemon.base, enemy_pokemon.base, move) == 0:
            continue
        # 속이기, 만나자마자 제외
        if move.first_turn_only and my_pokemon.is_first_turn is False:
            continue
        # 방어적 특성에 의한 기술 사용 제한
        if enemy_pokemon.base.ability and enemy_pokemon.base.ability.defensive:
            ability_name = enemy_pokemon.base.ability.name
            
            # 타입 무효화 특성 체크
            if "type_nullification" in enemy_pokemon.base.ability.defensive:
                # 물 타입 무효화 특성
                if ability_name in ["저수", "마중물", "건조피부"] and move.type == "물":
                    continue
                # 불 타입 무효화 특성
                elif ability_name == "타오르는불꽃" and move.type == "불":
                    continue
                # 땅 타입 무효화 특성
                elif ability_name in ["흙먹기", "부유"] and move.type == "땅":
                    continue
                # 풀 타입 무효화 특성
                elif ability_name == "초식" and move.type == "풀":
                    continue
                # 전기 타입 무효화 특성
                elif ability_name in ["전기엔진", "피뢰침"] and move.type == "전기":
                    continue
            
            # 데미지 무효화 특성 체크
            if "damage_nullification" in enemy_pokemon.base.ability.defensive:
                # 가루 계열 기술 무효화
                if ability_name == "방진" and move.affiliation == "가루":
                    continue
                # 폭탄 계열 기술 무효화
                elif ability_name == "방탄" and move.affiliation == "폭탄":
                    continue
                # 우선도 기술 무효화
                elif ability_name == "여왕의위엄" and move.priority > 0:
                    continue
                # 소리 계열 기술 무효화
                elif ability_name == "방음" and move.affiliation == "소리":
                    continue
                
        usable_moves.append(move)
    if len(usable_moves) == 0:
        usable_moves.append(my_pokemon.base.moves[0])

    def type_effectiveness(attacker_types: List[str], defender_types: List[str]) -> float:
        return max(calculate_type_effectiveness(atk, defender_types) for atk in attacker_types)

    def get_best_move() -> MoveInfo:
        best = None
        best_score = -1
        rate = 1

        for move in usable_moves:
            stab = 1.5 if move.type in my_pokemon.base.types else 1.0
            rate = apply_offensive_ability_effect_before_damage(move, side)
            effectiveness = calculate_type_effectiveness(move.type, enemy_pokemon.base.types)
            
            base_power = move.power or 0
            for effect in move.effects or []:
                if effect.double_hit:
                    base_power = 2 * move.power
                elif effect.multi_hit:
                    base_power = 3 * move.power
            
            if move.get_power:
                base_power = move.get_power(enemy_team, 'enemy')
            
            score = base_power * stab * rate * effectiveness
            if score > best_score:
                best_score = score
                best = move

        return best

    def get_speed_up_move() -> Optional[MoveInfo]:
        prankster = True if (my_pokemon.base.ability and my_pokemon.base.ability.name == "심술꾸러기") else False
        enemy_types = enemy_pokemon.base.types

        for move in usable_moves:
            effectiveness = calculate_type_effectiveness(move.type, enemy_types)
            if effectiveness == 0:
                continue

            for effect in move.effects or []:
                for stat_change in effect.stat_change or []:
                    if ((stat_change.target == 'self' and 
                        stat_change.stat == 'speed' and 
                        stat_change.change > 0) or
                        (stat_change.target == 'opponent' and 
                        stat_change.stat == 'speed' and 
                        stat_change.change < 0) or
                        (prankster and 
                        stat_change.target == 'self' and 
                        stat_change.stat == 'speed' and 
                        stat_change.change < 0)):
                        return move
        return None

    def get_attack_up_move() -> Optional[MoveInfo]:
        prankster = my_pokemon.base.ability and my_pokemon.base.ability.name == "심술꾸러기"
        
        for move in usable_moves:
            for effect in move.effects or []:
                if (effect.chance is not None and effect.chance <= 0.5):
                    continue
                    
                for stat_change in effect.stat_change or []:
                    if ((stat_change.target == 'self' and 
                        stat_change.stat in ['attack', 'sp_attack', 'critical'] and 
                        stat_change.change > 0) or
                        (prankster and 
                        stat_change.target == 'self' and 
                        stat_change.stat in ['attack', 'sp_attack'] and 
                        stat_change.change < 0)):
                        return move
        return None

    def get_uturn_move() -> Optional[MoveInfo]:
        return next((m for m in usable_moves if m.u_turn and m.pp > 0), None)

    def get_priority_move() -> Optional[MoveInfo]:
        return next((m for m in usable_moves if m.priority and m.priority > 0 and m.pp > 0), None)

    def get_heal_move() -> Optional[MoveInfo]:
        return next((m for m in usable_moves 
                    if any(e.heal for e in m.effects or [])), None)

    def get_rank_up_move() -> Optional[MoveInfo]:
        rank_up_moves = [m for m in usable_moves 
                        if any((e.chance if e.chance is not None else 0) > 0.5 and 
                                any(s.target == 'self' and s.change > 0 
                                for s in e.stat_change or [])
                                for e in m.effects or [])]
        return rank_up_moves[0] if rank_up_moves else None

    # 모든 교체 가능한 포켓몬이 더 느린지 확인
    is_all_slower = all(
        (p.base.speed * calculate_rank_effect(p.rank['speed']) * 
            (0.5 if '마비' in p.status else 1)) <= 
        (enemy_pokemon.base.speed * calculate_rank_effect(enemy_pokemon.rank['speed']))
        if public_env['room'] == '트릭룸' else
        (p.base.speed * calculate_rank_effect(p.rank['speed']) * 
            (0.5 if '마비' in p.status else 1)) <= 
        (enemy_pokemon.base.speed * calculate_rank_effect(enemy_pokemon.rank['speed']))
        for i, p in enumerate(mine_team)
        if i != active_index and p.current_hp > 0
    )

    has_good_matchup = any(
        calculate_type_effectiveness(p.base.types[0], enemy_pokemon.base.types) > 1.5
        for i, p in enumerate(mine_team)
        if i != active_index and p.current_hp / p.base.hp > 0.3
    )

    def get_speed_down_move() -> Optional[MoveInfo]:
        return next((m for m in usable_moves 
                    if any(any(s.target == 'opponent' and 
                            s.stat == 'speed' and 
                            s.change < 0 
                            for s in e.stat_change or [])
                        for e in m.effects or [])), None)

    speed_down_move = get_speed_down_move()
    ai_to_user = type_effectiveness(my_pokemon.base.types, enemy_pokemon.base.types)
    user_to_ai = type_effectiveness(enemy_pokemon.base.types, my_pokemon.base.types)
    best_move = get_best_move()
    rank_up_move = get_rank_up_move()
    uturn_move = get_uturn_move()
    speed_up_move = get_speed_up_move()
    attack_up_move = get_attack_up_move()
    priority_move = get_priority_move()
    heal_move = get_heal_move()
    screen_moves = next((m for m in usable_moves if m.screen), None)
    support_move = next((m for m in usable_moves 
                        if m.category == '변화' and m != rank_up_move), None)
    counter_move = next((m for m in usable_moves 
                        if m.name in ['카운터', '미러코트', '메탈버스트']), None)
    
    has_switch_option = (any(i != active_enemy and p.current_hp > 0 
                        for i, p in enumerate(mine_team)) and 
                        '교체불가' not in my_pokemon.status)
    
    is_ai_low_hp = ai_hp_ratio < 0.35
    is_ai_high_hp = ai_hp_ratio > 0.8
    is_user_low_hp = user_hp_ratio < 0.35
    is_user_very_low_hp = user_hp_ratio < 0.2
    is_user_high_hp = user_hp_ratio > 0.8
    is_attack_reinforced = (mine_team[active_index].rank['attack'] > 1 or 
                        mine_team[active_index].rank['sp_attack'] > 1)
    switch_index = get_best_switch_index(side)

    # 0. is_charging일 경우
    if my_pokemon.is_charging and my_pokemon.charging_move:
        return my_pokemon.charging_move

    # 0-1. 행동불능 상태일 경우
    if my_pokemon.cannot_move:
        add_log(f"😵 {my_pokemon.base.name}은 아직 회복되지 않아 움직이지 못한다!")
        print(f"😵 {my_pokemon.base.name}은 아직 회복되지 않아 움직이지 못한다!")
        return best_move if side == 'my' else None # 원래 None이였는데, 오류때문에 일단 기술 뱉어내도록. 
    # battle_seqenence에서 처리. 

    # === 1. 내 포켓몬이 쓰러졌으면 무조건 교체 ===
    if my_pokemon.current_hp <= 0:
        switch_options = [
            {'pokemon': p, 'index': i}
            for i, p in enumerate(mine_team)
            if p.current_hp > 0 and i != active_index
        ]

        # 우선순위 기준: (1) 상대보다 빠르고 (2) 상대 체력 적음
        prioritized = next(
            (opt for opt in switch_options
             if ((opt['pokemon'].base.speed * 
                calculate_rank_effect(opt['pokemon'].rank['speed'])) <
                user_speed if public_env['room'] == '트릭룸'
                 else (opt['pokemon'].base.speed * 
                    calculate_rank_effect(opt['pokemon'].rank['speed'])) >
                user_speed) and user_hp_ratio < 0.35),
            None
        )

        if prioritized:
            add_log(f"⚡ {side}는 막타를 노려 빠른 포켓몬을 꺼냈다")
            print(f"⚡ {side}는 막타를 노려 빠른 포켓몬을 꺼냈다")
            return {"type": "switch", "index": prioritized['index']}
        elif switch_index != -1:  # 빠른 포켓몬은 없지만 교체할 수 있는 포켓몬이 있는 경우
            add_log(f"⚡ {side}는 상성이 좋은 포켓몬을 내보냈다")
            print(f"⚡ {side}는 상성이 좋은 포켓몬을 내보냈다")
            return {"type": "switch", "index": switch_index}
        else:  # 교체할 수 있는 포켓몬이 없는 경우
            add_log(f"😱 {side}는 교체할 포켓몬이 없어 최후의 발악을 시도한다!")
            print(f"😱 {side}는 교체할 포켓몬이 없어 최후의 발악을 시도한다!")
            return best_move

    # === 2. 플레이어가 더 빠를 경우 ===
    if not is_ai_faster:
        if user_to_ai > 1 and not (ai_to_user > 1):  # ai가 확실히 불리
            if is_user_very_low_hp and priority_move:
                add_log(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착하여 선공기 사용!")
                print(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착하여 선공기 사용!")
                return priority_move
                
            if roll < 0.3 and counter_move and is_ai_high_hp:
                enemy_atk = (enemy_pokemon.base.attack * 
                            calculate_rank_effect(enemy_pokemon.rank['attack']))
                enemy_sp_atk = (enemy_pokemon.base.sp_attack * 
                            calculate_rank_effect(enemy_pokemon.rank['sp_attack']))

                if ((counter_move.name == '카운터' and enemy_atk >= enemy_sp_atk) or
                    (counter_move.name == '미러코트' and enemy_sp_atk > enemy_atk) or
                    (counter_move.name == '메탈버스트')):
                    add_log(f"🛡️ {side}는 반사 기술 {counter_move.name} 사용 시도!")
                    print(f"🛡️ {side}는 반사 기술 {counter_move.name} 사용 시도!")
                    return counter_move

            if roll < 0.4 and speed_up_move and ai_hp_ratio > 0.5:
                add_log(f"🦅 {side}는 상대의 맞교체 또는 랭크업을 예측하고 스피드 상승을 시도!")
                print(f"🦅 {side}는 상대의 맞교체 또는 랭크업을 예측하고 스피드 상승을 시도!")
                return speed_up_move

            if roll < 0.5 and speed_down_move and ai_hp_ratio > 0.5:
                add_log(f"🦅 {side}는 상대의 스피드 감소를 시도!")
                print(f"🦅 {side}는 상대의 스피드 감소를 시도!")
                return speed_down_move

            if roll < 0.6 and has_switch_option and switch_index != -1:
                if is_all_slower and not has_good_matchup:
                    add_log(f"🤔 {side}는 교체해도 의미 없다고 판단하고 체력 보존을 택했다")
                    print(f"🤔 {side}는 교체해도 의미 없다고 판단하고 체력 보존을 택했다")
                    return best_move
                else:
                    add_log(f"🐢 {side}는 느리고 불리하므로 교체 선택")
                    print(f"🐢 {side}는 느리고 불리하므로 교체 선택")
                    return {"type": "switch", "index": switch_index}

            add_log(f"🥊 {side}는 최고 위력기를 선택")
            print(f"🥊 {side}는 최고 위력기를 선택")
            return best_move

        elif ai_to_user > 1 and not (user_to_ai > 1):  # ai가 느리지만 상성 확실히 유리
            if screen_moves and (is_ai_faster or is_ai_high_hp):
                add_log(f"🛡️ {side}는 방어용 스크린을 설치한다!")
                print(f"🛡️ {side}는 방어용 스크린을 설치한다!")
                return screen_moves

            if roll < 0.2 and is_ai_low_hp and has_switch_option:
                if switch_index != -1:
                    add_log(f"🐢 {side}는 느리고 상성은 유리하지만 체력이 낮아 교체를 시도한다!")
                    print(f"🐢 {side}는 느리고 상성은 유리하지만 체력이 낮아 교체를 시도한다!")
                    return {"type": "switch", "index": switch_index}

            if speed_up_move and is_ai_high_hp:
                add_log(f"🐢 {side}는 느리지만 상성이 유리하고 체력이 높아 스피드 상승을 시도한다!")
                print(f"🐢 {side}는 느리지만 상성이 유리하고 체력이 높아 스피드 상승을 시도한다!")
                return speed_up_move

            if roll < 0.1 and is_ai_high_hp and has_switch_option and uturn_move:
                add_log(f"🐢 {side}는 상성은 유리하지만 상대의 교체를 예상하고 유턴을 사용한다!")
                print(f"🐢 {side}는 상성은 유리하지만 상대의 교체를 예상하고 유턴을 사용한다!")
                return uturn_move

            if roll < 0.4:
                add_log(f"🥊 {side}는 상성 우위를 살려 가장 강한 기술로 공격한다!")
                print(f"🥊 {side}는 상성 우위를 살려 가장 강한 기술로 공격한다!")
                return best_move

            if roll < 0.6 and support_move:
                add_log(f"🤸‍♀️ {side}는 변화를 시도한다!")
                print(f"🤸‍♀️ {side}는 변화를 시도한다!")
                return support_move

            if roll < 0.7 and has_switch_option:
                if switch_index != -1:
                    add_log(f"🛼 {side}는 상대의 교체를 예상하고 맞교체한다!")
                    print(f"🛼 {side}는 상대의 교체를 예상하고 맞교체한다!")
                    return {"type": "switch", "index": switch_index}

            add_log(f"🥊 {side}는 예측샷으로 최고 위력기를 사용한다!")
            print(f"🥊 {side}는 예측샷으로 최고 위력기를 사용한다!")
            return best_move

        else:  # 느리고 상성 같은 경우
            if screen_moves and (is_ai_faster or is_ai_high_hp):
                add_log(f"🛡️ {side}는 방어용 스크린을 설치한다!")
                print(f"🛡️ {side}는 방어용 스크린을 설치한다!")
                return screen_moves

            if is_ai_high_hp and speed_up_move:
                add_log(f"🦅 {side}는 스피드 상승을 시도한다!")
                print(f"🦅 {side}는 스피드 상승을 시도한다!")
                return speed_up_move

            if is_ai_high_hp and user_hp_ratio < 0.5:
                add_log(f"🥊 {side}는 상대의 체력이 적고 상성이 같아서 가장 강한 기술로 공격한다!")
                print(f"🥊 {side}는 상대의 체력이 적고 상성이 같아서 가장 강한 기술로 공격한다!")
                return best_move

            if roll < 0.2 and counter_move and is_ai_high_hp:
                enemy_atk = (enemy_pokemon.base.attack * 
                            calculate_rank_effect(enemy_pokemon.rank['attack']))
                enemy_sp_atk = (enemy_pokemon.base.sp_attack * 
                            calculate_rank_effect(enemy_pokemon.rank['sp_attack']))

                if ((counter_move.name == '카운터' and enemy_atk >= enemy_sp_atk) or
                    (counter_move.name == '미러코트' and enemy_sp_atk > enemy_atk) or
                    (counter_move.name == '메탈버스트')):
                    add_log(f"🛡️ {side}는 반사 기술 {counter_move.name} 사용 시도!")
                    print(f"🛡️ {side}는 반사 기술 {counter_move.name} 사용 시도!")
                    return counter_move

            if roll < 0.2 and has_switch_option:
                if switch_index != -1:
                    add_log(f"🐢 {side}는 상성이 같지만 느려서 상대에게 유리한 포켓몬으로 교체한다!")
                    print(f"🐢 {side}는 상성이 같지만 느려서 상대에게 유리한 포켓몬으로 교체한다!")
                    return {"type": "switch", "index": switch_index}

            add_log(f"🥊 {side}는 상성이 같아서 가장 강한 기술로 공격한다!")
            print(f"🥊 {side}는 상성이 같아서 가장 강한 기술로 공격한다!")
            return best_move

    # === 3. AI가 더 빠를 경우 ===
    if ai_to_user > 1 and not (user_to_ai > 1):  # ai가 상성상 확실히 유리
        if screen_moves and (is_ai_faster or is_ai_high_hp):
            add_log(f"🛡️ {side}는 방어용 스크린을 설치한다!")
            print(f"🛡️ {side}는 방어용 스크린을 설치한다!")
            return screen_moves

        if roll < 0.5 and is_ai_high_hp and attack_up_move:
            add_log(f"🦅 {side}는 빠르므로 공격 상승 기술 사용!")
            print(f"🦅 {side}는 빠르므로 공격 상승 기술 사용!")
            return attack_up_move

        if not is_ai_high_hp and is_attack_reinforced:
            add_log(f"🥊 {side}는 강화된 공격력으로 공격!")
            print(f"🥊 {side}는 강화된 공격력으로 공격!")
            return best_move

        if is_user_low_hp:  # 막타치기 로직
            add_log(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착!")
            print(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착!")
            return best_move

        if is_ai_low_hp and heal_move:
            add_log(f"➕ {side}는 빠르지만 체력이 낮으므로 회복 기술 사용!")
            print(f"➕ {side}는 빠르지만 체력이 낮으므로 회복 기술 사용!")
            return heal_move

        if roll < 0.1 and has_switch_option and switch_index != -1:
            add_log(f"🛼 {side}는 상대 교체 예상하고 맞교체")
            print(f"🛼 {side}는 상대 교체 예상하고 맞교체")
            return {"type": "switch", "index": switch_index}

        if roll < 0.2 and support_move:
            add_log(f"🤸‍♀️ {side}는 변화 기술 사용")
            print(f"🤸‍♀️ {side}는 변화 기술 사용")
            return support_move

        add_log(f"🥊 {side}는 가장 강한 기술로 공격")
        print(f"🥊 {side}는 가장 강한 기술로 공격")
        return best_move

    elif not (ai_to_user > 1) and user_to_ai > 1:  # ai가 빠르고 상성은 확실히 불리
        if screen_moves and (is_ai_faster or is_ai_high_hp):
            add_log(f"🛡️ {side}는 방어용 스크린을 설치한다!")
            print(f"🛡️ {side}는 방어용 스크린을 설치한다!")
            return screen_moves

        if is_user_low_hp:
            add_log(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착!")
            print(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착!")
            return best_move

        if roll < 0.2 and counter_move and is_ai_high_hp:
            enemy_atk = (enemy_pokemon.base.attack * 
                        calculate_rank_effect(enemy_pokemon.rank['attack']))
            enemy_sp_atk = (enemy_pokemon.base.sp_attack * 
                        calculate_rank_effect(enemy_pokemon.rank['sp_attack']))

            if ((counter_move.name == '카운터' and enemy_atk >= enemy_sp_atk) or
                (counter_move.name == '미러코트' and enemy_sp_atk > enemy_atk) or
                (counter_move.name == '메탈버스트')):
                add_log(f"🛡️ {side}는 반사 기술 {counter_move.name} 사용 시도!")
                print(f"🛡️ {side}는 반사 기술 {counter_move.name} 사용 시도!")
                return counter_move

        if uturn_move and has_switch_option:
            add_log(f"🛼 {side}는 빠르지만 불리하므로 유턴으로 교체!")
            print(f"🛼 {side}는 빠르지만 불리하므로 유턴으로 교체!")
            return uturn_move

        if is_ai_low_hp:
            add_log(f"🥊 {side}는 일단은 강하게 공격!")
            print(f"🥊 {side}는 일단은 강하게 공격!")
            return best_move

        if roll < 0.15 and support_move:
            add_log(f"🤸‍♀️ {side}는 변화 기술을 사용")
            print(f"🤸‍♀️ {side}는 변화 기술을 사용")
            return support_move

        if roll < 0.25 and (has_switch_option or is_ai_low_hp):
            if switch_index != -1:
                add_log(f"🛼 {side}는 빠르지만 상성상 유리한 포켓몬이 있으므로 교체")
                print(f"🛼 {side}는 빠르지만 상성상 유리한 포켓몬이 있으므로 교체")
                return {"type": "switch", "index": switch_index}

        add_log(f"🥊 {side}는 가장 강한 공격 시도")
        print(f"🥊 {side}는 가장 강한 공격 시도")
        return best_move

    elif ai_to_user > 1 and user_to_ai > 1:  # 서로가 약점을 찌르는 경우
        if screen_moves and (is_ai_faster or is_ai_high_hp):
            add_log(f"🛡️ {side}는 방어용 스크린을 설치한다!")
            print(f"🛡️ {side}는 방어용 스크린을 설치한다!")
            return screen_moves

        if roll < 0.1 and is_ai_high_hp and attack_up_move:
            add_log(f"🏋️‍♂️ {side}는 빠르므로 공격 상승 기술 사용!")
            print(f"🏋️‍♂️ {side}는 빠르므로 공격 상승 기술 사용!")
            return attack_up_move

        if is_user_low_hp:  # 막타치기 로직
            add_log(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착!")
            print(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착!")
            return best_move

        if is_ai_low_hp and heal_move:
            add_log(f"➕ {side}는 빠르지만 체력이 낮으므로 회복 기술 사용!")
            print(f"➕ {side}는 빠르지만 체력이 낮으므로 회복 기술 사용!")
            return heal_move

        if roll < 0.1 and has_switch_option and switch_index != -1:
            add_log(f"🛼 {side}는 상대 교체 예상하고 맞교체")
            print(f"🛼 {side}는 상대 교체 예상하고 맞교체")
            return {"type": "switch", "index": switch_index}

        if roll < 0.2 and support_move:
            add_log(f"🤸‍♀️ {side}는 변화 기술 사용")
            print(f"🤸‍♀️ {side}는 변화 기술 사용")
            return support_move

        add_log(f"🥊 {side}는 가장 강한 기술로 공격")
        print(f"🥊 {side}는 가장 강한 기술로 공격")
        return best_move

    else:  # 특별한 상성 없을 때
        if screen_moves and (is_ai_faster or is_ai_high_hp):
            add_log(f"🛡️ {side}는 방어용 스크린을 설치한다!")
            print(f"🛡️ {side}는 방어용 스크린을 설치한다!")
            return screen_moves

        if is_user_low_hp:
            add_log(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착!")
            print(f"🦅 {side}는 상대 포켓몬의 빈틈을 포착!")
            return best_move

        if is_ai_high_hp and attack_up_move:
            add_log(f"🏋️‍♂️ {side}는 공격 상승 기술 사용")
            print(f"🏋️‍♂️ {side}는 공격 상승 기술 사용")
            return attack_up_move

        if roll < 0.15 and has_switch_option and switch_index != -1:
            add_log(f"🦅 {side}는 빠르지만 상대의 약점을 찌르기 위해 상대에게 유리한 포켓몬으로 교체")
            print(f"🦅 {side}는 빠르지만 상대의 약점을 찌르기 위해 상대에게 유리한 포켓몬으로 교체")
            return {"type": "switch", "index": switch_index}

        add_log(f"🥊 {side}는 더 빠르기에 가장 강한 공격 시도")
        print(f"🥊 {side}는 더 빠르기에 가장 강한 공격 시도")
        return best_move 