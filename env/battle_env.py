# env/battle_env.py
# 이거 엉망 코드임! 완전히 새로 짜야함
import random
import numpy as np
from p_data.mock_pokemon import create_mock_pokemon_list
from utils.state_encoder import encode_battle_state

class YakemonEnv:
    def __init__(self):
        self.pokemon_list = create_mock_pokemon_list()
        self.reset()

    def reset(self):
        self.my_team = random.sample(self.pokemon_list, 3)
        self.enemy_team = random.sample(self.pokemon_list, 3)
        self.active_my = 0
        self.active_enemy = 0
        self.done = False
        return self.get_state()

    def get_state(self):
        return encode_battle_state(self.my_team, self.enemy_team, self.active_my, self.active_enemy)

    def step(self, action):
        reward = 0
        if action < 4:
            # 기본 공격 4개 중 하나 실행
            reward += random.uniform(-0.5, 1.0)
        else:
            # 교체 (action - 4)
            idx = action - 4
            if idx < len(self.my_team):
                self.active_my = idx
                reward += 0.1

        # 랜덤으로 상대 행동 처리
        if random.random() < 0.5:
            reward -= 0.3  # 상대가 이득보는 경우
        else:
            reward += 0.2

        # 체력 소모 시뮬레이션
        self.my_team[self.active_my]['hp'] -= random.uniform(5, 15)
        self.enemy_team[self.active_enemy]['hp'] -= random.uniform(5, 15)

        # 포켓몬 쓰러짐 처리
        if self.my_team[self.active_my]['hp'] <= 0:
            available = [i for i, p in enumerate(self.my_team) if p['hp'] > 0]
            if available:
                self.active_my = available[0]
            else:
                self.done = True
                reward -= 1.0

        if self.enemy_team[self.active_enemy]['hp'] <= 0:
            available = [i for i, p in enumerate(self.enemy_team) if p['hp'] > 0]
            if available:
                self.active_enemy = available[0]
            else:
                self.done = True
                reward += 1.0

        return self.get_state(), reward, self.done, {}