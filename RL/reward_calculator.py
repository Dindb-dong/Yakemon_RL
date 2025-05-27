from typing import List, Union
from p_models.move_info import MoveInfo
from p_models.status import StatusManager
from p_models.battle_pokemon import BattlePokemon
from utils.battle_logics.pre_damage_calculator import pre_calculate_move_damage
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

    # 현재 활성화된 포켓몬
    current_pokemon = my_team[active_my]
    target_pokemon = enemy_team[active_enemy]

    # battle_store에서 pre_damage_list 가져오기
    pre_damage_list = store.get_pre_damage_list() if battle_store else []

    # 학습 단계에 따른 가중치 계산
    episode = battle_store.episode if hasattr(battle_store, 'episode') else 0
    if not hasattr(battle_store, 'total_episodes'):
        raise ValueError("total_episodes not set in battle_store. Please set battle_store.total_episodes before training.")
    total_episodes = battle_store.total_episodes
    learning_stage = min(float(episode) / float(total_episodes), 1.0)  # 전체 에피소드 수에 따른 점진적 증가
    print(f"total_episodes: {total_episodes}")
    print(f"learning_stage: {learning_stage}")

    # 교체 후 타입 상성에 따른 보상 계산
    if action >= 4:  # 교체 행동인 경우 (action 4, 5는 교체)
        # damage_calculator.py에서 계산된 was_effective와 was_null 값 사용
        was_effective = result.get('was_effective', 0)
        was_null = result.get('was_null', False)
        print(f"was_effective: {was_effective}")
        if was_null:
            reward += 0.2  # 효과 없는 공격에 대한 보상
            print(f"Good switch: Immune to attack! Reward: {reward}")
        elif was_effective == 2:  # 4배 이상 데미지
            reward -= 0.1  # 매우 큰 페널티
            print(f"Warning: Switched into 4x weakness! Reward: {reward}")
        elif was_effective == 1:  # 2배 데미지
            reward -= 0.05  # 적당한 페널티
            print(f"Warning: Switched into 2x weakness! Reward: {reward}")
        elif was_effective == -1:  # 1/2 데미지
            reward += 0.05 # 적당한 보상
            print(f"Good switch: Resistant to 1/2 damage! Reward: {reward}")
        elif was_effective == -2:  # 1/4 데미지
            reward += 0.1  # 매우 큰 보상
            print(f"Good switch: Resistant to 1/4 damage! Reward: {reward}")
    # 교체가 아니라 싸운 경우
    else:
        # 포켓몬이 기절했거나 행동할 수 없는 경우 리워드 계산하지 않음
        if result and (result.get("was_null", False) or current_pokemon.current_hp <= 0):
            print("Pokemon couldn't move or fainted, skipping reward calculation")
            return reward

        # 데미지가 같은 기술 중 demerit_effects가 있는 기술이 있음에도 demerit_effects가 없는 기술을 사용한 경우 리워드 증가
        for i, (damage, demerit, effect) in enumerate(pre_damage_list):
            if i == action and damage > 0:  # 현재 선택한 공격 기술
                if demerit == 0:  # demerit_effects가 없고 데미지가 0보다 큰 기술
                    # 같은 데미지를 가진 다른 기술 중 demerit_effects가 있는 기술이 있는지 확인
                    has_demerit_with_same_damage = any(
                        d == damage and dem == 1 and d > 0 for d, dem, _ in pre_damage_list
                    )
                    if has_demerit_with_same_damage:
                        reward += 0.1  # 리워드 증가
                        print(f"Good choice: Used a move without demerit effects! Reward: {reward}")
                
                # demerit_effects 조건이 동일한 경우, effects가 있는 기술을 사용하면 리워드 증가
                if effect == 1:  # effects가 있고 데미지가 0보다 큰 기술
                    # 같은 데미지를 가진 다른 기술 중 demerit_effects가 동일하고 effects가 없는 기술이 있는지 확인
                    has_same_demerit_without_effect = any(
                        d == damage and dem == demerit and eff == 0 and d > 0 for d, dem, eff in pre_damage_list
                    )
                    if has_same_demerit_without_effect:
                        reward += 0.1  # 리워드 증가
                        print(f"Good choice: Used a move with effects! Reward: {reward}")

    # 승리/패배에 따른 보상 (가장 중요한 요소)
    if done:
        # 살아있는 포켓몬 수 우위에 대한 보상
        my_pokemon_alive = sum(1 for p in my_team if p.current_hp > 0)
        enemy_pokemon_alive = sum(1 for p in enemy_team if p.current_hp > 0)
        pokemon_count_difference = my_pokemon_alive - enemy_pokemon_alive
        
        # 포켓몬 수 차이에 따른 보상 계산 (이 값은 그대로 유지 - 승리/패배가 가장 중요)
        if pokemon_count_difference <= -3:
            reward -= 5.0  # 상대가 3마리 이상 많음
        elif pokemon_count_difference == -2:
            reward -= 2.0  # 상대가 2마리 많음
        elif pokemon_count_difference == -1:
            reward -= 0.5  # 상대가 1마리 많음
        elif pokemon_count_difference == 1:
            reward += 1.0  # 내가 1마리 많음
        elif pokemon_count_difference == 2:
            reward += 2.0  # 내가 2마리 많음
        elif pokemon_count_difference >= 3:
            reward += 5.0  # 내가 3마리 이상 많음
    
    return reward