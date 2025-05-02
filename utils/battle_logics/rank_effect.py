from typing import Optional
from p_models.ability_info import AbilityInfo
import random

def calculate_rank_effect(rank: int) -> float:
    """
    공/방/특공/특방/스피드 랭크 효과 계산
    """
    if rank > 0 and rank <= 6:
        return (rank + 2) / 2
    elif rank > 6:
        return 4.0
    elif rank < -6:
        return 0.25
    else:
        return 2 / (abs(rank) + 2)


def calculate_accuracy(acc_rate: float, move_accuracy: float, acc_rank: int, dodge_rank: int) -> bool:
    """
    명중 여부 계산
    """
    hit_prob = acc_rate

    rank_diff = acc_rank - dodge_rank

    if rank_diff > 6:
        hit_prob *= 3
    elif 0 <= rank_diff <= 6:
        hit_prob *= (rank_diff + 3) / 3
    elif -6 <= rank_diff < 0:
        hit_prob *= 3 / (abs(rank_diff) + 3)
    else:
        hit_prob *= 1 / 3

    hit_prob *= (move_accuracy / 100)
    hit_prob = min(1.0, hit_prob)

    return random.random() < hit_prob


def calculate_critical(base_critical: int, ability: Optional[AbilityInfo], cri_rank: int) -> bool:
    """
    급소 여부 계산
    """
    cri_prob = 0
    if ability and ability.name == "대운":
        cri_prob += 1

    cri_prob += base_critical
    cri_prob += cri_rank

    if cri_prob == 0:
        cri_rate = 1 / 24
    else:
        cri_rate = (cri_prob ** 2) * 2 / 16

    return random.random() < cri_rate