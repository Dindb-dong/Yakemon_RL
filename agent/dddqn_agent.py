# agent/dddqn_agent.py
import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import namedtuple
import torch.nn.functional as F
import numpy as np

from context.battle_store import BattleStore
from utils.replay_buffer import ReplayBuffer

# 경험 리플레이를 위한 데이터 구조
Experience = namedtuple('Experience', ['state', 'action', 'reward', 'next_state', 'done'])

class DuelingDQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DuelingDQN, self).__init__()
        
        # 공통 특성 추출기
        self.feature_layer = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU()
        )
        
        # Value 스트림
        self.value_stream = nn.Sequential(
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
        # Advantage 스트림
        self.advantage_stream = nn.Sequential(
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim)
        )
    
    def forward(self, state):
        features = self.feature_layer(state)
        values = self.value_stream(features)
        advantages = self.advantage_stream(features)
        
        # Dueling DQN의 Q-value 계산
        qvals = values + (advantages - advantages.mean(dim=1, keepdim=True))
        return qvals

class DDDQNAgent:
    """
    Dueling Double DQN 에이전트
    
    주요 하이퍼파라미터:
    - learning_rate: 학습률 (기본값: 0.0005)
    - gamma: 할인 계수 (기본값: 0.95)
    - epsilon_start: 초기 탐험률 (기본값: 1.0)
    - epsilon_end: 최소 탐험률 (기본값: 0.01)
    - epsilon_decay: 탐험률 감소율 (기본값: 0.997)
    - target_update: 타겟 네트워크 업데이트 주기 (기본값: 20)
        - 매 20번의 학습 스텝마다 타겟 네트워크를 정책 네트워크의 가중치로 하드 업데이트
        - 이는 학습의 안정성을 높이고 Q값의 과대 추정을 방지하는 역할
    - memory_size: 리플레이 버퍼 크기 (기본값: 50000)
    - batch_size: 배치 크기 (기본값: 128)
    """
    def __init__(self, state_dim, action_dim, learning_rate, gamma, epsilon_start, epsilon_end, epsilon_decay, target_update, memory_size, batch_size):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.update_frequency = target_update  # 타겟 네트워크 업데이트 주기 (학습 스텝 단위)
        
        # 메인 네트워크와 타겟 네트워크
        self.policy_net = DuelingDQN(state_dim, action_dim).to(self.device)
        self.target_net = DuelingDQN(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        
        # 옵티마이저
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        
        # 경험 리플레이 버퍼
        self.memory = ReplayBuffer(memory_size)
        self.batch_size = batch_size
        
        # 타겟 네트워크 업데이트 관련
        self.steps = 0  # 총 학습 스텝 수
        self.updates = 0  # 실제로 수행된 네트워크 업데이트 수
    
    def select_action(self, state, store: BattleStore=None, duration_store=None, use_target=False):
        """ε-greedy 정책에 따라 행동을 선택합니다."""
        if store is not None:
            current_index = store.get_active_index("my")
            my_team = store.get_team("my")
            current_pokemon = my_team[current_index]
            
            # cannot_move 상태 체크
            if current_pokemon.cannot_move:
                print("dddqn_agent: cannot_move 상태")
                return -1
                
            # is_charging 상태 체크
            if current_pokemon.is_charging:
                print("dddqn_agent: is_charging 상태")
                for i, move in enumerate(current_pokemon.base.moves):
                    if current_pokemon.charging_move is not None and move.name == current_pokemon.charging_move:
                        return i
                        
            # locked_move 상태 체크
            if current_pokemon.locked_move:
                print("dddqn_agent: locked_move 상태")
                for i, move in enumerate(current_pokemon.base.moves):
                    if current_pokemon.locked_move is not None and move.name == current_pokemon.locked_move:
                        return i
        
        if random.random() < self.epsilon:  # epsilon 체크
            # 마스크를 고려한 랜덤 행동 선택
            action_mask = self._get_action_mask(store)
            valid_actions = [i for i, mask in enumerate(action_mask) if mask == 1]
            if valid_actions:
                return random.choice(valid_actions)
            else:
                print("dddqn_agent: 가능한 행동이 없는 상태")
                return -1
        
        with torch.no_grad():
            state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            # use_target이 True면 target network를 사용
            network = self.target_net if use_target else self.policy_net
            q_values = network(state)
            
            # 마스크 적용
            action_mask = self._get_action_mask(store)
            masked_q_values = q_values.clone()
            masked_q_values[0, action_mask == 0] = float(-100)
            
            return masked_q_values.argmax().item()
    
    def _get_action_mask(self, store):
        """현재 상태에서 가능한 행동들의 마스크를 반환합니다."""
        mask = np.ones(self.action_dim, dtype=np.int32)
        
        if store is None:
            return mask
            
        current_index = store.get_active_index("my")
        my_team = store.get_team("my")
        current_pokemon = my_team[current_index]
        
        # 기술 사용(0-3)에 대한 마스킹
        for i in range(4):
            if current_pokemon.pp.get(current_pokemon.base.moves[i].name, 0) <= 0:
                mask[i] = 0
        
        # 교체 행동(4-5)에 대한 마스킹
        for i in range(2):  # 교체 행동 2개
            switch_index = i
            # 자기 자신으로 교체하는 경우
            if switch_index == current_index:
                #print("dddqn_agent: 자기 자신으로 교체할 수 없습니다.")
                mask[4 + i] = 0
            # 교체하려는 포켓몬이 쓰러진 경우
            elif my_team[switch_index].current_hp <= 0:
                #print("dddqn_agent: 쓰러진 포켓몬으로 교체할 수 없습니다.")
                mask[4 + i] = 0
        
        return mask
    
    def store_transition(self, state, action, reward, next_state, done):
        """경험을 리플레이 버퍼에 저장합니다."""
        experience = Experience(state, action, reward, next_state, done)
        self.memory.push(experience)
    
    def update_target_network(self):
        """타겟 네트워크를 메인 네트워크의 가중치로 업데이트합니다."""
        # 업데이트 전 타겟 네트워크의 첫 번째 레이어 가중치
        before_update = self.target_net.feature_layer[0].weight.data.clone()
        
        # 타겟 네트워크 업데이트
        self.target_net.load_state_dict(self.policy_net.state_dict())
        
        # 업데이트 후 타겟 네트워크의 첫 번째 레이어 가중치
        after_update = self.target_net.feature_layer[0].weight.data.clone()
        
        # 가중치 변화 확인
        weight_diff = torch.abs(before_update - after_update).mean().item()
        print(f"Target network updated at step {self.steps} (update #{self.updates}). Mean weight difference: {weight_diff:.6f}")
    
    def update_epsilon(self):
        """탐험률을 감소시킵니다."""
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
    
    def train(self):
        """
        네트워크를 학습합니다.
        리플레이 버퍼에 최소 배치 크기(batch_size) 이상의 샘플이 있을 때만 학습을 수행합니다.
        
        Returns:
            float: 학습 손실값. 학습이 수행되지 않은 경우 0.0을 반환합니다.
        """
        # 최소 배치 크기 이상의 샘플이 있는지 확인
        if len(self.memory) < self.batch_size:
            return 0.0
        
        try:
            # 배치 샘플링
            states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
            
            # 텐서 변환
            state_batch = torch.FloatTensor(states).to(self.device)
            action_batch = torch.LongTensor(actions).to(self.device)
            reward_batch = torch.FloatTensor(rewards).clamp(-5, 5).to(self.device)
            next_state_batch = torch.FloatTensor(next_states).to(self.device)
            done_batch = torch.FloatTensor(dones).to(self.device)
            
            # 디버그 정보 출력
            print(f"\nDebug - Batch Info:")
            print(f"Replay Buffer Size: {len(self.memory)}/{self.memory.max_size}")
            print(f"Invalid Actions (-1): {(action_batch == -1).sum().item()}/{len(action_batch)}")
            print(f"Rewards - Min: {reward_batch.min().item():.2f}, Max: {reward_batch.max().item():.2f}, Mean: {reward_batch.mean().item():.2f}")
            print(f"Dones - True count: {done_batch.sum().item()}")
            
            # 현재 Q 값 계산
            current_q_values = self.policy_net(state_batch)
            
            # -1 액션을 6으로 매핑 (행동불능 상태는 마지막 액션으로 처리)
            mapped_actions = action_batch.clone()
            mapped_actions[action_batch == -1] = 6
            
            # 선택된 액션의 Q값만 추출
            current_q_values = current_q_values.gather(1, mapped_actions.unsqueeze(1))
            
            # 다음 상태의 최대 Q 값 계산 (Double DQN)
            with torch.no_grad():
                # 다음 상태의 Q 값 계산 (policy net으로 action 선택)
                next_q_values = self.policy_net(next_state_batch)
                next_actions = next_q_values.max(1)[1].unsqueeze(1)
                
                # target net으로 value 계산
                next_target_q_values = self.target_net(next_state_batch)
                next_q_values = next_target_q_values.gather(1, next_actions)
                
                # Q 값 클리핑
                next_q_values = next_q_values.clamp(-10, 10)
                
                # expected Q 값 계산
                expected_q_values = reward_batch.unsqueeze(1) + (1 - done_batch.unsqueeze(1)) * self.gamma * next_q_values
                expected_q_values = expected_q_values.clamp(-10, 10)
            
            # Q값 디버그 정보
            print(f"Debug - Q-values:")
            print(f"Current Q - Min: {current_q_values.min().item():.2f}, Max: {current_q_values.max().item():.2f}, Mean: {current_q_values.mean().item():.2f}")
            print(f"Next Q - Min: {next_q_values.min().item():.2f}, Max: {next_q_values.max().item():.2f}, Mean: {next_q_values.mean().item():.2f}")
            print(f"Expected Q - Min: {expected_q_values.min().item():.2f}, Max: {expected_q_values.max().item():.2f}, Mean: {expected_q_values.mean().item():.2f}")
            
            # 손실 계산 (Huber Loss 사용)
            loss = F.smooth_l1_loss(current_q_values, expected_q_values)
            
            # 손실값 디버그
            print(f"Debug - Loss: {loss.item():.4f}")
            
            # 최적화
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
            self.optimizer.step()
            
            # 학습 스텝 카운트 증가
            self.steps += 1
            self.updates += 1
            
            # 타겟 네트워크 업데이트
            if self.updates % self.update_frequency == 0:
                print(f"\nUpdating target network at step {self.steps} (update #{self.updates})")
                self.update_target_network()
            
            # 메모리 정리
            del state_batch, action_batch, reward_batch, next_state_batch, done_batch
            del current_q_values, next_q_values, expected_q_values
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            
            return loss.item()
            
        except Exception as e:
            print(f"Error during training: {str(e)}")
            return 0.0

    def update(self):
        """
        네트워크를 학습하고 탐험률을 업데이트합니다.
        리플레이 버퍼에 충분한 샘플이 있을 때만 학습을 수행합니다.
        
        Returns:
            float: 학습 손실값. 학습이 수행되지 않은 경우 0.0을 반환합니다.
        """
        # 학습 수행
        loss = self.train()
        
        # 탐험률 업데이트
        self.update_epsilon()
        
        return loss

    def save(self, path):
        """모델의 상태를 저장합니다."""
        torch.save({
            'policy_net_state_dict': self.policy_net.state_dict(),
            'target_net_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'steps': self.steps
        }, path)
        print(f"Model saved to {path}")

    def load(self, path):
        """저장된 모델의 상태를 불러옵니다."""
        checkpoint = torch.load(path)
        self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
        self.steps = checkpoint['steps']
        print(f"Model loaded from {path}")