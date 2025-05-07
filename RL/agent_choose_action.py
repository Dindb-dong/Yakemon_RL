import tensorflow as tf
import numpy as np
from typing import Union, Dict, List, Optional
from .get_state_vector import get_state  # 이것도 나중에 구현 필요

rl_model: Optional[tf.keras.Model] = None

def load_rl_model():
    """RL 모델을 로드하는 함수"""
    global rl_model
    try:
        rl_model = tf.keras.models.load_model("model/converted/final_keras/model.h5")
        # TODO: 에러 트래킹 필요 
        # TODO: 모델 루트 수정 필요
        print("✅ RL 모델 로딩 완료")
    except:
        print("모델 로드 실패")
        raise Exception("RL 모델이 로딩되지 않았습니다.")

def get_action_from_state(state: List[float]) -> int:
    """상태 벡터로부터 행동을 선택하는 함수
    
    Args:
        state: [96] 크기의 상태 벡터
        
    Returns:
        선택된 행동 인덱스 (0-5)
        0-3: 기술 사용
        4-5: 포켓몬 교체
    """
    if rl_model is None:
        raise Exception("RL 모델이 로딩되지 않았습니다.")
        
    input_tensor = tf.convert_to_tensor([state])  # [1, 96]
    output = rl_model(input_tensor)
    action = tf.argmax(output, axis=1).numpy()[0]
    return int(action)

def get_switch_target_index(current_index: int, switch_action_index: int) -> int:
    """교체 행동에 대한 실제 교체 대상 인덱스를 반환하는 함수
    
    Args:
        current_index: 현재 활성화된 포켓몬의 인덱스
        switch_action_index: 교체 행동 인덱스 (0 또는 1)
        
    Returns:
        실제 교체할 포켓몬의 인덱스 또는 -1 (유효하지 않은 경우)
    """
    all_indexes = [0, 1, 2]
    candidates = [i for i in all_indexes if i != current_index]
    
    if switch_action_index < 0 or switch_action_index >= len(candidates):
        return -1
    return candidates[switch_action_index]

def agent_choose_action(
    side: str,
    my_team: List[Dict],
    enemy_team: List[Dict],
    active_my: int,
    active_enemy: int
) -> Union[Dict, Dict[str, Union[str, int]]]:
    """에이전트가 행동을 선택하는 함수
    
    Args:
        side: 'my' 또는 'enemy'
        my_team: 내 팀 정보
        enemy_team: 상대 팀 정보
        active_my: 현재 활성화된 내 포켓몬 인덱스
        active_enemy: 현재 활성화된 상대 포켓몬 인덱스
        
    Returns:
        선택된 행동 (기술 사용 또는 교체)
    """
    is_enemy = side == 'enemy'
    state_vector = get_state(is_enemy)
    result = get_action_from_state(state_vector)
    
    mine_team = enemy_team if is_enemy else my_team
    active_index = active_enemy if is_enemy else active_my
    my_pokemon = mine_team[active_enemy if is_enemy else active_my]
    
    # 사용 가능한 기술 필터링
    usable_moves = [move for move in my_pokemon['base']['moves'] 
                   if my_pokemon['pp'][move['name']] > 0]
    
    if result is not None:
        if result < 4:
            # 기술 사용
            if result < len(usable_moves):
                return usable_moves[result]
        else:
            # 포켓몬 교체
            switch_index = get_switch_target_index(active_index, result - 4)
            if switch_index != -1:
                return {"type": "switch", "index": switch_index}
    
    # 기본값: 첫 번째 사용 가능한 기술 반환
    return usable_moves[0] 