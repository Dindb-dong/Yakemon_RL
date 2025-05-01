# rank_status.py

from typing import Dict, Literal

# 타입 정의
RankStat = Literal['attack', 'spAttack', 'defense', 'spDefense', 'speed', 'accuracy', 'dodge', 'critical']

# RankState = 공격/방어/스피드/명중률/회피율/급소율 등을 관리하는 dict
RankState = Dict[RankStat, int]

class RankManager:
    def __init__(self, initial_state: RankState):
        self.state: RankState = self.clamp_state(initial_state.copy())

    def get_state(self) -> RankState:
        return self.state

    def reset_state(self) -> RankState:
        reset = {
            'attack': 0,
            'spAttack': 0,
            'defense': 0,
            'spDefense': 0,
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
            print(f"{which_state}이/가 {rank}만큼 올랐다!")
            self.state = self.clamp_state(self.state)

    def decrease_state(self, which_state: RankStat, rank: int) -> None:
        if which_state in self.state:
            self.state[which_state] = self.state.get(which_state, 0) - rank
            print(f"{which_state}이/가 {rank}만큼 내려갔다!")
            self.state = self.clamp_state(self.state)

    def clamp_state(self, state: RankState) -> RankState:
        def clamp(value: int, limit: int = 6) -> int:
            return max(-limit, min(limit, value))

        return {
            'attack': clamp(state.get('attack', 0)),
            'spAttack': clamp(state.get('spAttack', 0)),
            'defense': clamp(state.get('defense', 0)),
            'spDefense': clamp(state.get('spDefense', 0)),
            'speed': clamp(state.get('speed', 0)),
            'accuracy': clamp(state.get('accuracy', 0)),
            'dodge': clamp(state.get('dodge', 0)),
            'critical': max(0, min(4, state.get('critical', 0))),  # 급소율만 0~4로 따로 관리
        }