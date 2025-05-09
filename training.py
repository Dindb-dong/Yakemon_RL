#%% [markdown]
# Yakemon 강화학습 에이전트 학습
# 각 알고리즘을 독립적으로 테스트하기 위한 스크립트

#%% [markdown]
# 필요한 라이브러리 임포트
import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
from datetime import datetime
import json
import random
from collections import deque

# 환경 관련 import
from env.battle_env import YakemonEnv

# 모델 관련 import
from p_models.pokemon_info import PokemonInfo
from p_models.rank_state import RankManager
from p_models.status import StatusManager
from p_models.move_info import MoveInfo, MoveEffect, StatChange
from p_models.battle_pokemon import BattlePokemon
from p_models.ability_info import AbilityInfo

# 유틸리티 관련 import
from utils.type_relation import calculate_type_effectiveness
from utils.battle_logics.battle_sequence import battle_sequence, BattleAction
from utils.battle_logics.damage_calculator import calculate_move_damage
from utils.battle_logics.rank_effect import calculate_rank_effect
from utils.replay_buffer import ReplayBuffer

# 에이전트 관련 import
from agent.dddqn_agent import DDDQNAgent

# RL 관련 import
from RL.reward_calculator import calculate_reward
from RL.get_state_vector import get_state

# 데이터 관련 import
from p_data.move_data import move_data
from p_data.ability_data import ability_data
from p_data.mock_pokemon import create_mock_pokemon_list

# 컨텍스트 관련 import
from context.battle_store import battle_store_instance
from context.battle_environment import PublicBattleEnvironment, IndividualBattleEnvironment
from context.duration_store import duration_store
from context.form_check_wrapper import with_form_check


# 전역 변수 초기화
battle_store = battle_store_instance
duration_store = duration_store


# 하이퍼파라미터 설정
HYPERPARAMS = {
    "learning_rate": 0.001,
    "gamma": 0.99,
    "epsilon_start": 1.0,
    "epsilon_end": 0.01,
    "epsilon_decay": 0.995,
    "batch_size": 64,
    "memory_size": 10000,
    "target_update": 10,
    "num_episodes": 1000,
    "save_interval": 100,
    "test_episodes": 100,
    "state_dim": 144,  # get_state_vector의 출력 차원
    "action_dim": 8,   # 4개의 기술 + 4개의 교체
}

#%% [markdown]
# 학습 함수 정의
def train_agent(
    env,
    agent: DDDQNAgent,
    num_episodes: int,
    save_path: str = 'models',
    agent_name: str = 'ddqn'
) -> tuple:
    """
    에이전트 학습 함수
    """
    rewards_history = []
    losses_history = []
    best_reward = float('-inf')
    
    # 모델 저장 디렉토리 생성
    os.makedirs(save_path, exist_ok=True)
    
    # 하이퍼파라미터 저장
    with open(os.path.join(save_path, f'{agent_name}_hyperparams.json'), 'w') as f:
        json.dump(HYPERPARAMS, f, indent=4)
    
    for episode in range(num_episodes):
        # 매 에피소드마다 새로운 포켓몬 팀 생성
        my_team = create_mock_pokemon_list()[:6]  # 6마리 선택
        enemy_team = create_mock_pokemon_list()[6:12]  # 다른 6마리 선택
        
        # 각 포켓몬의 기술과 특성 설정
        for pokemon in my_team + enemy_team:
            # 기술 설정
            moves = []
            for i in range(4):
                move = MoveInfo(
                    name=f'기술{i}',
                    power=random.randint(40, 120),
                    accuracy=random.randint(70, 100),
                    pp=random.randint(5, 20),
                    type=random.choice(pokemon['base']['types']),
                    category=random.choice(['physical', 'special', 'status']),
                    effect=MoveEffect(
                        stat_changes=[StatChange('atk', 1)],
                        status_effect=random.choice(['burn', 'paralyze', 'poison', None]),
                        weather=random.choice(['sunny', 'rainy', 'sandstorm', 'hail', None]),
                        field=random.choice(['electric', 'psychic', 'grassy', 'misty', None])
                    )
                )
                moves.append(move)
            pokemon['base']['moves'] = moves
            
            # 특성 설정
            ability = AbilityInfo(
                id=random.randint(1, 100),
                name=random.choice(['엽록소', '맹화', '급류', '심록']),
                description='강력한 특성',
                appear=['rank_change'],
                offensive=['damage_buff'],
                defensive=['damage_reduction'],
                util=['hp_low_trigger'],
                un_touchable=False
            )
            pokemon['ability'] = ability
        
        # 배틀 환경 초기화
        state = env.reset(my_team=my_team, enemy_team=enemy_team)
        
        total_reward = 0
        total_loss = 0
        steps = 0
        
        while True:
            # 현재 상태 벡터 생성
            state_dict = get_state(
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env.__dict__,
                my_env=env.my_env.__dict__,
                enemy_env=env.enemy_env.__dict__,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            # 정해진 순서로 상태 벡터 생성
            state_keys = sorted(state_dict.keys())  # 키를 정렬하여 고정된 순서 사용
            state_vector = [state_dict[key] for key in state_keys]
            
            # 행동 선택
            action = agent.select_action(state_vector, env.battle_store, env.duration_store)
            
            # 행동 실행
            next_state, reward, done, _ = env.step(action)
            
            # 다음 상태 벡터 생성
            next_state_dict = get_state(
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env.__dict__,
                my_env=env.my_env.__dict__,
                enemy_env=env.enemy_env.__dict__,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            # 정해진 순서로 다음 상태 벡터 생성
            next_state_vector = [next_state_dict[key] for key in state_keys]
            
            # 보상 계산
            reward = calculate_reward(
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env.__dict__,
                my_env=env.my_env.__dict__,
                enemy_env=env.enemy_env.__dict__,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects,
                action=action,
                done=done,
                battle_store=env.battle_store,
                duration_store=env.duration_store
            )
            
            # 경험 저장
            agent.store_transition(state_vector, action, reward, next_state_vector, done)
            
            # 학습
            if len(agent.memory) > agent.batch_size:
                loss = agent.update()
                total_loss += loss
            
            state_vector = next_state_vector
            total_reward += reward
            steps += 1
            
            if done:
                break
        
        # 에피소드 결과 저장
        avg_reward = total_reward / steps
        avg_loss = total_loss / steps if total_loss > 0 else 0
        rewards_history.append(avg_reward)
        losses_history.append(avg_loss)
        
        # 최고 성능 모델 저장
        if avg_reward > best_reward:
            best_reward = avg_reward
            agent.save(os.path.join(save_path, f'{agent_name}_best.pth'))
        
        # 주기적으로 모델 저장
        if (episode + 1) % HYPERPARAMS["save_interval"] == 0:
            agent.save(os.path.join(save_path, f'{agent_name}_episode_{episode+1}.pth'))
        
        # 학습 진행 상황 출력
        print(f'Episode {episode+1}/{num_episodes}')
        print(f'Average Reward: {avg_reward:.2f}')
        print(f'Average Loss: {avg_loss:.4f}')
        print(f'Epsilon: {agent.epsilon:.4f}')
        print(f'Steps: {steps}')
        print('-' * 50)
    
    return rewards_history, losses_history

#%% [markdown]
# 시각화 함수 정의
def plot_training_results(
    rewards_history: list,
    losses_history: list,
    agent_name: str,
    save_path: str = 'results'
) -> None:
    """
    학습 결과 시각화
    """
    os.makedirs(save_path, exist_ok=True)
    
    # 보상 그래프
    plt.figure(figsize=(10, 5))
    plt.plot(rewards_history)
    plt.title(f'{agent_name} Training Rewards')
    plt.xlabel('Episode')
    plt.ylabel('Average Reward')
    plt.savefig(os.path.join(save_path, f'{agent_name}_rewards.png'))
    plt.close()
    
    # 손실 그래프
    plt.figure(figsize=(10, 5))
    plt.plot(losses_history)
    plt.title(f'{agent_name} Training Losses')
    plt.xlabel('Episode')
    plt.ylabel('Average Loss')
    plt.savefig(os.path.join(save_path, f'{agent_name}_losses.png'))
    plt.close()

#%% [markdown]
# 테스트 함수 정의
def test_agent(
    env,
    agent: DDDQNAgent,
    num_episodes: int = 10
) -> tuple:
    """
    학습된 에이전트 테스트
    """
    rewards = []
    steps_list = []
    
    for episode in range(num_episodes):
        # 테스트용 포켓몬 팀 생성
        my_team = create_mock_pokemon_list()[:6]
        enemy_team = create_mock_pokemon_list()[6:12]
        
        # 각 포켓몬의 기술과 특성 설정
        for pokemon in my_team + enemy_team:
            # 기술 설정
            moves = []
            for i in range(4):
                move = MoveInfo(
                    name=f'기술{i}',
                    power=random.randint(40, 120),
                    accuracy=random.randint(70, 100),
                    pp=random.randint(5, 20),
                    type=random.choice(pokemon['types']),
                    category=random.choice(['physical', 'special', 'status']),
                    effect=MoveEffect(
                        stat_changes=[StatChange('atk', 1)],
                        status_effect=random.choice(['burn', 'paralyze', 'poison', None]),
                        weather=random.choice(['sunny', 'rainy', 'sandstorm', 'hail', None]),
                        field=random.choice(['electric', 'psychic', 'grassy', 'misty', None])
                    )
                )
                moves.append(move)
            pokemon['moves'] = moves
            
            # 특성 설정
            ability = AbilityInfo(
                id=random.randint(1, 100),
                name=random.choice(['엽록소', '맹화', '급류', '심록']),
                description='강력한 특성',
                appear=['rank_change'],
                offensive=['damage_buff'],
                defensive=['damage_reduction'],
                util=['hp_low_trigger'],
                un_touchable=False
            )
            pokemon['ability'] = ability
        
        # 배틀 환경 초기화
        state = env.reset(my_team=my_team, enemy_team=enemy_team)
        
        total_reward = 0
        steps = 0
        
        while True:
            # 현재 상태 벡터 생성
            state_vector = get_state(
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.active_my,
                active_enemy=env.battle_store.active_enemy,
                public_env=env.battle_store.public_env,
                my_env=env.battle_store.my_env,
                enemy_env=env.battle_store.enemy_env,
                turn=env.battle_store.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            action = agent.select_action(state_vector, env.battle_store, env.duration_store)
            next_state, reward, done, _ = env.step(action)
            reward = calculate_reward(state, next_state, action, done, env.battle_store, env.duration_store)
            
            state = next_state
            total_reward += reward
            steps += 1
            
            if done:
                break
        
        rewards.append(total_reward)
        steps_list.append(steps)
        
        print(f'Test Episode {episode+1}/{num_episodes}')
        print(f'Total Reward: {total_reward:.2f}')
        print(f'Steps: {steps}')
        print('-' * 50)
    
    avg_reward = np.mean(rewards)
    std_reward = np.std(rewards)
    avg_steps = np.mean(steps_list)
    
    print(f'\nTest Results:')
    print(f'Average Reward: {avg_reward:.2f} ± {std_reward:.2f}')
    print(f'Average Steps: {avg_steps:.2f}')
    
    return avg_reward, std_reward, avg_steps

#%% [markdown]
# 메인 실행 코드
if __name__ == "__main__":
    # 환경 초기화
    env = YakemonEnv()  # 실제 게임 환경
    state_dim = HYPERPARAMS["state_dim"]
    action_dim = HYPERPARAMS["action_dim"]
    
    # DDDQN 에이전트 생성
    ddqn_agent = DDDQNAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        learning_rate=HYPERPARAMS["learning_rate"],
        gamma=HYPERPARAMS["gamma"],
        epsilon_start=HYPERPARAMS["epsilon_start"],
        epsilon_end=HYPERPARAMS["epsilon_end"],
        epsilon_decay=HYPERPARAMS["epsilon_decay"]
    )
    
    # DDDQN 에이전트 학습
    ddqn_rewards, ddqn_losses = train_agent(
        env=env,
        agent=ddqn_agent,
        num_episodes=HYPERPARAMS["num_episodes"],
        agent_name='ddqn'
    )
    
    # 학습 결과 시각화
    plot_training_results(
        rewards_history=ddqn_rewards,
        losses_history=ddqn_losses,
        agent_name='DDDQN'
    )
    
    # 학습된 에이전트 테스트
    test_agent(
        env=env,
        agent=ddqn_agent,
        num_episodes=HYPERPARAMS["test_episodes"]
    )

