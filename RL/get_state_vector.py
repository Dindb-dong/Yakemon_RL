from typing import List, Dict

from context.battle_store import BattleStore
from p_models.battle_pokemon import BattlePokemon

def get_type_index(type_name: str) -> int:
    """타입 이름을 인덱스로 변환하는 함수"""
    type_to_index = {
        "노말": 1, "불": 2, "물": 3, "풀": 4, "전기": 5, "얼음": 6,
        "격투": 7, "독": 8, "땅": 9, "비행": 10, "에스퍼": 11, "벌레": 12,
        "바위": 13, "고스트": 14, "드래곤": 15, "악": 16, "강철": 17, "페어리": 18, "없음": 19
    }
    return type_to_index.get(type_name, 0)

def get_position_index(position: str) -> int:
    """포지션을 인덱스로 변환하는 함수"""
    position_to_index = {
        "땅": 1, "하늘": 2, "바다": 3, "공허": 4, "없음": 5
    }
    return position_to_index.get(position, 0)


def get_state(
    store: BattleStore,
    my_team: List[BattlePokemon],
    enemy_team: List[BattlePokemon],
    active_my: int,
    active_enemy: int,
    public_env: Dict,
    my_env: Dict,
    enemy_env: Dict,
    turn: int,
    my_effects: List[Dict],
    enemy_effects: List[Dict],
    for_opponent: bool = False # 왼쪽 플레이어가 쓸 때에는 False, 오른쪽 플레이어가 쓸 때에는 True
) -> Dict[str, float]:
    """상태 벡터를 딕셔너리로 생성하는 함수"""
    state = {}
    player_team = my_team if not for_opponent else enemy_team
    opponent_team = enemy_team if not for_opponent else my_team
    player: BattlePokemon = my_team[active_my] if not for_opponent else enemy_team[active_enemy]
    opponent: BattlePokemon = enemy_team[active_enemy] if not for_opponent else my_team[active_my]

    # 1. 내 포켓몬의 HP 비율 (1차원)
    state['current_hp'] = player.current_hp / player.base.hp
    # 누적 차원: 1

    # 2. 타입 (2차원)
    type1 = get_type_index(player.base.types[0]) if player.base.types else 0
    type2 = get_type_index(player.base.types[1]) if len(player.base.types) > 1 else 0
    state['type1'] = type1 / 19.0  # 정규화
    state['type2'] = type2 / 19.0  # 정규화
    # 누적 차원: 3

    # 3. 종족값 (hp 제외) - 5개
    state['attack'] = player.base.attack / 255.0
    state['defense'] = player.base.defense / 255.0
    state['sp_attack'] = player.base.sp_attack / 255.0
    state['sp_defense'] = player.base.sp_defense / 255.0
    state['speed'] = player.base.speed / 255.0
    # 누적 차원: 8

    # 4. 상태이상 (14개)
    status_list = [
        '독', '맹독', '마비', '화상', '잠듦', '얼음', '혼란', 
        '풀죽음', '사슬묶기', '소리기술사용불가', '하품', 
        '교체불가', '조이기', '멸망의노래'
    ]
    for status in status_list:
        state[f'status_{status}'] = 1.0 if status in player.status else 0.0
    # 누적 차원: 22

    # 5. 랭크 변화 (7개, -6 ~ +6 정규화)
    ranks = ['attack', 'defense', 'spAttack', 'spDefense', 'speed', 'accuracy', 'dodge']
    for stat in ranks:
        rank = player.rank.get(stat, 0)
        state[f'rank_{stat}'] = (rank + 6) / 12.0
    # 누적 차원: 29

    # 6. 기술 PP 비율 (최대 4개 기술)
    for i in range(4):
        if i < len(player.base.moves):
            move = player.base.moves[i]
            pp = player.pp.get(move.name, 0)
            state[f'move_{i}_pp'] = pp / move.pp
        else:
            state[f'move_{i}_pp'] = 0.0
    # 누적 차원: 33

    # 7. 추가 상태 정보 (내 포켓몬)
    # 7-1. 포지션 (1차원)
    state['position'] = get_position_index(player.position if hasattr(player, 'position') else '없음') / 5.0
    # 누적 차원: 34

    # 7-2. 기타 상태 (13개)
    state['is_active'] = 1.0 if getattr(player, 'is_active', False) else 0.0
    # locked_move 관련 정보
    state['locked_move_id'] = getattr(getattr(player, 'locked_move', None), 'id', 0) / 1000.0
    state['locked_move_turn'] = (getattr(player, 'locked_move_turn', 0) or 0) / 5.0
    state['is_protecting'] = 1.0 if getattr(player, 'is_protecting', False) else 0.0
    # used_move 정보
    state['used_move_id'] = getattr(getattr(player, 'used_move', None), 'id', 0) / 1000.0
    state['had_missed'] = 1.0 if getattr(player, 'had_missed', False) else 0.0
    state['had_rank_up'] = 1.0 if getattr(player, 'had_rank_up', False) else 0.0
    state['is_charging'] = 1.0 if getattr(player, 'is_charging', False) else 0.0
    # charging_move 정보
    state['charging_move_id'] = getattr(getattr(player, 'charging_move', None), 'id', 0) / 1000.0
    state['received_damage_ratio'] = (getattr(player, 'received_damage', 0) or 0) / player.base.hp if hasattr(player, 'received_damage') else 0
    state['is_first_turn'] = 1.0 if getattr(player, 'is_first_turn', False) else 0.0
    state['cannot_move'] = 1.0 if getattr(player, 'cannot_move', False) else 0.0
    # unusable_move 정보
    state['unusable_move_id'] = getattr(getattr(player, 'un_usable_move', None), 'id', 0) / 1000.0
    # 누적 차원: 47

    # 7-3. 임시 타입 (2차원)
    temp_type = getattr(player, 'temp_type', []) or []
    temp_type1 = get_type_index(temp_type[0]) if temp_type else 0
    temp_type2 = get_type_index(temp_type[1]) if len(temp_type) > 1 else 0
    state['temp_type1'] = temp_type1 / 19.0  # 정규화
    state['temp_type2'] = temp_type2 / 19.0  # 정규화
    # 누적 차원: 49

    # 8. 상대 포켓몬 정보
    # 8-1. HP와 타입 (3차원)
    state['enemy_hp'] = opponent.current_hp / opponent.base.hp
    enemy_type1 = get_type_index(opponent.base.types[0]) if opponent.base.types else 0
    enemy_type2 = get_type_index(opponent.base.types[1]) if len(opponent.base.types) > 1 else 0
    state['enemy_type1'] = enemy_type1 / 19.0
    state['enemy_type2'] = enemy_type2 / 19.0
    # 누적 차원: 52

    # 8-2. 종족값 (5차원)
    state['enemy_attack'] = opponent.base.attack / 255
    state['enemy_defense'] = opponent.base.defense / 255
    state['enemy_sp_attack'] = opponent.base.sp_attack / 255
    state['enemy_sp_defense'] = opponent.base.sp_defense / 255
    state['enemy_speed'] = opponent.base.speed / 255
    # 누적 차원: 57

    # 8-3. 상태이상 (14차원)
    for status in status_list:
        state[f'enemy_status_{status}'] = 1.0 if status in opponent.status else 0.0
    # 누적 차원: 71

    # 8-4. 랭크 (7차원)
    for stat in ranks:
        rank = opponent.rank.get(stat, 0)
        state[f'enemy_rank_{stat}'] = (rank + 6) / 12.0
    # 누적 차원: 78

    # 8-5. 상대 포켓몬 추가 상태 정보
    # 8-5-1. 포지션 (1차원)
    state['enemy_position'] = get_position_index(opponent.position if hasattr(opponent, 'position') else '없음') / 5.0
    # 누적 차원: 79

    # 8-5-2. 기타 상태 (13개)
    state['enemy_is_active'] = 1.0 if getattr(opponent, 'is_active', False) else 0.0
    # locked_move 관련 정보
    state['enemy_locked_move_id'] = getattr(getattr(opponent, 'locked_move', None), 'id', 0) / 1000.0
    state['enemy_locked_move_turn'] = (getattr(opponent, 'locked_move_turn', 0) or 0) / 5.0
    state['enemy_is_protecting'] = 1.0 if getattr(opponent, 'is_protecting', False) else 0.0
    # used_move 정보
    state['enemy_used_move_id'] = getattr(getattr(opponent, 'used_move', None), 'id', 0) / 1000.0
    state['enemy_had_missed'] = 1.0 if getattr(opponent, 'had_missed', False) else 0.0
    state['enemy_had_rank_up'] = 1.0 if getattr(opponent, 'had_rank_up', False) else 0.0
    state['enemy_is_charging'] = 1.0 if getattr(opponent, 'is_charging', False) else 0.0
    # charging_move 정보
    state['enemy_charging_move_id'] = getattr(getattr(opponent, 'charging_move', None), 'id', 0) / 1000.0
    state['enemy_received_damage_ratio'] = (getattr(opponent, 'received_damage', 0) or 0) / opponent.base.hp if hasattr(opponent, 'received_damage') else 0
    state['enemy_is_first_turn'] = 1.0 if getattr(opponent, 'is_first_turn', False) else 0.0
    state['enemy_cannot_move'] = 1.0 if getattr(opponent, 'cannot_move', False) else 0.0
    # unusable_move 정보
    state['enemy_unusable_move_id'] = getattr(getattr(opponent, 'un_usable_move', None), 'id', 0) / 1000.0
    # 누적 차원: 92

    # 8-5-3. 임시 타입 (2차원)
    temp_type = getattr(opponent, 'temp_type', []) or []
    temp_type1 = get_type_index(temp_type[0]) if temp_type else 0
    temp_type2 = get_type_index(temp_type[1]) if len(temp_type) > 1 else 0
    state['enemy_temp_type1'] = temp_type1 / 19.0  # 정규화
    state['enemy_temp_type2'] = temp_type2 / 19.0  # 정규화
    # 누적 차원: 94

    # 9. 팀 구성 정보 (HP 비율 + 상태이상 여부, 3마리 기준)
    # 9-1. 내 팀 정보 (6차원, 체력과 상태이상 여부때문에 6차원)
    for i in range(3):  # 3마리
        if i < len(player_team):
            poke = player_team[i]
            state[f'my_team_{i}_hp'] = poke.current_hp / poke.base.hp
            state[f'my_team_{i}_has_status'] = 1.0 if len(poke.status) > 0 else 0.0
        else:
            state[f'my_team_{i}_hp'] = 0.0
            state[f'my_team_{i}_has_status'] = 0.0
    # 누적 차원: 100

    # 9-2. 상대 팀 정보 (6차원, 체력과 상태이상 여부때문에 6차원)
    for i in range(3):  # 3마리
        if i < len(opponent_team):
            poke = opponent_team[i]
            state[f'enemy_team_{i}_hp'] = poke.current_hp / poke.base.hp
            state[f'enemy_team_{i}_has_status'] = 1.0 if len(poke.status) > 0 else 0.0
        else:
            state[f'enemy_team_{i}_hp'] = 0.0
            state[f'enemy_team_{i}_has_status'] = 0.0
    # 누적 차원: 106

    # 10. 턴 수 (1차원)
    state['turn'] = min(1.0, turn / 30)
    # 누적 차원: 107

    # 11. 공용 환경 정보 
    # 11-1. 날씨 (1차원)
    weathers = ['쾌청', '비', '모래바람', '싸라기눈']
    for weather in weathers:
        if public_env['weather'] == weather:
            state['weather'] = weathers.index(weather) / len(weathers)
            break
        else:
            state['weather'] = 0.0
    # 누적 차원: 108

    # 11-2. 필드 (1차원)
    fields = ['그래스필드', '사이코필드', '미스트필드', '일렉트릭필드']
    for field in fields:
        if public_env['field'] == field:
            state['field'] = fields.index(field) / len(fields)
            break
        else:
            state['field'] = 0.0
    # 누적 차원: 109

    # 11-3. 룸 (1차원)
    rooms = ['트릭룸', '매직룸', '원더룸']
    for room in rooms:
        if public_env['room'] == room:
            state['room'] = rooms.index(room) / len(rooms)
            break
        else:
            state['room'] = 0.0
    # 누적 차원: 110

    # 12. 함정 정보 (14차원)
    # 12-1. 내 필드 함정 (7차원)
    traps = ['독압정', '맹독압정', '스텔스록', '압정뿌리기1', '압정뿌리기2', '압정뿌리기3', '끈적끈적네트']
    my_traps = my_env.get('traps', [])
    for trap in traps:
        state[f'my_trap_{trap}'] = 1.0 if trap in my_traps else 0.0
    # 누적 차원: 117

    # 12-2. 상대 필드 함정 (7차원)
    enemy_traps = enemy_env.get('traps', [])
    for trap in traps:
        state[f'enemy_trap_{trap}'] = 1.0 if trap in enemy_traps else 0.0
    # 누적 차원: 124

    # 13. 스크린 효과 정보 (2차원)
    # 13-1. 내 스크린 효과 (1차원)
    screens = ['빛의장막', '리플렉터', '오로라베일']
    my_screen_effect = next((e for e in my_effects if e['name'] in screens), None)
    state['my_screen_effect'] = my_screen_effect['remainingTurn'] / 5 if my_screen_effect else 0.0
    # 누적 차원: 125

    # 13-2. 상대 스크린 효과 (1차원)
    enemy_screen_effect = next((e for e in enemy_effects if e['name'] in screens), None)
    state['enemy_screen_effect'] = enemy_screen_effect['remainingTurn'] / 5 if enemy_screen_effect else 0.0
    # 누적 차원: 126

    # print("✅ 상태 벡터 길이:", len(state))
    return state 