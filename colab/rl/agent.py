import os
import numpy as np
import random
import tensorflow as tf
import keras
from keras import backend as K
from collections import deque
from .replay_buffer import ReplayBuffer

# 모델 저장 경로
MODEL_PATH = './pokemon_dqn_models'
os.makedirs(MODEL_PATH, exist_ok=True)

# 최고 성능 모델 저장 경로
BEST_MODEL_PATH = './pokemon_best_models'
os.makedirs(BEST_MODEL_PATH, exist_ok=True)

def subtract_mean(x):
    """명시적으로 정의된 평균 차감 함수"""
    return x - K.mean(x, axis=1, keepdims=True)

# 커스텀 객체 등록
keras.utils.get_custom_objects().update({'subtract_mean': subtract_mean})

class DQNAgent:
    """향상된 DQN 에이전트 (Dueling DQN + Double DQN + Prioritized Experience Replay)"""

    def __init__(self, state_size, action_size, **kwargs):
        self.state_size = state_size
        self.action_size = action_size

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
        self.online_network = self._build_network()
        self.target_network = self._build_network()

        # 타겟 네트워크 초기화
        self.update_target_network()

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

        # 그래디언트 클리핑이 있는 커스텀 옵티마이저
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=self.learning_rate, clipnorm=self.grad_clip_norm)

    def _build_network(self):
        inputs = tf.keras.layers.Input(shape=(self.state_size,))

        # 특징 추출 레이어
        features = tf.keras.layers.Dense(512, activation='relu')(inputs)
        features = tf.keras.layers.BatchNormalization()(features)
        features = tf.keras.layers.Dropout(0.2)(features)

        features = tf.keras.layers.Dense(256, activation='relu')(features)
        features = tf.keras.layers.BatchNormalization()(features)
        features = tf.keras.layers.Dropout(0.2)(features)

        features = tf.keras.layers.Dense(128, activation='relu')(features)
        features = tf.keras.layers.BatchNormalization()(features)

        if self.use_dueling:
            # Dueling DQN: 상태 가치 (V) + 행동 이점 (A)
            state_value = tf.keras.layers.Dense(64, activation='relu')(features)
            state_value = tf.keras.layers.Dense(1)(state_value)

            action_advantages = tf.keras.layers.Dense(64, activation='relu')(features)
            action_advantages = tf.keras.layers.Dense(self.action_size)(action_advantages)

            # 명시적 함수 참조
            action_advantages_mean = tf.keras.layers.Lambda(
                subtract_mean  # 직접 함수 참조
            )(action_advantages)

            # Q = V + A
            outputs = tf.keras.layers.Add()([state_value, action_advantages_mean])
        else:
            # 표준 DQN
            outputs = tf.keras.layers.Dense(64, activation='relu')(features)
            outputs = tf.keras.layers.Dense(self.action_size, activation='linear')(outputs)

        model = tf.keras.Model(inputs=inputs, outputs=outputs)
        return model

    def update_target_network(self):
        """타겟 네트워크 업데이트"""
        self.target_network.set_weights(self.online_network.get_weights())

    def choose_action(self, state, valid_actions):
        """행동 선택 (epsilon-greedy)"""
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
        state_tensor = np.expand_dims(state, axis=0)
        q_values = self.online_network.predict(state_tensor, verbose=0)[0]

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

    @tf.function
    def _train_step(self, states, actions, targets):
        """TensorFlow 그래프로 최적화된 학습 단계"""
        actions_one_hot = tf.one_hot(actions, self.action_size)

        with tf.GradientTape() as tape:
            q_values = self.online_network(states, training=True)
            q_values_for_actions = tf.reduce_sum(q_values * actions_one_hot, axis=1)
            td_errors = targets - q_values_for_actions
            loss = tf.reduce_mean(tf.square(td_errors))

        gradients = tape.gradient(loss, self.online_network.trainable_variables)
        self.optimizer.apply_gradients(zip(gradients, self.online_network.trainable_variables))

        return loss, td_errors

    def train_batch(self):
        """배치 학습 - Double DQN + Prioritized Experience Replay"""
        if len(self.replay_buffer) < self.batch_size:
            return None

        # 배치 샘플링
        states, actions, rewards, next_states, dones, indices = self.replay_buffer.sample(self.batch_size)

        # numpy 배열로 변환
        states = np.array(states, dtype=np.float32)
        next_states = np.array(next_states, dtype=np.float32)
        rewards = np.array(rewards, dtype=np.float32)
        dones = np.array(dones, dtype=np.float32)
        actions = np.array(actions, dtype=np.int32)

        # Double DQN: 온라인 네트워크로 행동 선택, 타겟 네트워크로 평가
        next_q_values = self.online_network.predict(next_states, verbose=0)
        best_actions = np.argmax(next_q_values, axis=1)

        # 선택된 행동에 대한 타겟 네트워크의 Q값 획득
        target_q_values = self.target_network.predict(next_states, verbose=0)
        target_values = np.array([target_q_values[i, action] for i, action in enumerate(best_actions)])

        # Q 타겟 계산
        targets = rewards + self.gamma * target_values * (1 - dones)

        # 그래프 모드에서 학습
        loss_value, td_errors = self._train_step(states, actions, targets)

        # 우선순위 업데이트
        self.replay_buffer.update_priorities(indices, td_errors.numpy())

        # 손실 기록
        loss = float(loss_value)
        self.loss_history.append(loss)

        # 단계 카운터 증가 및 탐색률 감소
        self.train_step += 1
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        # 주기적으로 타겟 네트워크 업데이트
        if self.train_step % self.update_target_freq == 0:
            self.update_target_network()

        return loss

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

        self.online_network.save(os.path.join(save_path, f"{filename}_online.keras"))
        self.target_network.save(os.path.join(save_path, f"{filename}_target.keras"))

        # 메트릭 및 파라미터 저장
        np.save(os.path.join(save_path, f"{filename}_loss_history.npy"), np.array(self.loss_history))
        np.save(os.path.join(save_path, f"{filename}_reward_history.npy"), np.array(self.reward_history))

        params = {
            'epsilon': self.epsilon,
            'train_step': self.train_step,
            'episode_count': self.episode_count,
            'win_count': self.win_count,
            'version': self.version
        }
        np.save(os.path.join(save_path, f"{filename}_params.npy"), params)

        status = "최고 성능" if is_best else "일반"
        print(f"{status} 모델 저장 완료: {os.path.join(save_path, filename)}")

    def load_model(self, filename, model_dir='./'):
        """모델 로드 - 온라인 모델만 있는 경우도 처리"""
        try:
            # 온라인 모델 경로
            online_path = os.path.join(model_dir, f"{filename}_online.keras")

            # 온라인 모델 로드
            print(f"온라인 모델 로드 시도: {online_path}")
            self.online_network = tf.keras.models.load_model(online_path)

            # 타겟 모델 경로
            target_path = os.path.join(model_dir, f"{filename}_target.keras")

            # 타겟 모델이 있으면 로드, 없으면 온라인 모델 복사
            if os.path.exists(target_path):
                print(f"타겟 모델 로드: {target_path}")
                self.target_network = tf.keras.models.load_model(target_path)
            else:
                print(f"타겟 모델 없음, 온라인 모델 복사")
                # 온라인 모델의 가중치를 타겟 모델에 복사
                self.target_network = tf.keras.models.clone_model(self.online_network)
                self.target_network.set_weights(self.online_network.get_weights())

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
        # 가중치 복사
        clone_agent.online_network.set_weights(self.online_network.get_weights())
        clone_agent.target_network.set_weights(self.target_network.get_weights())
        clone_agent.version = self.version  # 버전 정보 복사
        return clone_agent 