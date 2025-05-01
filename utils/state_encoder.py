# utils/state_encoder.py
import numpy as np

def encode_battle_state(my_team, enemy_team, active_my, active_enemy):
    state = []
    for team, active in [(my_team, active_my), (enemy_team, active_enemy)]:
        active_pokemon = team[active]
        state.extend([
            active_pokemon['hp'] / 100,
            active_pokemon['attack'] / 100,
            active_pokemon['defense'] / 100,
            active_pokemon['spAttack'] / 100,
            active_pokemon['spDefense'] / 100,
            active_pokemon['speed'] / 100,
            len(active_pokemon['status']) / 5,  # 상태이상 수
        ])
    return np.array(state, dtype=np.float32)