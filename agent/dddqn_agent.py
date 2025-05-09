# agent/dddqn_agent.py
import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import namedtuple
import torch.nn.functional as F

from utils.replay_buffer import ReplayBuffer

# 경험 리플레이를 위한 데이터 구조
Experience = namedtuple('Experience', ['state', 'action', 'reward', 'next_state', 'done'])

class DuelingDQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DuelingDQN, self).__init__()
        
        # 공통 특성 추출기
        self.feature_layer = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU()
        )
        
        # Value 스트림
        self.value_stream = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
        # Advantage 스트림
        self.advantage_stream = nn.Sequential(
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
    def __init__(self, state_dim, action_dim, learning_rate=0.001, gamma=0.99, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        
        # 메인 네트워크와 타겟 네트워크
        self.policy_net = DuelingDQN(state_dim, action_dim).to(self.device)
        self.target_net = DuelingDQN(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        
        # 옵티마이저
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        
        # 경험 리플레이 버퍼
        self.memory = ReplayBuffer(10000)
        self.batch_size = 64
        
        # 타겟 네트워크 업데이트 관련
        self.steps = 0
        self.update_frequency = 10
    
    def select_action(self, state, store=None, duration_store=None):
        """ε-greedy 정책에 따라 행동을 선택합니다."""
        if random.random() < self.epsilon:
            return random.randrange(self.action_dim)
        
        with torch.no_grad():
            state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state)
            return q_values.argmax().item()
    
    def store_transition(self, state, action, reward, next_state, done):
        """경험을 리플레이 버퍼에 저장합니다."""
        experience = Experience(state, action, reward, next_state, done)
        self.memory.push(experience)
    
    def update_target_network(self):
        """타겟 네트워크를 메인 네트워크의 가중치로 업데이트합니다."""
        self.target_net.load_state_dict(self.policy_net.state_dict())
    
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
            next_actions = self.policy_net(next_state_batch).max(1)[1].unsqueeze(1)
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
        return loss