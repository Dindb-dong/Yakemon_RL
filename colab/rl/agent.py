import os
import numpy as np
import random
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
from .replay_buffer import ReplayBuffer

# 모델 저장 경로
MODEL_PATH = './pokemon_dqn_models'
os.makedirs(MODEL_PATH, exist_ok=True)

# 최고 성능 모델 저장 경로
BEST_MODEL_PATH = './pokemon_best_models'
os.makedirs(BEST_MODEL_PATH, exist_ok=True)

class DuelingDQN(nn.Module):
    """Dueling DQN 네트워크"""
    def __init__(self, state_size, action_size, use_dueling=True):
        super(DuelingDQN, self).__init__()
        self.use_dueling = use_dueling

        # 특징 추출 레이어
        self.features = nn.Sequential(
            nn.Linear(state_size, 512),
            nn.ReLU(),
            nn.BatchNorm1d(512),
            nn.Dropout(0.2),
            
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.2),
            
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128)
        )

        if use_dueling:
            # 상태 가치 스트림
            self.value_stream = nn.Sequential(
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, 1)
            )
            
            # 행동 이점 스트림
            self.advantage_stream = nn.Sequential(
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, action_size)
            )
        else:
            # 표준 DQN
            self.output = nn.Sequential(
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, action_size)
            )

    def forward(self, x):
        features = self.features(x)
        
        if self.use_dueling:
            values = self.value_stream(features)
            advantages = self.advantage_stream(features)
            # Q = V + (A - mean(A))
            qvals = values + (advantages - advantages.mean(dim=1, keepdim=True))
        else:
            qvals = self.output(features)
            
        return qvals

class DQNAgent:
    """향상된 DQN 에이전트 (Dueling DQN + Double DQN + Prioritized Experience Replay)"""

    def __init__(self, state_size, action_size, **kwargs):
        self.state_size = state_size
        self.action_size = action_size
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 하이퍼파라미터
        self.gamma = kwargs.get('gamma', 0.99)  # 할인 계수
        self.epsilon = kwargs.get('epsilon', 1.0)  # 탐색률
        self.epsilon_min = kwargs.get('epsilon_min', 0.05)  # 최소 탐색률
        self.epsilon_decay = kwargs.get('epsilon_decay', 0.9999)  # 탐색률 감소율
        self.learning_rate = kwargs.get('learning_rate', 0.0003)  # 학습률
        self.batch_size = kwargs.get('batch_size', 128)  # 배치 크기
        self.update_target_freq = kwargs.get('update_target_freq', 1000)  # 타겟 네트워크 업데이트 주기
        self.use_dueling = kwargs.get('use_dueling', True)  # Dueling DQN 사용 여부
        self.grad_clip_norm = kwargs.get('grad_clip_norm', 10.0)  # 그래디언트 클리핑 값

        # 네트워크 생성
        self.online_network = DuelingDQN(state_size, action_size, self.use_dueling).to(self.device)
        self.target_network = DuelingDQN(state_size, action_size, self.use_dueling).to(self.device)
        self.target_network.load_state_dict(self.online_network.state_dict())

        # 옵티마이저 설정
        self.optimizer = optim.Adam(self.online_network.parameters(), lr=self.learning_rate)

        # 경험 재생 버퍼
        buffer_size = kwargs.get('buffer_size', 200000)
        self.replay_buffer = ReplayBuffer(max_size=buffer_size)

        # 학습 변수
        self.train_step = 0
        self.loss_history = []
        self.reward_history = []
        self.episode_count = 0
        self.win_count = 0

        # 최근 에피소드 기록 (이동 평균용)
        self.recent_win_history = deque(maxlen=100)  # 100 에피소드로 증가

        # 자가 대전 버전 정보
        self.version = 0

    def update_target_network(self):
        """타겟 네트워크 업데이트"""
        self.target_network.load_state_dict(self.online_network.state_dict())

    def choose_action(self, state, valid_actions):
        """행동 선택 (epsilon-greedy)"""
        self.online_network.eval() # Set to evaluation mode for inference
        # 유효한 행동이 없으면 기본 행동 반환
        if not valid_actions:
            return 0

        # 유효한 행동 필터링 (인덱스 범위 확인)
        valid_actions = [a for a in valid_actions if a < self.action_size]

        if not valid_actions:
            return 0

        # epsilon 확률로 무작위 행동 선택 (탐색)
        if np.random.rand() < self.epsilon:
            return random.choice(valid_actions)

        # 아니면 최대 Q값을 가진 행동 선택 (활용)
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.online_network(state_tensor).cpu().numpy()[0]

        # 유효하지 않은 행동은 큰 음수 값으로 마스킹
        masked_q_values = q_values.copy()
        for a in range(self.action_size):
            if a not in valid_actions:
                masked_q_values[a] = -float('inf')

        # 최대 Q값을 가진 행동 선택
        return np.argmax(masked_q_values)

    def remember(self, state, action, reward, next_state, done):
        """경험 저장"""
        self.replay_buffer.add(state, action, reward, next_state, done)

    def train_batch(self):
        """배치 학습 - Double DQN + Prioritized Experience Replay"""
        if len(self.replay_buffer) < self.batch_size:
            return None

        self.online_network.train() # Set to training mode

        # 배치 샘플링
        states, actions, rewards, next_states, dones, indices = self.replay_buffer.sample(self.batch_size)

        # torch 텐서로 변환
        states = torch.FloatTensor(np.array(states)).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        rewards = torch.FloatTensor(np.array(rewards)).to(self.device)
        dones = torch.FloatTensor(np.array(dones)).to(self.device)
        actions = torch.LongTensor(np.array(actions)).to(self.device)

        # Double DQN
        with torch.no_grad():
            # Double DQN: 온라인 네트워크로 행동 선택, 타겟 네트워크로 평가
            next_q_values = self.online_network(next_states)
            best_actions = torch.argmax(next_q_values, dim=1)
            
            # 선택된 행동에 대한 타겟 네트워크의 Q값 획득
            target_q_values = self.target_network(next_states)
            target_values = target_q_values.gather(1, best_actions.unsqueeze(1)).squeeze()
            
            # Q 타겟 계산
            targets = rewards + self.gamma * target_values * (1 - dones)

        # 현재 Q 값 계산
        q_values = self.online_network(states)
        current_q_values = q_values.gather(1, actions.unsqueeze(1)).squeeze()

        # 손실 계산 및 역전파
        loss = nn.MSELoss()(current_q_values, targets)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_network.parameters(), self.grad_clip_norm)
        self.optimizer.step()

        # TD 오차 계산 및 우선순위 업데이트
        td_errors = abs(targets - current_q_values.detach()).cpu().numpy()
        self.replay_buffer.update_priorities(indices, td_errors)

        # 손실 기록
        loss_value = loss.item()
        self.loss_history.append(loss_value)

        # 단계 카운터 증가 및 탐색률 감소
        self.train_step += 1
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        # 주기적으로 타겟 네트워크 업데이트
        if self.train_step % self.update_target_freq == 0:
            self.update_target_network()

        return loss_value

    def add_win(self):
        """승리 기록"""
        self.episode_count += 1
        self.win_count += 1
        self.recent_win_history.append(1)  # 1: 승

    def add_loss(self):
        """패배 기록"""
        self.episode_count += 1
        self.recent_win_history.append(0)  # 0: 패

    def get_win_rate(self):
        """현재 승률 계산"""
        if self.episode_count == 0:
            return 0.0
        return self.win_count / self.episode_count * 100.0

    def get_recent_win_rate(self):
        """최근 100 게임의 승률 계산"""
        if not self.recent_win_history:
            return 0.0
        return sum(self.recent_win_history) / len(self.recent_win_history) * 100.0

    def increment_version(self):
        """버전 증가"""
        self.version += 1
        return self.version

    def save_model(self, filename, is_best=False):
        """모델 저장"""
        # 저장 경로 결정 (최고 모델 여부에 따라)
        save_path = BEST_MODEL_PATH if is_best else MODEL_PATH

        torch.save({
            'online_state_dict': self.online_network.state_dict(),
            'target_state_dict': self.target_network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'train_step': self.train_step,
            'episode_count': self.episode_count,
            'win_count': self.win_count,
            'version': self.version,
            'loss_history': self.loss_history,
            'reward_history': self.reward_history
        }, os.path.join(save_path, f"{filename}.pt"))

        status = "최고 성능" if is_best else "일반"
        print(f"{status} 모델 저장 완료: {os.path.join(save_path, filename)}")

    def load_model(self, filename, model_dir='./'):
        """모델 로드"""
        try:
            checkpoint = torch.load(os.path.join(model_dir, f"{filename}.pt"))
            
            self.online_network.load_state_dict(checkpoint['online_state_dict'])
            self.target_network.load_state_dict(checkpoint['target_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            
            self.epsilon = checkpoint['epsilon']
            self.train_step = checkpoint['train_step']
            self.episode_count = checkpoint['episode_count']
            self.win_count = checkpoint['win_count']
            self.version = checkpoint['version']
            self.loss_history = checkpoint['loss_history']
            self.reward_history = checkpoint['reward_history']

            print(f"모델 로드 성공: {filename}")
            return True
        except Exception as e:
            print(f"모델 로드 실패: {filename}, 오류: {e}")

            # 디렉토리 내용 확인
            try:
                print("\n디렉토리 파일 목록:")
                files = os.listdir(model_dir)
                for file in files:
                    if filename in file:
                        print(f"  - {file}")
            except Exception as dir_err:
                print(f"디렉토리 확인 실패: {dir_err}")

            return False

    def clone(self):
        """에이전트 복제 (가중치만 복사)"""
        clone_agent = DQNAgent(
            state_size=self.state_size,
            action_size=self.action_size,
            gamma=self.gamma,
            epsilon=0.1,  # 상대방의 epsilon을 0.1로 고정
            epsilon_min=self.epsilon_min,
            epsilon_decay=self.epsilon_decay,
            learning_rate=self.learning_rate,
            batch_size=self.batch_size
        )
        clone_agent.online_network.load_state_dict(self.online_network.state_dict())
        clone_agent.target_network.load_state_dict(self.target_network.state_dict())
        clone_agent.version = self.version  # 버전 정보 복사
        return clone_agent