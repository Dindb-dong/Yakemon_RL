# rank_status.py

from typing import Dict, Literal

# 타입 정의
RankStat = Literal['attack', 'sp_attack', 'defense', 'sp_defense', 'speed', 'accuracy', 'dodge', 'critical']

# RankState = 공격/방어/스피드/명중률/회피율/급소율 등을 관리하는 dict
RankState = Dict[RankStat, int]

def clamp_rank(value: int, limit: int = 6) -> int:
    """랭크 값을 제한 범위 내로 조정합니다."""
    return max(-limit, min(limit, value))

class RankManager:
    def __init__(self, initial_state: RankState):
        self.state: RankState = self.clamp_state(initial_state.copy())

    def get_state(self) -> RankState:
        return self.state

    def reset_state(self) -> RankState:
        reset = {
            'attack': 0,
            'sp_attack': 0,
            'defense': 0,
            'sp_defense': 0,
            'speed': 0,
            'accuracy': 0,
            'dodge': 0,
            'critical': 0,
        }
        print("랭크가 리셋됐다!")
        self.state = self.clamp_state(reset)
        return self.state

    def update_state(self, new_state: Dict[RankStat, int]) -> None:
        updated = {**self.state, **new_state}
        self.state = self.clamp_state(updated)

    def increase_state(self, which_state: RankStat, rank: int) -> None:
        if which_state in self.state:
            self.state[which_state] = self.state.get(which_state, 0) + rank
            print(f"RankManager: {which_state}이/가 {rank}만큼 올랐다!")
            self.state = self.clamp_state(self.state)

    def decrease_state(self, which_state: RankStat, rank: int) -> None:
        if which_state in self.state:
            self.state[which_state] = self.state.get(which_state, 0) - rank
            print(f"RankManager: {which_state}이/가 {rank}만큼 내려갔다!")
            self.state = self.clamp_state(self.state)

    def clamp_state(self, state: RankState) -> RankState:
        return {
            'attack': clamp_rank(state.get('attack', 0)),
            'sp_attack': clamp_rank(state.get('sp_attack', 0)),
            'defense': clamp_rank(state.get('defense', 0)),
            'sp_defense': clamp_rank(state.get('sp_defense', 0)),
            'speed': clamp_rank(state.get('speed', 0)),
            'accuracy': clamp_rank(state.get('accuracy', 0)),
            'dodge': clamp_rank(state.get('dodge', 0)),
            'critical': max(0, min(4, state.get('critical', 0))),  # 급소율만 0~4로 따로 관리
        }