#%% [markdown]
# Yakemon 강화학습 에이전트 학습
# Rainbow DQN 알고리즘을 사용한 학습 스크립트

#%% [markdown]
# 필요한 라이브러리 임포트
import asyncio
import nest_asyncio
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
import random
import torch
import logging

# 환경 관련 import
from env.battle_env import YakemonEnv

# 유틸리티 관련 import
from utils.battle_logics.create_battle_pokemon import create_battle_pokemon
from utils.visualization import plot_training_results

# RL 관련 import
from RL.reward_calculator import calculate_reward
from RL.get_state_vector import get_state

# 데이터 관련 import
from p_data.move_data import move_data
from p_data.ability_data import ability_data
from p_data.mock_pokemon import create_mock_pokemon_list

# 컨텍스트 관련 import
from context.battle_store import store
from context.duration_store import duration_store

# agent 관련 import
from agent.rainbow_agent import DQNAgent

# 전역 변수 초기화
battle_store = store
duration_store = duration_store

# 하이퍼파라미터 설정
HYPERPARAMS = {
    "memory_size": 100000,
    "batch_size": 64,
    "target_update": 10,
    "gamma": 0.99,
    "alpha": 0.4,
    "beta": 0.4,
    "prior_eps": 1e-6,
    "v_min": -10.0,
    "v_max": 10.0,
    "atom_size": 51,
    "n_step": 3,
    "num_episodes": 50000,
    "save_interval": 100,
    "test_episodes": 100,
    "state_dim": 1165,  # get_state_vector의 출력 차원
    "action_dim": 6,   # 4개의 기술 + 2개의 교체
    "learning_rate": 0.0003,  # 학습률 추가
}

#%% [markdown]
# 학습 함수 정의
async def train_agent(
    env: YakemonEnv,
    agent: DQNAgent,
    num_episodes: int,
    save_path: str = 'models',
    agent_name: str = 'rainbow'
) -> tuple:
    """
    Rainbow DQN 에이전트 학습 함수
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
        # 1. 팀 생성 단계
        all_pokemon = create_mock_pokemon_list()
        
        # 불, 물, 풀 타입의 포켓몬들을 각각 분류
        fire_pokemon = [p for p in all_pokemon if '불' in p.types]
        water_pokemon = [p for p in all_pokemon if '물' in p.types]
        grass_pokemon = [p for p in all_pokemon if '풀' in p.types]
        
        # 각 타입에서 랜덤하게 3마리씩 선택
        my_team = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        
        # 상대 팀도 동일하게 구성
        enemy_team = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        
        # PokemonInfo를 BattlePokemon으로 변환
        my_team = [create_battle_pokemon(poke) for poke in my_team]
        enemy_team = [create_battle_pokemon(poke) for poke in enemy_team]
        
        # 팀 정보 출력 (딕셔너리 형식)
        print(f"[Episode {episode+1}] My Team (BattlePokemon):")
        for p in my_team:
            print(vars(p))
        print(f"[Episode {episode+1}] My Team (PokemonInfo):")
        for p in my_team:
            print(vars(p.base))
        print(f"[Episode {episode+1}] Enemy Team (BattlePokemon):")
        for p in enemy_team:
            print(vars(p))
        print(f"[Episode {episode+1}] Enemy Team (PokemonInfo):")
        for p in enemy_team:
            print(vars(p.base))
        
        # 2. 배틀 환경 초기화
        state = env.reset(my_team=my_team, enemy_team=enemy_team)
        my_team = env.my_team
        enemy_team = env.enemy_team
        store = env.battle_store
        store.set_active_my(0)
        store.set_active_enemy(0)
        total_reward = 0
        total_loss = 0
        steps = 0
        
        # 3. 배틀 루프
        while True:
            # 현재 상태 벡터 생성
            state_vector = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 행동 선택
            action = agent.select_action(state_vector)
            
            # 행동 실행
            next_state, reward, done, _ = await env.step(action)
            
            # 다음 상태 벡터 생성
            next_state_vector = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 경험 저장 및 학습
            await agent.step(action)
            if len(agent.memory) > agent.batch_size:
                loss = agent.update_model()
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
            torch.save(agent.dqn.state_dict(), os.path.join(save_path, f'{agent_name}_best.pth'))
        
        # 주기적으로 모델 저장
        if (episode + 1) % HYPERPARAMS["save_interval"] == 0:
            torch.save(agent.dqn.state_dict(), os.path.join(save_path, f'{agent_name}_episode_{episode+1}.pth'))
        
        # 학습 진행 상황 출력
        print(f'Episode {episode+1}/{num_episodes}')
        print(f'Average Reward: {avg_reward:.2f}')
        print(f'Average Loss: {avg_loss:.4f}')
        print(f'Steps: {steps}')
        print('-' * 50)
    
    return rewards_history, losses_history

#%% [markdown]
# 테스트 함수 정의
async def test_agent(
    env: YakemonEnv,
    agent: DQNAgent,
    num_episodes: int = 10
) -> tuple:
    """
    학습된 에이전트 테스트
    """
    rewards = []
    steps_list = []
    victories = 0
    
    for episode in range(num_episodes):
        # 1. 팀 생성 단계
        all_pokemon = create_mock_pokemon_list()
        
        # 불, 물, 풀 타입의 포켓몬들을 각각 분류
        fire_pokemon = [p for p in all_pokemon if '불' in p.types]
        water_pokemon = [p for p in all_pokemon if '물' in p.types]
        grass_pokemon = [p for p in all_pokemon if '풀' in p.types]
        
        # 각 타입에서 랜덤하게 3마리씩 선택
        my_team = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        
        # 상대 팀도 동일하게 구성
        enemy_team = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        
        # PokemonInfo를 BattlePokemon으로 변환
        my_team = [create_battle_pokemon(poke) for poke in my_team]
        enemy_team = [create_battle_pokemon(poke) for poke in enemy_team]
        
        # 2. 배틀 환경 초기화
        state = env.reset(my_team=my_team, enemy_team=enemy_team)
        my_team = env.my_team
        enemy_team = env.enemy_team
        
        total_reward = 0
        steps = 0
        
        # 3. 배틀 루프
        while True:
            # 현재 상태 벡터 생성
            state_vector = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 행동 선택
            action = agent.select_action(state_vector)
            
            # 행동 실행
            next_state, reward, done, _ = await env.step(action)
            
            # 다음 상태 벡터 생성
            next_state_vector = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 보상 계산
            reward = calculate_reward(
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects,
                action=action,
                done=done,
                battle_store=env.battle_store,
                duration_store=env.duration_store
            )
            
            state_vector = next_state_vector
            total_reward += reward
            steps += 1
            
            if done:
                # 승리 여부 확인
                my_team_alive = any(pokemon.current_hp > 0 for pokemon in my_team)
                enemy_team_alive = any(pokemon.current_hp > 0 for pokemon in enemy_team)
                if my_team_alive and not enemy_team_alive:
                    victories += 1
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
    win_rate = (victories / num_episodes) * 100
    
    print(f'\nTest Results:')
    print(f'Average Reward: {avg_reward:.2f} ± {std_reward:.2f}')
    print(f'Average Steps: {avg_steps:.2f}')
    print(f'Victories: {victories}/{num_episodes} (Win Rate: {win_rate:.1f}%)')
    
    return avg_reward, std_reward, avg_steps, victories, win_rate

#%% [markdown]
# 메인 실행 코드
if __name__ == "__main__":
    # Jupyter에서 중첩된 이벤트 루프 허용
    nest_asyncio.apply()
    
    # 결과 저장 디렉토리 설정
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join('results', f'training_{timestamp}')
    models_dir = os.path.join('models', f'training_{timestamp}')
    
    # 환경 초기화
    env = YakemonEnv()
    
    # Rainbow DQN 에이전트 생성
    rainbow_agent = DQNAgent(
        env=env,
        memory_size=HYPERPARAMS["memory_size"],
        batch_size=HYPERPARAMS["batch_size"],
        target_update=HYPERPARAMS["target_update"],
        seed=42,
        gamma=HYPERPARAMS["gamma"],
        alpha=HYPERPARAMS["alpha"],
        beta=HYPERPARAMS["beta"],
        prior_eps=HYPERPARAMS["prior_eps"],
        v_min=HYPERPARAMS["v_min"],
        v_max=HYPERPARAMS["v_max"],
        atom_size=HYPERPARAMS["atom_size"],
        n_step=HYPERPARAMS["n_step"],
        learning_rate=HYPERPARAMS["learning_rate"]
    )
    
    print("Starting Rainbow DQN training...")
    print(f"Results will be saved in: {results_dir}")
    print(f"Models will be saved in: {models_dir}")
    print("\nHyperparameters:")
    for key, value in HYPERPARAMS.items():
        print(f"  {key}: {value}")
    print("\n" + "="*50 + "\n")
    
    # Rainbow DQN 에이전트 학습
    rainbow_rewards, rainbow_losses = asyncio.run(train_agent(
        env=env,
        agent=rainbow_agent,
        num_episodes=HYPERPARAMS["num_episodes"],
        save_path=models_dir,
        agent_name='rainbow'
    ))
    
    # 학습 결과 시각화
    plot_training_results(
        rewards_history=rainbow_rewards,
        losses_history=rainbow_losses,
        agent_name='Rainbow DQN',
        save_path=results_dir
    )
    
    print("\nTraining completed!")
    print(f"Results saved in: {results_dir}")
    print(f"Models saved in: {models_dir}")
    
    # 학습된 에이전트 테스트
    print("\nStarting test phase...")
    test_results = asyncio.run(test_agent(
        env=env,
        agent=rainbow_agent,
        num_episodes=HYPERPARAMS["test_episodes"]
    ))
    
    # 테스트 결과 저장
    test_stats = {
        'avg_reward': test_results[0],
        'std_reward': test_results[1],
        'avg_steps': test_results[2],
        'victories': test_results[3],
        'win_rate': test_results[4]
    }
    
    with open(os.path.join(results_dir, 'test_results.json'), 'w') as f:
        json.dump(test_stats, f, indent=4)
    
    with open(os.path.join(results_dir, 'test_results.txt'), 'w') as f:
        f.write("Test Results\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Average Reward: {test_stats['avg_reward']:.4f} ± {test_stats['std_reward']:.4f}\n")
        f.write(f"Average Steps: {test_stats['avg_steps']:.2f}\n")
        f.write(f"Victories: {test_stats['victories']}/{HYPERPARAMS['test_episodes']} (Win Rate: {test_stats['win_rate']:.1f}%)\n")
    
    print("\nTest completed!")
    print(f"Test results saved in: {results_dir}")

