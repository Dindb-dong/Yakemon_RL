from collections import deque
import numpy as np

class ReplayBuffer:
    """우선순위 샘플링이 있는 경험 재생 버퍼"""

    def __init__(self, max_size=200000, alpha=0.6):
        self.buffer = deque(maxlen=max_size)
        self.priorities = deque(maxlen=max_size)
        self.alpha = alpha  # 우선순위 인자 (0: 무작위 샘플링, 1: 완전 우선순위)

    def add(self, state, action, reward, next_state, done):
        """경험을 버퍼에 추가"""
        # 새 경험에 최대 우선순위 할당
        max_priority = max(self.priorities) if self.priorities else 1.0

        self.buffer.append((state, action, reward, next_state, done))
        self.priorities.append(max_priority)

    def sample(self, batch_size):
        """우선순위 기반 배치 샘플링"""
        batch_size = min(batch_size, len(self.buffer))

        # 우선순위 계산
        if self.alpha == 0:
            # 표준 무작위 샘플링
            indices = np.random.choice(len(self.buffer), batch_size)
        else:
            # 우선순위 기반 샘플링
            priorities = np.array(self.priorities) ** self.alpha
            probabilities = priorities / sum(priorities)
            indices = np.random.choice(len(self.buffer), batch_size, p=probabilities)

        # 배치 데이터 추출
        states = []
        actions = []
        rewards = []
        next_states = []
        dones = []

        for i in indices:
            state, action, reward, next_state, done = self.buffer[i]
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            next_states.append(next_state)
            dones.append(done)

        return states, actions, rewards, next_states, dones, indices

    def update_priorities(self, indices, errors, eps=1e-5):
        """TD 오류에 기반한 우선순위 업데이트"""
        for i, error in zip(indices, errors):
            self.priorities[i] = abs(error) + eps  # 0 방지를 위한 작은 값 추가

    def __len__(self):
        """버퍼 크기 반환"""
        return len(self.buffer) 