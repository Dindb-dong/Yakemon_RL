# move_data.py

import random
from typing import List, Dict
from utils.shuffle_array import shuffle_array

# 예시 MoveInfo 데이터
move_datas = [
    # {'name': '플레어드라이브', 'type': '불', 'power': 120, 'category': '물리'},
    # ...
]

def move_data(move_names: List[str], types: List[str]) -> List[Dict]:
    # 1. moveDatas에서 name 일치하는 MoveInfo 찾기
    selected = [m for name in move_names for m in move_datas if m['name'] == name]

    if len(selected) != len(move_names):
        for m_name in move_names:
            if not any(m['name'] == m_name for m in selected):
                print(f"Warning: moveData - moveNames에 없는 기술: {m_name}")

    # 2. 자속 기술 골라내기 (type 일치 && power ≥ 10)
    preferred = [move for move in selected if move['type'] in types and move.get('power', 0) >= 10]

    # 3. 나머지 기술 (비자속)
    non_preferred = [move for move in selected if move not in preferred]

    chosen = []

    # 4. 자속 기술 하나 강제 포함
    if preferred:
        random_preferred = random.choice(preferred)
        chosen.append(random_preferred)

    # 5. 남은 기술 중에서 나머지 선택
    remaining_pool = shuffle_array([m for m in selected if m not in chosen])

    for move in remaining_pool:
        is_status = move.get('category') == '변화'
        status_count = sum(1 for m in chosen if m.get('category') == '변화')

        if is_status and status_count >= 3:
            continue  # 변화기술은 최대 3개

        if len(chosen) >= 4:
            break

        chosen.append(move)

    return shuffle_array(chosen)