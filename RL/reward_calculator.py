from typing import List, Union
from RL.base_ai_choose_action import type_effectiveness
from p_models.pokemon_info import PokemonInfo
from p_models.battle_pokemon import BattlePokemon
from utils.battle_logics.calculate_order import calculate_speed
from context.battle_store import store

def calculate_reward(
    my_team: list[BattlePokemon],
    enemy_team: list[BattlePokemon],
    active_my: int,
    active_enemy: int,
    public_env: dict,
    my_env: dict,
    enemy_env: dict,
    turn: int,
    my_effects: list,
    enemy_effects: list,
    action: int,
    done: bool,
    battle_store=None,
    duration_store=None,
    result: dict[str, Union[bool, int]] = None,
    outcome: dict[str, Union[bool, int]] = None,
    enemy_post_pokemon: BattlePokemon = None,
    my_post_pokemon: BattlePokemon = None,
    is_monte_carlo: bool = False,
) -> float:
    """
    전략적 요소를 고려한 최적화된 보상 계산
    Args:
        my_team: 내 팀 (BattlePokemon 리스트)
        enemy_team: 상대 팀 (BattlePokemon 리스트)
        active_my: 내 활성 포켓몬 인덱스
        active_enemy: 상대 활성 포켓몬 인덱스
        public_env: 공개 환경 정보
        my_env: 내 환경 정보
        enemy_env: 상대 환경 정보
        turn: 현재 턴
        my_effects: 내 효과 리스트
        enemy_effects: 상대 효과 리스트
        action: 수행한 행동 (int)
        done: 종료 여부
        battle_store: (옵션) 배틀 스토어
        duration_store: (옵션) 지속 효과 스토어
    Returns:
        float: 계산된 보상
    """     
    # 보상 초기화
    reward = 0.0
    my_post_pokemon.used_move = outcome.get("used_move", None)
    # 현재 활성화된 포켓몬
    current_pokemon = my_team[active_my]
    my_alive_team: List[PokemonInfo] = [p.base for p in my_team if p.current_hp > 0]
    target_pokemon = enemy_team[active_enemy]
    # print(f"reward_calculator: my_post_pokemon: {my_post_pokemon.base.name}")
    # print(f"reward_calculator: my_post_pokemon.used_move: {my_post_pokemon.used_move.name if my_post_pokemon.used_move else 'None'}")
    # print(f"reward_calculator: my_post_pokemon.current_hp: {my_post_pokemon.current_hp}")
    # print(f"reward_calculator: my_post_pokemon.dealt_damage: {my_post_pokemon.dealt_damage}")
    # print(f"reward_calculator: enemy_post_pokemon: {enemy_post_pokemon.base.name}")
    # print(f"reward_calculator: enemy_post_pokemon.current_hp: {enemy_post_pokemon.current_hp}")
    # print(f"reward_calculator: enemy_post_pokemon.base.hp: {enemy_post_pokemon.base.hp}")
    # print(f"reward_calculator: current_pokemon: {current_pokemon.base.name}")
    # print(f"reward_calculator: current_pokemon.used_move: {current_pokemon.used_move.name if current_pokemon.used_move else 'None'}")
    # print(f"reward_calculator: current_pokemon.dealt_damage: {current_pokemon.dealt_damage}")
    # print(f"reward_calculator: target_pokemon: {target_pokemon.base.name}")
    # print(f"reward_calculator: target_pokemon.received_damage: {target_pokemon.received_damage}")

    # battle_store에서 pre_damage_list 가져오기
    pre_damage_list = store.get_pre_damage_list() if battle_store else []

    # 학습 단계에 따른 가중치 계산
    #episode = battle_store.episode if hasattr(battle_store, 'episode') else 0
    # if not hasattr(battle_store, 'total_episodes'):
    #     raise ValueError("total_episodes not set in battle_store. Please set battle_store.total_episodes before training.")
    #total_episodes = battle_store.total_episodes
    #learning_stage = min(float(episode) / float(total_episodes), 1.0)  # 전체 에피소드 수에 따른 점진적 증가
    # print(f"total_episodes: {total_episodes}")
    # print(f"learning_stage: {learning_stage}")
    # 타입 상성 계산
    agent_to_ai = type_effectiveness(current_pokemon.base.types, target_pokemon.base.types)
    ai_to_agent = type_effectiveness(target_pokemon.base.types, current_pokemon.base.types)
    # print(f"agent_to_ai: {agent_to_ai}")
    # print(f"ai_to_agent: {ai_to_agent}")

    # 교체 후 타입 상성에 따른 보상 계산
    if action >= 4:  # 교체 행동인 경우 (action 4, 5는 교체)
        # damage_calculator.py에서 계산된 was_effective와 was_null 값 사용
        was_effective = result.get('was_effective', 0)
        was_null = result.get('was_null', False)
        print(f"was_effective: {was_effective}")
        if calculate_speed(current_pokemon) > calculate_speed(target_pokemon):
            reward += 0.5
            if not is_monte_carlo:
                print(f"Good switch: Agent is faster than enemy! Reward: {reward}")
            else: print(f"Agent is faster than enemy! Reward: {reward}")
        if agent_to_ai > 1 and ai_to_agent < 1:
            reward += 1.5
            if not is_monte_carlo:
                print(f"Good switch: Agent to AI is way stronger! Reward: {reward}")
            else: print(f"Agent to AI is way stronger! Reward: {reward}")
        elif agent_to_ai > 1 and ai_to_agent == 1:
            reward += 0.5
            if not is_monte_carlo:
                print(f"Good switch: Agent to AI is stronger! Reward: {reward}")
            else: print(f"Agent to AI is stronger! Reward: {reward}")
        elif agent_to_ai < 1 and ai_to_agent > 1:
            reward -= 3.0
            if not is_monte_carlo:
                print(f"Bad switch: AI to Agent is way stronger! Reward: {reward}")
            else: print(f"AI to Agent is way stronger! Reward: {reward}")
        elif agent_to_ai < 1 and ai_to_agent == 1:
            reward -= 1.5
            if not is_monte_carlo:
                print(f"Bad switch: AI to Agent is stronger! Reward: {reward}")
            else: print(f"AI to Agent is stronger! Reward: {reward}")
        if was_null:
            reward += 1.5  # 효과 없는 공격에 대한 보상
            if not is_monte_carlo:
                print(f"Good switch: Immune to attack! Reward: {reward}")
            else: print(f"Immune to attack! Reward: {reward}")
        elif was_effective == 2:  # 4배 이상 데미지
            reward -= 3.0  # 매우 큰 페널티
            if not is_monte_carlo:
                print(f"Bad switch: Switched into 4x weakness! Reward: {reward}")
            else: print(f"Switched into 4x weakness! Reward: {reward}")
        elif was_effective == 1:  # 2배 데미지
            reward -= 2.0  # 적당한 페널티
            if not is_monte_carlo:
                print(f"Bad switch: Switched into 2x weakness! Reward: {reward}")
            else: print(f"Switched into 2x weakness! Reward: {reward}")
        elif was_effective == -1:  # 1/2 데미지
            reward += 0.3 # 적당한 보상
            if not is_monte_carlo:
                print(f"Good switch: Resistant to 1/2 damage! Reward: {reward}")
            else: print(f"Resistant to 1/2 damage! Reward: {reward}")
        elif was_effective == -2:  # 1/4 데미지
            reward += 0.6  # 매우 큰 보상
            if not is_monte_carlo:
                print(f"Good switch: Resistant to 1/4 damage! Reward: {reward}")
            else: print(f"Resistant to 1/4 damage! Reward: {reward}")
    # 교체가 아니라 싸운 경우
    elif action < 4:
        # damage_calculator.py에서 계산된 was_effective와 was_null 값 사용
        was_effective = outcome.get('was_effective', 0)
        was_null = outcome.get('was_null', False)
        print(f"was_effective: {was_effective}")
        if was_null:
            reward -= 2.5  # 효과 없는 공격에 대한 보상
            if not is_monte_carlo:
                print(f"Bad Attack: Immune to attack... Reward: {reward}")
            else: print(f"Immune to attack... Reward: {reward}")
        elif was_effective == 2:  # 4배 이상 데미지
            reward += 2.0  # 매우 큰 리워드
            if not is_monte_carlo:
                print(f"Good Attack: Attacked to 4x effectiveness! Reward: {reward}")
            else: print(f"Attacked to 4x effectiveness! Reward: {reward}")
        elif was_effective == 1:  # 2배 데미지
            reward += 1.5  # 적당한 리워드
            if not is_monte_carlo:
                print(f"Good Attack: Attacked to 2x effectiveness! Reward: {reward}")
            else: print(f"Attacked to 2x effectiveness! Reward: {reward}")
        elif was_effective == -1:  # 1/2 데미지
            reward -= 1.5 # 적당한 페널티
            if not is_monte_carlo:
                print(f"Bad Attack: Attacked to 1/2 effectiveness! Reward: {reward}")
            else: print(f"Attacked to 1/2 effectiveness! Reward: {reward}")
        elif was_effective == -2:  # 1/4 데미지
            reward -= 2.0  # 매우 큰 페널티
            if not is_monte_carlo:
                print(f"Bad Attack: Attacked to 1/4 effectiveness! Reward: {reward}")
            else: print(f"Attacked to 1/4 effectiveness! Reward: {reward}")
        # 포켓몬이 행동할 수 없는 경우 리워드 계산하지 않음 (선공을 맞고 기절한 경우는 제외)
        if my_post_pokemon.cannot_move is not None and my_post_pokemon.cannot_move == True:
            if not is_monte_carlo:
                print("Pokemon couldn't move, skipping reward calculation")
        # 속이기, 만나자마자 잘못 사용했을 경우 
        if my_post_pokemon.used_move is not None and my_post_pokemon.used_move.first_turn_only and my_post_pokemon.is_first_turn is False:
            reward -= 5.0
            if not is_monte_carlo:
                print("Bad choice: Used a first turn only move out of turn")
            else: print(f"Penalty: Used a first turn only move out of turn")
        # 이전 포켓몬이 공격 못하고 죽었을 때
        if (my_post_pokemon.used_move is None and (my_post_pokemon.base.name != current_pokemon.base.name)
            and (target_pokemon.used_move is not None and not target_pokemon.used_move.exile)):
            print("이전 포켓몬이 공격 못하고 쓰러졌거나 교체하자마자 쓰러짐")
            # 공격 못하고 죽음 
            reward -= 5.0
        # 공격, 특수공격 랭크업 기술 쓰고 살아있을 때 (상대보다 빠른 조건)
        if (my_post_pokemon.used_move is not None and my_post_pokemon.used_move.effects and any(effect.chance == 1.0 and effect.stat_change and any(sc.stat == 'attack' or sc.stat == 'special_attack' for sc in effect.stat_change) for effect in my_post_pokemon.used_move.effects)
            and my_post_pokemon.base.name == current_pokemon.base.name and calculate_speed(current_pokemon) > calculate_speed(target_pokemon)):
            reward += 2.5
            if not is_monte_carlo:
                print(f"Good choice: Used a rank change (attack/sp_attack) move to increase stats! Reward: {reward}")
            else: print(f"Used a rank change (attack/sp_attack) move to increase stats! Reward: {reward}")
        # 스피드 랭크업 기술 쓰고 스피드 추월했을 경우 
        if (calculate_speed(my_post_pokemon) < calculate_speed(enemy_post_pokemon) and calculate_speed(current_pokemon) > calculate_speed(target_pokemon)
            and my_post_pokemon.base.name == current_pokemon.base.name and enemy_post_pokemon.base.name == target_pokemon.base.name
            and my_post_pokemon.used_move is not None and my_post_pokemon.used_move.effects and any(effect.chance == 1.0 and effect.stat_change and any(sc.stat == 'speed' for sc in effect.stat_change) for effect in my_post_pokemon.used_move.effects)):
            reward += 3.0
            if not is_monte_carlo:
                print(f"Good choice: Used a speed rank change move to overtake the enemy! Reward: {reward}")
            else: print(f"Used a speed rank change move to overtake the enemy! Reward: {reward}")
        # 상대 쓰러뜨렸으면 리워드 증가
        if (current_pokemon.dealt_damage == enemy_post_pokemon.current_hp or my_post_pokemon.dealt_damage == enemy_post_pokemon.current_hp
            or (current_pokemon.base.name == my_post_pokemon.base.name and current_pokemon.used_move is not None and not current_pokemon.used_move.u_turn and
                current_pokemon.dealt_damage is not None and current_pokemon.dealt_damage > 0 and (target_pokemon.received_damage is None or target_pokemon.received_damage == 0))):
            reward += 6.0
            if not is_monte_carlo:
                print(f"Good choice: Used a move to defeat the enemy! Reward: {reward}")
            else: print(f"Used a move to defeat the enemy! Reward: {reward}")
        # 상대 때리면 리워드 증가 
        if current_pokemon.dealt_damage and enemy_post_pokemon.current_hp != 0:
            reward += (current_pokemon.dealt_damage / enemy_post_pokemon.base.hp) * 1.2
            print(f"dealt_damage: {current_pokemon.dealt_damage}")
            print(f"enemy_post_pokemon.base.hp: {enemy_post_pokemon.base.hp}")
            print(f"hit! : {reward}")
        # 내가 먼저 선공, 상대의 후공으로 기절했을 때
        elif ((my_post_pokemon.base.name != current_pokemon.base.name) and (current_pokemon.used_move == None) and (enemy_post_pokemon.base.name == target_pokemon.base.name)
            and my_post_pokemon.used_move is not None and not my_post_pokemon.used_move.u_turn and target_pokemon.received_damage is not None):
            reward += (target_pokemon.received_damage / target_pokemon.base.hp) * 0.3
            print(f"received_damage (fallback): {target_pokemon.received_damage}")
            print(f"enemy_post_pokemon.base.hp: {enemy_post_pokemon.base.hp}")
            print(f"hit(fallback) : {reward}")
            
        # 유턴 기술로 때렸을 때
        elif ((my_post_pokemon.base.name != current_pokemon.base.name) and (current_pokemon.used_move == None) and (enemy_post_pokemon.base.name == target_pokemon.base.name)
            and my_post_pokemon.used_move is not None and my_post_pokemon.used_move.u_turn and target_pokemon.received_damage is not None):
            reward += (target_pokemon.received_damage / target_pokemon.base.hp) * 0.2
            print(f"received_damage (u_turn): {target_pokemon.received_damage}")
            print(f"enemy_post_pokemon.base.hp: {enemy_post_pokemon.base.hp}")
            print(f"hit(u_turn) : {reward}")
        # 기술은 썼는데 데미지 못주고 죽음
        elif ((my_post_pokemon.base.name != current_pokemon.base.name) and (current_pokemon.used_move == None) and (enemy_post_pokemon.base.name == target_pokemon.base.name)
            and my_post_pokemon.used_move is not None and target_pokemon.received_damage is None):
            # 그런데 그 기술이 확정 랭업기였을때
            if my_post_pokemon.used_move.effects and any(effect.chance == 1.0 and effect.stat_change and any(sc.target == 'self' for sc in effect.stat_change) for effect in my_post_pokemon.used_move.effects):
                reward -= 2.5  # 스탯 상승 기술 사용 후 바로 기절한 경우 페널티
                if not is_monte_carlo:
                    print(f"Bad choice: Used stat boost move ({my_post_pokemon.used_move.name}) but fainted immediately!")
                else: print(f"Penalty for using stat boost move and fainting: {reward}")
        # 상태이상 기술 중복 사용 시 페널티
        if (my_post_pokemon.used_move is not None and my_post_pokemon.used_move.effects 
            and was_null is True
            and any(effect.chance == 1.0 for effect in my_post_pokemon.used_move.effects)
            and any(effect.status in target_pokemon.status for effect in my_post_pokemon.used_move.effects)):
            reward -= 3.0  # 상태이상 기술 중복 사용 시 페널티  
            if not is_monte_carlo:
                print(f"Bad choice: Used status condition move ({my_post_pokemon.used_move.name}) but Enemy already has status condition!")
            else: print(f"Penalty for using status condition move in duplicate: {reward}")
        """
        # 스탯 상승 기술 사용 후 바로 기절한 경우 (위력 없음)
        elif ((my_post_pokemon.base.name != current_pokemon.base.name) and (current_pokemon.used_move == None) and (enemy_post_pokemon.base.name == target_pokemon.base.name)
            and my_post_pokemon.used_move is not None and my_post_pokemon.used_move.effects and 
            any(effect.chance == 1.0 and effect.stat_change and 
                any(sc.target == 'self' for sc in effect.stat_change) 
                for effect in my_post_pokemon.used_move.effects) and
            my_post_pokemon.used_move.power == 0):
            print(f"Bad choice: Used stat boost move ({my_post_pokemon.used_move.name}) but fainted immediately!")
            reward -= 1.0  # 스탯 상승 기술 사용 후 바로 기절한 경우 페널티
            print(f"Penalty for using stat boost move and fainting: {reward}")
        """

        # 선공을 맞고 죽은 경우가 아닐 때만 기술 선택에 따른 리워드 계산
        if current_pokemon.current_hp > 0:
            # 데미지가 같은 기술 중 demerit_effects가 있는 기술이 있음에도 demerit_effects가 없는 기술을 사용한 경우 리워드 증가
            for i, (damage, demerit, effect) in enumerate(pre_damage_list):
                if i == action and damage > 0:  # 현재 선택한 공격 기술
                    if demerit == 0:  # demerit_effects가 없고 데미지가 0보다 큰 기술
                        # 같은 데미지를 가진 다른 기술 중 demerit_effects가 있는 기술이 있는지 확인
                        has_demerit_with_same_damage = any(
                            d == damage and dem == 1 and d > 0 for d, dem, _ in pre_damage_list
                        )
                        if has_demerit_with_same_damage:
                            reward += 0.5  # 리워드 증가
                            if not is_monte_carlo:
                                print(f"Good choice: Used a move without demerit effects! Reward: {reward}")
                            else: print(f"Used a move without demerit effects! Reward: {reward}")
                    
                    # demerit_effects 조건이 동일한 경우, effects가 있는 기술을 사용하면 리워드 증가
                    if effect == 1:  # effects가 있고 데미지가 0보다 큰 기술
                        # 같은 데미지를 가진 다른 기술 중 demerit_effects가 동일하고 effects가 없는 기술이 있는지 확인
                        has_same_demerit_without_effect = any(
                            d == damage and dem == demerit and eff == 0 and d > 0 for d, dem, eff in pre_damage_list
                        )
                        if has_same_demerit_without_effect:
                            reward += 0.5  # 리워드 증가
                            if not is_monte_carlo:
                                print(f"Good choice: Used a move with effects! Reward: {reward}")
                            else: print(f"Used a move with effects! Reward: {reward}")

    # # 승리/패배에 따른 보상 (가장 중요한 요소)
    # if done:
    #     # 살아있는 포켓몬 수 우위에 대한 보상
    #     my_pokemon_alive = sum(1 for p in my_team if p.current_hp > 0)
    #     enemy_pokemon_alive = sum(1 for p in enemy_team if p.current_hp > 0)
    #     pokemon_count_difference = my_pokemon_alive - enemy_pokemon_alive
    #     my_team_alive = any(pokemon.current_hp > 0 for pokemon in my_team)
    #     enemy_team_alive = any(pokemon.current_hp > 0 for pokemon in enemy_team)
    #     victory = 1 if my_team_alive and not enemy_team_alive else 0

    #     print(f"Game Over - My alive: {my_pokemon_alive}, Enemy alive: {enemy_pokemon_alive}, Difference: {pokemon_count_difference}")
        
    #     # 포켓몬 수 차이에 따른 보상 계산 (이 값은 그대로 유지 - 승리/패배가 가장 중요)
    #     if pokemon_count_difference == -3:
    #         reward -= 2.0  # 상대가 3마리 이상 많음
    #         print(f"You lose! 0 : 3")
    #     elif pokemon_count_difference == -2:
    #         reward -= 1.0  # 상대가 2마리 많음
    #         print(f"You lose! 0 : 2")
    #     elif pokemon_count_difference == -1:
    #         reward -= 0.5  # 상대가 1마리 많음
    #         print(f"You lose! 0 : 1")
    #     elif pokemon_count_difference == 1:
    #         reward += 3.0  # 내가 1마리 많음
    #         print(f"You win! 1 : 0")
    #     elif pokemon_count_difference == 2:
    #         reward += 4.0  # 내가 2마리 많음
    #         print(f"You win! 2 : 0")
    #     elif pokemon_count_difference == 3:
    #         reward += 5.0  # 내가 3마리 이상 많음
    #         print(f"You win! 3 : 0")
    #     else:
    #         if victory:
    #             reward += 2.0
    #             print(f"You win! 0 : 0")
    #         else:
    #             reward -= 0.5
    #             print(f"You lose! 0 : 0")
        
    #    print(f"Final reward after win/loss calculation: {reward}")
    
    return reward