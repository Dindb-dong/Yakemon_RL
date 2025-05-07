import os
import numpy as np
from datetime import datetime
from .agent import DQNAgent
from .replay_buffer import ReplayBuffer
from .selfplay_manager import SelfPlayManager
from .model_evaluator import ModelEvaluator
from .training_logger import TrainingLogger

def train_with_improved_selfplay(env_creator, 
                               total_episodes=10000,
                               batch_size=32,
                               target_update_freq=1000,
                               eval_freq=100,
                               save_freq=1000,
                               selfplay_start_episode=1000,
                               selfplay_win_rate_threshold=60.0,
                               selfplay_eval_episodes=100,
                               initial_epsilon=1.0,
                               final_epsilon=0.01,
                               epsilon_decay=0.995,
                               gamma=0.99,
                               learning_rate=0.001,
                               memory_size=100000,
                               dueling=True,
                               double=True,
                               prioritized=True):
    """
    개선된 자가 대전을 통한 DQN 에이전트 훈련
    
    Args:
        env_creator: 환경 생성 함수
        total_episodes: 총 훈련 에피소드 수
        batch_size: 배치 크기
        target_update_freq: 타겟 네트워크 업데이트 주기
        eval_freq: 평가 주기
        save_freq: 모델 저장 주기
        selfplay_start_episode: 자가 대전 시작 에피소드
        selfplay_win_rate_threshold: 자가 대전 상대방 업데이트 임계값
        selfplay_eval_episodes: 자가 대전 평가 에피소드 수
        initial_epsilon: 초기 탐색률
        final_epsilon: 최종 탐색률
        epsilon_decay: 탐색률 감소율
        gamma: 할인율
        learning_rate: 학습률
        memory_size: 리플레이 버퍼 크기
        dueling: Dueling DQN 사용 여부
        double: Double DQN 사용 여부
        prioritized: Prioritized Experience Replay 사용 여부
    """
    # 실험 ID 생성
    experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 에이전트 초기화
    agent = DQNAgent(
        state_size=env_creator().observation_space.shape[0],
        action_size=env_creator().action_space.n,
        learning_rate=learning_rate,
        gamma=gamma,
        epsilon=initial_epsilon,
        epsilon_min=final_epsilon,
        epsilon_decay=epsilon_decay,
        memory_size=memory_size,
        batch_size=batch_size,
        dueling=dueling,
        double=double,
        prioritized=prioritized
    )
    
    # 자가 대전 관리자 초기화
    selfplay_manager = SelfPlayManager(
        win_rate_threshold=selfplay_win_rate_threshold,
        eval_episodes=selfplay_eval_episodes
    )
    
    # 모델 평가기 초기화
    evaluator = ModelEvaluator()
    
    # 훈련 로거 초기화
    logger = TrainingLogger()
    
    # 훈련 루프
    total_steps = 0
    best_win_rate = 0.0
    
    for episode in range(total_episodes):
        # 환경 초기화
        env = env_creator()
        state = env.reset()
        done = False
        episode_reward = 0
        episode_steps = 0
        
        while not done:
            # 행동 선택 및 실행
            valid_actions = env.get_valid_actions()
            action = agent.choose_action(state, valid_actions)
            next_state, reward, done, info = env.step(action)
            
            # 경험 저장
            agent.remember(state, action, reward, next_state, done, valid_actions)
            
            # 배치 학습
            if len(agent.memory) > batch_size:
                loss = agent.replay(batch_size)
                logger.log_episode(episode, total_steps, reward, loss=loss, epsilon=agent.epsilon)
            else:
                logger.log_episode(episode, total_steps, reward, epsilon=agent.epsilon)
            
            # 상태 업데이트
            state = next_state
            episode_reward += reward
            episode_steps += 1
            total_steps += 1
            
            # 타겟 네트워크 업데이트
            if total_steps % target_update_freq == 0:
                agent.update_target_model()
        
        # 자가 대전 시작
        if episode >= selfplay_start_episode and not selfplay_manager.is_active:
            selfplay_manager.start_selfplay(agent)
            print(f"\n자가 대전 시작: 에피소드 {episode}")
        
        # 자가 대전 평가
        if selfplay_manager.is_active and episode % eval_freq == 0:
            selfplay_info = selfplay_manager.evaluate_selfplay(agent, env_creator)
            
            # 상대방 업데이트 여부 확인
            if selfplay_manager.should_update_opponent():
                selfplay_manager.update_opponent(agent)
                print(f"\n자가 대전 상대방 업데이트: 에피소드 {episode}")
        
        # 모델 평가
        if episode % eval_freq == 0:
            is_best, win_rate, avg_reward, avg_turns = evaluator.evaluate(
                agent, env_creator, total_steps, episode,
                selfplay_info=selfplay_manager.get_selfplay_info() if selfplay_manager.is_active else None
            )
            
            # 최고 성능 모델 저장
            if is_best:
                best_win_rate = win_rate
                logger.save_checkpoint(agent, episode, total_steps, is_best=True)
        
        # 주기적 모델 저장
        if episode % save_freq == 0:
            logger.save_checkpoint(agent, episode, total_steps)
        
        # 진행 상황 출력
        if episode % 10 == 0:
            stats = logger.get_statistics()
            logger.print_progress(episode, total_steps, stats)
    
    return agent, evaluator, logger

def continue_training_from_best_model(env_creator,
                                    model_path,
                                    total_episodes=10000,
                                    batch_size=32,
                                    target_update_freq=1000,
                                    eval_freq=100,
                                    save_freq=1000,
                                    selfplay_start_episode=0,
                                    selfplay_win_rate_threshold=60.0,
                                    selfplay_eval_episodes=100,
                                    initial_epsilon=0.1,
                                    final_epsilon=0.01,
                                    epsilon_decay=0.995,
                                    gamma=0.99,
                                    learning_rate=0.001,
                                    memory_size=100000,
                                    dueling=True,
                                    double=True,
                                    prioritized=True):
    """
    최고 성능 모델에서 훈련 계속하기
    
    Args:
        env_creator: 환경 생성 함수
        model_path: 최고 성능 모델 경로
        total_episodes: 추가 훈련 에피소드 수
        batch_size: 배치 크기
        target_update_freq: 타겟 네트워크 업데이트 주기
        eval_freq: 평가 주기
        save_freq: 모델 저장 주기
        selfplay_start_episode: 자가 대전 시작 에피소드
        selfplay_win_rate_threshold: 자가 대전 상대방 업데이트 임계값
        selfplay_eval_episodes: 자가 대전 평가 에피소드 수
        initial_epsilon: 초기 탐색률
        final_epsilon: 최종 탐색률
        epsilon_decay: 탐색률 감소율
        gamma: 할인율
        learning_rate: 학습률
        memory_size: 리플레이 버퍼 크기
        dueling: Dueling DQN 사용 여부
        double: Double DQN 사용 여부
        prioritized: Prioritized Experience Replay 사용 여부
    """
    # 에이전트 초기화
    agent = DQNAgent(
        state_size=env_creator().observation_space.shape[0],
        action_size=env_creator().action_space.n,
        learning_rate=learning_rate,
        gamma=gamma,
        epsilon=initial_epsilon,
        epsilon_min=final_epsilon,
        epsilon_decay=epsilon_decay,
        memory_size=memory_size,
        batch_size=batch_size,
        dueling=dueling,
        double=double,
        prioritized=prioritized
    )
    
    # 최고 성능 모델 로드
    agent.load_model(model_path)
    print(f"\n최고 성능 모델 로드: {model_path}")
    
    # 자가 대전 관리자 초기화
    selfplay_manager = SelfPlayManager(
        win_rate_threshold=selfplay_win_rate_threshold,
        eval_episodes=selfplay_eval_episodes
    )
    
    # 모델 평가기 초기화
    evaluator = ModelEvaluator()
    
    # 훈련 로거 초기화
    logger = TrainingLogger()
    
    # 훈련 루프
    total_steps = 0
    best_win_rate = 0.0
    
    for episode in range(total_episodes):
        # 환경 초기화
        env = env_creator()
        state = env.reset()
        done = False
        episode_reward = 0
        episode_steps = 0
        
        while not done:
            # 행동 선택 및 실행
            valid_actions = env.get_valid_actions()
            action = agent.choose_action(state, valid_actions)
            next_state, reward, done, info = env.step(action)
            
            # 경험 저장
            agent.remember(state, action, reward, next_state, done, valid_actions)
            
            # 배치 학습
            if len(agent.memory) > batch_size:
                loss = agent.replay(batch_size)
                logger.log_episode(episode, total_steps, reward, loss=loss, epsilon=agent.epsilon)
            else:
                logger.log_episode(episode, total_steps, reward, epsilon=agent.epsilon)
            
            # 상태 업데이트
            state = next_state
            episode_reward += reward
            episode_steps += 1
            total_steps += 1
            
            # 타겟 네트워크 업데이트
            if total_steps % target_update_freq == 0:
                agent.update_target_model()
        
        # 자가 대전 시작
        if episode >= selfplay_start_episode and not selfplay_manager.is_active:
            selfplay_manager.start_selfplay(agent)
            print(f"\n자가 대전 시작: 에피소드 {episode}")
        
        # 자가 대전 평가
        if selfplay_manager.is_active and episode % eval_freq == 0:
            selfplay_info = selfplay_manager.evaluate_selfplay(agent, env_creator)
            
            # 상대방 업데이트 여부 확인
            if selfplay_manager.should_update_opponent():
                selfplay_manager.update_opponent(agent)
                print(f"\n자가 대전 상대방 업데이트: 에피소드 {episode}")
        
        # 모델 평가
        if episode % eval_freq == 0:
            is_best, win_rate, avg_reward, avg_turns = evaluator.evaluate(
                agent, env_creator, total_steps, episode,
                selfplay_info=selfplay_manager.get_selfplay_info() if selfplay_manager.is_active else None
            )
            
            # 최고 성능 모델 저장
            if is_best:
                best_win_rate = win_rate
                logger.save_checkpoint(agent, episode, total_steps, is_best=True)
        
        # 주기적 모델 저장
        if episode % save_freq == 0:
            logger.save_checkpoint(agent, episode, total_steps)
        
        # 진행 상황 출력
        if episode % 10 == 0:
            stats = logger.get_statistics()
            logger.print_progress(episode, total_steps, stats)
    
    return agent, evaluator, logger 