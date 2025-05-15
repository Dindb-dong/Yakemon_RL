# agent/dddqn_agent.py
import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import namedtuple
import torch.nn.functional as F
import numpy as np

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
    def __init__(self, state_dim, action_dim, learning_rate, gamma, epsilon_start, epsilon_end, epsilon_decay, target_update, memory_size, batch_size):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.update_frequency = target_update
        
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
        self.steps = 0
    
    def select_action(self, state, store=None, duration_store=None):
        """ε-greedy 정책에 따라 행동을 선택합니다."""
        if random.random() < self.epsilon:
            # 마스크를 고려한 랜덤 행동 선택
            action_mask = self._get_action_mask(store)
            valid_actions = [i for i, mask in enumerate(action_mask) if mask == 1]
            if valid_actions:
                return random.choice(valid_actions)
            return random.randrange(self.action_dim)
        
        with torch.no_grad():
            state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state)
            
            # 마스크 적용
            action_mask = self._get_action_mask(store)
            masked_q_values = q_values.clone()
            masked_q_values[0, action_mask == 0] = float('-inf')
            
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
                mask[4 + i] = 0
            # 교체하려는 포켓몬이 쓰러진 경우
            elif my_team[switch_index].current_hp <= 0:
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
        print(f"Target network weights updated. Mean weight difference: {weight_diff:.6f}")
    
    def update_epsilon(self):
        """탐험률을 감소시킵니다."""
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
    
    def train(self):
        """네트워크를 학습합니다."""
        if len(self.memory) < self.batch_size:
            return 0.0
        
        # 배치 샘플링
        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        
        # 텐서 변환
        state_batch = torch.FloatTensor(states).to(self.device)
        action_batch = torch.LongTensor(actions).to(self.device)
        reward_batch = torch.FloatTensor(rewards).to(self.device)
        next_state_batch = torch.FloatTensor(next_states).to(self.device)
        done_batch = torch.FloatTensor(dones).to(self.device)
        
        # 현재 Q 값 계산
        current_q_values = self.policy_net(state_batch).gather(1, action_batch.unsqueeze(1))
        
        # 다음 상태의 최대 Q 값 계산 (Double DQN)
        with torch.no_grad():
            # 다음 상태의 Q 값 계산
            next_q_values = self.policy_net(next_state_batch)
            
            # 마스크 적용 (다음 상태에서 가능한 행동만 고려)
            next_actions = next_q_values.max(1)[1].unsqueeze(1)
            next_q_values = self.target_net(next_state_batch).gather(1, next_actions)
            expected_q_values = reward_batch.unsqueeze(1) + (1 - done_batch.unsqueeze(1)) * self.gamma * next_q_values
        
        # 손실 계산
        loss = F.smooth_l1_loss(current_q_values, expected_q_values)
        
        # 최적화
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        return loss.item()
    
    def update(self):
        """네트워크를 학습하고 탐험률을 업데이트합니다."""
        loss = self.train()
        self.update_epsilon()
        
        # 타겟 네트워크 업데이트
        self.steps += 1
        if self.steps % self.update_frequency == 0:
            self.update_target_network()
            print(f"Target network updated at step {self.steps}")
        
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