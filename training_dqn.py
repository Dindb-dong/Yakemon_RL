#%% [markdown]
# Yakemon 강화학습 에이전트 학습
# 각 알고리즘을 독립적으로 테스트하기 위한 스크립트

#%% [markdown]
# 필요한 라이브러리 임포트
import asyncio
from typing import Dict, Union
import nest_asyncio
import os
import numpy as np
from datetime import datetime
import json
import random

# 환경 관련 import
from RL.base_ai_choose_action import base_ai_choose_action
from env.battle_env import YakemonEnv

# 모델 관련 import

# 유틸리티 관련 import
from p_models.battle_pokemon import BattlePokemon
from p_models.move_info import MoveInfo
from utils.battle_logics.create_battle_pokemon import create_battle_pokemon
from utils.visualization import plot_training_results

# 에이전트 관련 import
from agent.dddqn_agent import DDDQNAgent

# RL 관련 import
from RL.get_state_vector import get_state

# 데이터 관련 import
from p_data.mock_pokemon import create_mock_pokemon_list

# 컨텍스트 관련 import
from context.battle_store import BattleStoreState, store
from context.duration_store import duration_store


# 전역 변수 초기화
battle_store = store
duration_store = duration_store

# 하이퍼파라미터 설정
hyperparams = {
    "learning_rate": 0.0005,
    "gamma": 0.95,
    "epsilon_start": 1.0,
    "epsilon_end": 0.01,
    "epsilon_decay": 0.997,
    "batch_size": 128,
    "memory_size": 500000,
    "target_update": 20,
    "num_episodes": 50000,
    "save_interval": 10000,
    "test_episodes": 300,
    "state_dim": 1165,  # get_state_vector의 출력 차원
    "action_dim": 6   # 4개의 기술 + 2개의 교체
}

#%% [markdown]
# 학습 함수 정의
def get_action_int(action: MoveInfo | Dict[str, Union[str, int]] | None, pokemon: BattlePokemon):
    if action is None:
        print("get_action_int: action is None due to cannot_move")
        return 6
    if isinstance(action, dict):
        state: BattleStoreState = store.get_state()
        active_my = state["active_my"]
        if active_my == 0:
            return action['index'] - 1 + 4
        elif active_my == 1:
            if action['index'] == 0:
                return 4
            elif action['index'] == 2:
                return 5
            else:
                raise ValueError(f"Invalid action index: {action['index']}")
        elif active_my == 2:
            return action['index'] + 4
        else:
            raise ValueError(f"Invalid active_my: {active_my}")
    else: 
        for i, move in enumerate(pokemon.base.moves):
            if move.name == action.name:
                return i
        raise ValueError(f"Invalid move name: {action.name}")

async def train_agent(
    env: YakemonEnv,
    agent: DDDQNAgent,
    num_episodes: int,
    save_path: str = 'models',
    agent_name: str = 'ddqn',
    HYPERPARAMS: dict = hyperparams
) -> tuple:
    """
    에이전트 학습 함수
    
    Args:
        env: 학습 환경
        agent: 학습할 에이전트
        num_episodes: 학습할 에피소드 수
        save_path: 모델 저장 경로
        agent_name: 에이전트 이름
    
    Returns:
        tuple: (rewards_history, losses_history, victories_history)
    """
    # models/ 디렉토리에서 모든 .pth 파일 찾기
    best_model_files = [f for f in os.listdir('best_models') if f.endswith('.pth')]
    best_reward = 0
    if best_model_files:
        # 파일 이름에서 평균 리워드 추출 (파일명 형식: "숫자_best.pth")
        reward_model_pairs = []
        for file in best_model_files:
            try:
                reward = float(file.split('_')[0])
                reward_model_pairs.append((reward, file))
            except ValueError:
                continue
        
        if reward_model_pairs:
            # 가장 높은 평균 리워드를 가진 모델 찾기
            best_reward, best_model = max(reward_model_pairs, key=lambda x: x[0])
            if HYPERPARAMS["load_best_model"]:
                load_path = os.path.join('best_models', best_model)
                print(f"Loading model with highest average reward: {best_reward} from {load_path}")
                agent.load(load_path)
        else:
            print("No valid model files found in best_models/ directory")
    else:
        print("No .pth files found in best_models/ directory")
    # 마지막 모델 로드
    if HYPERPARAMS["load_last_model"]:
        # models/ 디렉토리에서 training_* 형식의 폴더들을 찾기
        training_folders = [f for f in os.listdir('models') if f.startswith('training_')]
        if training_folders:
            # 가장 최근의 training 폴더 찾기 (날짜순 정렬)
            latest_training_folder = sorted(training_folders)[-1]
            training_path = os.path.join('models', latest_training_folder)
            
            # 해당 폴더에서 ddqn_episode_*.pth 파일들 찾기
            model_files = [f for f in os.listdir(training_path) if f.startswith('ddqn_episode_') and f.endswith('.pth')]
            if model_files:
                # episode 번호 추출하여 가장 큰 번호의 모델 찾기
                episode_numbers = []
                for file in model_files:
                    try:
                        episode = int(file.split('_')[-1].split('.')[0])  # ddqn_episode_숫자.pth에서 숫자 추출
                        episode_numbers.append((episode, file))
                    except ValueError:
                        continue
                
                if episode_numbers:
                    # 가장 큰 episode 번호를 가진 모델 찾기
                    latest_episode, latest_model = max(episode_numbers, key=lambda x: x[0])
                    load_path = os.path.join(training_path, latest_model)
                    print(f"Loading latest model from episode {latest_episode} at {load_path}")
                    agent.load(load_path)
                else:
                    print(f"No valid model files found in {training_path}")
            else:
                print(f"No model files found in {training_path}")
        else:
            print("No training folders found in models/ directory")
    
    rewards_history = []
    losses_history = []
    victories_history = []
    
    # 모델 저장 디렉토리 생성
    os.makedirs(save_path, exist_ok=True)
    
    # 하이퍼파라미터 저장
    with open(os.path.join(save_path, f'{agent_name}_hyperparams.json'), 'w') as f:
        json.dump(HYPERPARAMS, f, indent=4)
    
    # 전체 에피소드 수를 battle_store에 설정
    env.battle_store.total_episodes = num_episodes
    
    for episode in range(num_episodes):
        # 에피소드 번호를 battle_store에 설정
        env.battle_store.episode = episode
        
        # 1. 팀 생성 단계
        all_pokemon = create_mock_pokemon_list()
        
        # 첫 번째 포켓몬은 완전 랜덤하게 선택
        my_team = [random.choice(all_pokemon)]
        
        # 두 번째 포켓몬은 첫 번째 포켓몬과 타입이 겹치지 않는 포켓몬 중에서 선택
        first_pokemon_types = set(my_team[0].types)
        available_second = [p for p in all_pokemon if not any(t in first_pokemon_types for t in p.types)]
        my_team.append(random.choice(available_second))
        
        # 세 번째 포켓몬은 첫 번째와 두 번째 포켓몬과 타입이 겹치지 않는 포켓몬 중에서 선택
        first_two_types = first_pokemon_types.union(set(my_team[1].types))
        available_third = [p for p in all_pokemon if not any(t in first_two_types for t in p.types)]
        my_team.append(random.choice(available_third))

        # 상대 팀도 동일한 로직으로 구성
        enemy_team = [random.choice(all_pokemon)]
        
        first_pokemon_types = set(enemy_team[0].types)
        available_second = [p for p in all_pokemon if not any(t in first_pokemon_types for t in p.types)]
        enemy_team.append(random.choice(available_second))
        
        first_two_types = first_pokemon_types.union(set(enemy_team[1].types))
        available_third = [p for p in all_pokemon if not any(t in first_two_types for t in p.types)]
        enemy_team.append(random.choice(available_third))
        
        # PokemonInfo를 BattlePokemon으로 변환
        my_team = [create_battle_pokemon(poke) for poke in my_team]
        enemy_team = [create_battle_pokemon(poke) for poke in enemy_team]
        print(f"[Episode {episode+1}]")
        # 팀 정보 출력 (포켓몬 이름 포함)
        print(f"\nMy Team:")
        for i, p in enumerate(my_team):
            print(f"{i+1}. {p.base.name} (HP: {p.current_hp}/{p.base.hp})")
            print(f"   타입: {', '.join(p.base.types)}")
            print(f"   특성: {p.base.ability.name if p.base.ability else '없음'}")
            print(f"   기술: {', '.join(move.name for move in p.base.moves)}")
        print(f"\nEnemy Team:")
        for i, p in enumerate(enemy_team):
            print(f"{i+1}. {p.base.name} (HP: {p.current_hp}/{p.base.hp})")
            print(f"   타입: {', '.join(p.base.types)}")
            print(f"   특성: {p.base.ability.name if p.base.ability else '없음'}")
            print(f"   기술: {', '.join(move.name for move in p.base.moves)}")
        print('-' * 50)
        
        # 2. 배틀 환경 초기화
        state = env.reset(my_team=my_team, enemy_team=enemy_team)
        my_team = env.my_team
        enemy_team = env.enemy_team
        store = env.battle_store
        store.set_active_my(0)
        store.set_active_enemy(0)
        
        # 에피소드 관련 변수 초기화
        total_reward = 0
        total_loss = 0
        steps = 0
        
        # 3. 배틀 루프: 환경 스텝마다 한 번씩 학습 호출
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
            # 초반 학습 중에는 base ai와 DQN을 혼합하여 사용
            if episode < HYPERPARAMS["num_episodes"] / 2:
                print(f"Episode {episode+1} / {HYPERPARAMS['num_episodes']/2}")
                temp_action = base_ai_choose_action(
                    side="my",
                    my_team=my_team,
                    enemy_team=enemy_team,
                    active_my=env.battle_store.get_active_index("my"),
                    active_enemy=env.battle_store.get_active_index("enemy"),
                    public_env=env.public_env.__dict__,
                    enemy_env=env.my_env.__dict__,
                    my_env=env.enemy_env.__dict__,
                    add_log=env.battle_store.add_log
                )
                action = get_action_int(temp_action, my_team[env.battle_store.get_active_index("my")])
            else:
                action = agent.select_action(state_vector, env.battle_store, env.duration_store, use_target=False)
            
            # 행동 실행
            next_state, reward, done, _ = await env.step(action)
            
            # 경험 저장 (리플레이 버퍼에 추가)
            agent.store_transition(state_vector, action, reward, next_state, done)
            
            # ◆ 환경 스텝마다 업데이트 한 번
            loss = agent.update()
            total_loss += loss
            
            # 다음 스텝 준비
            state_vector = next_state
            total_reward += reward
            steps += 1
            
            if done:
                # 승리 여부 확인
                my_team_alive = any(pokemon.current_hp > 0 for pokemon in my_team)
                enemy_team_alive = any(pokemon.current_hp > 0 for pokemon in enemy_team)
                victory = 1 if my_team_alive and not enemy_team_alive else 0
                victories_history.append(victory)
                break
        
        # 에피소드 결과 저장
        avg_reward = total_reward / steps
        avg_loss = total_loss / steps if total_loss > 0 else 0
        rewards_history.append(avg_reward)
        losses_history.append(avg_loss)
        
        # 최고 성능 모델 저장
        if avg_reward > best_reward:
            best_reward = avg_reward
            agent.save(os.path.join('best_models', f'{avg_reward}_best.pth'))
        
        # 주기적으로 모델 저장
        if (episode + 1) % HYPERPARAMS["save_interval"] == 0:
            agent.save(os.path.join(save_path, f'{agent_name}_episode_{episode+1}.pth'))
        
        # 학습 진행 상황 출력
        print(f'Episode {episode+1}/{num_episodes}')
        print(f'Average Reward: {avg_reward:.2f}')
        print(f'Average Loss: {avg_loss:.4f}')
        print(f'Epsilon: {agent.epsilon:.4f}')
        print(f'Steps: {steps}')
        print(f'Alive Enemies: {len(enemy_team) - sum(pokemon.current_hp <= 0 for pokemon in enemy_team)}')
        print(f'Victory: {"Yes" if victory else "No"}')
        print(f'Cumulative Victories: {sum(victories_history)}/{len(victories_history)}')
        print('-' * 50)
    
    return rewards_history, losses_history, victories_history

#%% [markdown]
# 테스트 함수 정의
async def test_agent(
    env: YakemonEnv,
    agent: DDDQNAgent,
    num_episodes: int = 10,
    HYPERPARAMS: dict = hyperparams
) -> tuple:
    """
    학습된 에이전트 테스트
    """
    
    rewards = []
    steps_list = []
    victories = 0  # 승리 횟수 추적
    
    for episode in range(num_episodes):
        # 1. 팀 생성 단계
        all_pokemon = create_mock_pokemon_list()
        
        # 불, 물, 풀 타입의 포켓몬들을 각각 분류
        fire_pokemon = [p for p in all_pokemon if '불' in p.types]
        water_pokemon = [p for p in all_pokemon if '물' in p.types]
        grass_pokemon = [p for p in all_pokemon if '풀' in p.types]
        
        # test 시에는 물 불 풀만 사용
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
        my_team = env.my_team  # BattlePokemon 객체 리스트로 업데이트
        enemy_team = env.enemy_team  # BattlePokemon 객체 리스트로 업데이트
        
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
            
            # 행동 선택 (기술 4개 + 교체 가능한 포켓몬 수)
            # 테스트 시에는 target network를 사용
            action = agent.select_action(state_vector, env.battle_store, env.duration_store, use_target=True)
            
            # 행동 실행
            next_state, reward, done, _ = await env.step(action)
            
            # 다음 스텝 준비
            state_vector = next_state
            total_reward += reward
            steps += 1
            
            # 배틀이 끝났는지 확인
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
from utils.visualization import capture_output
if __name__ == "__main__":
    # Jupyter에서 중첩된 이벤트 루프 허용
    nest_asyncio.apply()
    
    # 결과 저장 디렉토리 설정
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join('results', f'training_{timestamp}')
    models_dir = os.path.join('models', f'training_{timestamp}')
    
    # 환경 초기화
    env = YakemonEnv()  # 실제 게임 환경
    state_dim = hyperparams["state_dim"]
    action_dim = hyperparams["action_dim"]
    
    # DDDQN 에이전트 생성
    ddqn_agent = DDDQNAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        learning_rate=hyperparams["learning_rate"],
        gamma=hyperparams["gamma"],
        epsilon_start=hyperparams["epsilon_start"],
        epsilon_end=hyperparams["epsilon_end"],
        epsilon_decay=hyperparams["epsilon_decay"],
        target_update=hyperparams["target_update"],
        memory_size=hyperparams["memory_size"],
        batch_size=hyperparams["batch_size"]
    )
    
    print("Starting DDDQN training...")
    print(f"Results will be saved in: {results_dir}")
    print(f"Models will be saved in: {models_dir}")
    print("\nHyperparameters:")
    for key, value in hyperparams.items():
        print(f"  {key}: {value}")
    print("\n" + "="*50 + "\n")
    
    # DDDQN 에이전트 학습
    with capture_output() as output:
        ddqn_rewards, ddqn_losses, ddqn_victories = asyncio.run(train_agent(
            env=env,
            agent=ddqn_agent,
            num_episodes=hyperparams["num_episodes"],
            save_path=models_dir,
            agent_name='ddqn'
        ))
    
    # 학습 결과 시각화
    log_lines = output.getvalue().splitlines()
    plot_training_results(
        rewards_history=ddqn_rewards,
        losses_history=ddqn_losses,
        agent_name='DDDQN',
        save_path=results_dir,
        victories_history=ddqn_victories,  # 승리 기록 추가
        log_lines=log_lines
    )
    
    print("\nTraining completed!")
    print(f"Results saved in: {results_dir}")
    print(f"Models saved in: {models_dir}")
    
    # 학습된 에이전트 테스트
    print("\nStarting test phase...")
    test_results = asyncio.run(test_agent(
        env=env,
        agent=ddqn_agent,
        num_episodes=hyperparams["test_episodes"]
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
        f.write(f"Victories: {test_stats['victories']}/{hyperparams['test_episodes']} (Win Rate: {test_stats['win_rate']:.1f}%)\n")
    
    print("\nTest completed!")
    print(f"Test results saved in: {results_dir}")

