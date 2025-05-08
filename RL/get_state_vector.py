from typing import List, Dict

def get_type_index(type_name: str) -> int:
    """타입 이름을 인덱스로 변환하는 함수"""
    type_to_index = {
        "노말": 1, "불": 2, "물": 3, "풀": 4, "전기": 5, "얼음": 6,
        "격투": 7, "독": 8, "땅": 9, "비행": 10, "에스퍼": 11, "벌레": 12,
        "바위": 13, "고스트": 14, "드래곤": 15, "악": 16, "강철": 17, "페어리": 18
    }
    return type_to_index.get(type_name, 0)

def get_position_index(position: str) -> int:
    """포지션을 인덱스로 변환하는 함수"""
    position_to_index = {
        "땅": 1, "하늘": 2, "바다": 3, "공허": 4, "없음": 5
    }
    return position_to_index.get(position, 0)


def get_state(
    my_team: List[Dict],
    enemy_team: List[Dict],
    active_my: int,
    active_enemy: int,
    public_env: Dict,
    my_env: Dict,
    enemy_env: Dict,
    turn: int,
    my_effects: List[Dict],
    enemy_effects: List[Dict],
    for_opponent: bool = False # 왼쪽 플레이어가 쓸 때에는 False, 오른쪽 플레이어가 쓸 때에는 True
) -> List[float]:
    """상태 벡터를 생성하는 함수"""
    state: List[float] = []
    player_team = my_team if not for_opponent else enemy_team
    opponent_team = enemy_team if not for_opponent else my_team
    player = my_team[active_my] if not for_opponent else enemy_team[active_enemy]
    opponent = enemy_team[active_enemy] if not for_opponent else my_team[active_my]

    # 1. 내 포켓몬의 HP 비율 (1차원)
    state.append(player['currentHp'] / player['base']['hp'])
    # 누적 차원: 1

    # 2. 타입 (2차원)
    type1 = get_type_index(player['base']['types'][0]) if player['base']['types'] else 0
    state.append(type1 / 18.0)  # 정규화
    type2 = get_type_index(player['base']['types'][1]) if len(player['base']['types']) > 1 else 0
    state.append(type2 / 18.0)  # 정규화
    # 누적 차원: 3

    # 3. 종족값 (hp 제외) - 5개
    state.append(player['base']['attack'] / 255)
    state.append(player['base']['defense'] / 255)
    state.append(player['base']['spAttack'] / 255)
    state.append(player['base']['spDefense'] / 255)
    state.append(player['base']['speed'] / 255)
    # 누적 차원: 8

    # 4. 상태이상 (14개)
    status_list = [
        '독', '맹독', '마비', '화상', '잠듦', '얼음', '혼란', 
        '풀죽음', '사슬묶기', '소리기술사용불가', '하품', 
        '교체불가', '조이기', '없음'
    ]
    for status in status_list:
        state.append(1.0 if status in player['status'] else 0.0)
    # 누적 차원: 22

    # 5. 랭크 변화 (7개, -6 ~ +6 정규화)
    ranks = ['attack', 'defense', 'spAttack', 'spDefense', 'speed', 'accuracy', 'dodge']
    for stat in ranks:
        rank = player['rank'].get(stat, 0)
        state.append((rank + 6) / 12)
    # 누적 차원: 29

    # 6. 기술 PP 비율 (최대 4개 기술)
    for i in range(4):
        if i < len(player['base']['moves']):
            move = player['base']['moves'][i]
            pp = player['pp'].get(move['name'], 0)
            state.append(pp / move['pp'])
        else:
            state.append(0.0)
    # 누적 차원: 33

    # 7. 추가 상태 정보 (내 포켓몬)
    # 7-1. 포지션 (1차원)
    position_idx = get_position_index(player.get('position', '없음'))
    state.append(position_idx / 5.0)  # 정규화
    # 누적 차원: 34

    # 7-2. 기타 상태 (12개의 이진값 + 4개의 연속값)
    state.append(1.0 if player.get('is_active', False) else 0.0)
    # locked_move 관련 정보
    locked_move_id = player.get('locked_move', {}).get('id', 0)
    state.append(locked_move_id / 1000.0)  # 정규화
    state.append(player.get('locked_move_turn', 0) / 5.0)  # 정규화
    state.append(1.0 if player.get('is_protecting', False) else 0.0)
    # used_move 정보
    used_move_id = player.get('used_move', {}).get('id', 0)
    state.append(used_move_id / 1000.0)  # 정규화
    state.append(1.0 if player.get('had_missed', False) else 0.0)
    state.append(1.0 if player.get('had_rank_up', False) else 0.0)
    state.append(1.0 if player.get('is_charging', False) else 0.0)
    # charging_move 정보
    charging_move_id = player.get('charging_move', {}).get('id', 0)
    state.append(charging_move_id / 1000.0)  # 정규화
    damage_ratio = player.get('received_damage', 0) / player['base']['hp'] if player.get('received_damage') is not None else 0
    state.append(damage_ratio)
    state.append(1.0 if player.get('is_first_turn', False) else 0.0)
    state.append(1.0 if player.get('cannot_move', False) else 0.0)
    # unusable_move 정보
    unusable_move_id = player.get('un_usable_move', {}).get('id', 0)
    state.append(unusable_move_id / 1000.0)  # 정규화
    # 누적 차원: 50 (이전: 34 + 16 = 50)

    # 7-3. 임시 타입 (2차원)
    temp_type1 = 0
    temp_type2 = 0
    if player.get('temp_type'):
        temp_type1 = get_type_index(player['temp_type'][0]) if player['temp_type'] else 0
        temp_type2 = get_type_index(player['temp_type'][1]) if len(player['temp_type']) > 1 else 0
    state.append(temp_type1 / 18.0)  # 정규화
    state.append(temp_type2 / 18.0)  # 정규화
    # 누적 차원: 50

    # 8. 상대 포켓몬 정보
    # 8-1. HP와 타입 (3차원)
    state.append(opponent['currentHp'] / opponent['base']['hp'])
    type1 = get_type_index(opponent['base']['types'][0]) if opponent['base']['types'] else 0
    state.append(type1 / 18.0)  # 정규화
    type2 = get_type_index(opponent['base']['types'][1]) if len(opponent['base']['types']) > 1 else 0
    state.append(type2 / 18.0)  # 정규화
    # 누적 차원: 53

    # 8-2. 종족값 (5차원)
    state.append(opponent['base']['attack'] / 255)
    state.append(opponent['base']['defense'] / 255)
    state.append(opponent['base']['spAttack'] / 255)
    state.append(opponent['base']['spDefense'] / 255)
    state.append(opponent['base']['speed'] / 255)
    # 누적 차원: 58

    # 8-3. 상태이상 (14차원)
    for status in status_list:
        state.append(1.0 if status in opponent['status'] else 0.0)
    # 누적 차원: 72

    # 8-4. 랭크 (7차원)
    for stat in ranks:
        rank = opponent['rank'].get(stat, 0)
        state.append((rank + 6) / 12)
    # 누적 차원: 79

    # 9. 상대 포켓몬 추가 상태 정보
    # 9-1. 포지션 (1차원)
    position_idx = get_position_index(opponent.get('position', '없음'))
    state.append(position_idx / 5.0)  # 정규화
    # 누적 차원: 80

    # 9-2. 기타 상태 (12개의 이진값 + 4개의 연속값)
    state.append(1.0 if opponent.get('is_active', False) else 0.0)
    # locked_move 관련 정보
    locked_move_id = opponent.get('locked_move', {}).get('id', 0)
    state.append(locked_move_id / 1000.0)  # 정규화
    state.append(opponent.get('locked_move_turn', 0) / 5.0)  # 정규화
    state.append(1.0 if opponent.get('is_protecting', False) else 0.0)
    # used_move 정보
    used_move_id = opponent.get('used_move', {}).get('id', 0)
    state.append(used_move_id / 1000.0)  # 정규화
    state.append(1.0 if opponent.get('had_missed', False) else 0.0)
    state.append(1.0 if opponent.get('had_rank_up', False) else 0.0)
    state.append(1.0 if opponent.get('is_charging', False) else 0.0)
    # charging_move 정보
    charging_move_id = opponent.get('charging_move', {}).get('id', 0)
    state.append(charging_move_id / 1000.0)  # 정규화
    damage_ratio = opponent.get('received_damage', 0) / opponent['base']['hp'] if opponent.get('received_damage') is not None else 0
    state.append(damage_ratio)
    state.append(1.0 if opponent.get('is_first_turn', False) else 0.0)
    state.append(1.0 if opponent.get('cannot_move', False) else 0.0)
    # unusable_move 정보
    unusable_move_id = opponent.get('un_usable_move', {}).get('id', 0)
    state.append(unusable_move_id / 1000.0)  # 정규화
    # 누적 차원: 96 (이전: 80 + 16 = 96)

    # 9-3. 임시 타입 (2차원)
    temp_type1 = 0
    temp_type2 = 0
    if opponent.get('temp_type'):
        temp_type1 = get_type_index(opponent['temp_type'][0]) if opponent['temp_type'] else 0
        temp_type2 = get_type_index(opponent['temp_type'][1]) if len(opponent['temp_type']) > 1 else 0
    state.append(temp_type1 / 18.0)  # 정규화
    state.append(temp_type2 / 18.0)  # 정규화
    # 누적 차원: 96

    # 10. 팀 구성 정보 (HP 비율 + 상태이상 여부, 3마리 기준) (12차원)
    for team in [player_team, opponent_team]:
        for i in range(3):
            if i < len(team):
                poke = team[i]
                state.append(poke['currentHp'] / poke['base']['hp'])
                state.append(1.0 if len(poke['status']) > 0 else 0.0)
            else:
                state.append(0.0)
                state.append(0.0)
    # 누적 차원: 108

    # 11. 턴 수 (1차원)
    state.append(min(1.0, turn / 30))
    # 누적 차원: 109

    # 12. 공용 환경 정보 (11차원)
    # 12-1. 날씨 (4차원)
    weathers = ['쾌청', '비', '모래바람', '싸라기눈']
    for weather in weathers:
        state.append(1.0 if public_env['weather'] == weather else 0.0)
    # 누적 차원: 113

    # 12-2. 필드 (4차원)
    fields = ['그래스필드', '사이코필드', '미스트필드', '일렉트릭필드']
    for field in fields:
        state.append(1.0 if public_env['field'] == field else 0.0)
    # 누적 차원: 117

    # 12-3. 룸 (3차원)
    rooms = ['트릭룸', '매직룸', '원더룸']
    for room in rooms:
        state.append(1.0 if public_env['room'] == room else 0.0)
    # 누적 차원: 120

    # 13. 개인 환경 정보
    # 13-1. 내 환경 (7차원)
    # 함정 (7차원)
    traps = ['독압정', '맹독압정', '스텔스록', '압정뿌리기1', '압정뿌리기2', '압정뿌리기3']
    for trap in traps:
        state.append(1.0 if trap in my_env.get('trap', []) else 0.0)
    # 누적 차원: 127

    # 13-2. 상대 환경 (7차원)
    # 함정 (7차원)
    for trap in traps:
        state.append(1.0 if trap in enemy_env.get('trap', []) else 0.0)
    # 누적 차원: 134

    # 14. Duration Store 효과들

    # 14-1. 내 효과 (3차원)
    screens = ['빛의장막', '리플렉터', '오로라베일']
    for screen in screens:
        screen_effect = next((e for e in my_effects if e['name'] == screen), None)
        state.append(screen_effect['remainingTurn'] / 5 if screen_effect else 0.0)
    # 누적 차원: 137

    # 14-2. 상대 효과 (3차원)
    for screen in screens:
        screen_effect = next((e for e in enemy_effects if e['name'] == screen), None)
        state.append(screen_effect['remainingTurn'] / 5 if screen_effect else 0.0)
    # 누적 차원: 140

    print("✅ 상태 벡터 길이:", len(state))
    return state 