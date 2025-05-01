import random
from typing import List, Optional, Dict, Union
from p_models.ability_info import AbilityInfo

# availableAbilities 리스트
available_abilities: List[AbilityInfo] = [
    AbilityInfo(0, '없음'),
    AbilityInfo(1, '엽록소', util=['rank_buff']),
    AbilityInfo(2, '선파워', offensive=['rank_buff']),
    AbilityInfo(3, '급류', offensive=['damage_buff']),
    AbilityInfo(4, '맹화', offensive=['damage_buff']),
    AbilityInfo(5, '심록', offensive=['damage_buff']),
    AbilityInfo(6, '우격다짐', offensive=['damage_buff']),
    AbilityInfo(7, '가속', util=['rank_change']),
    AbilityInfo(8, '철주먹', offensive=['damage_buff']),
    AbilityInfo(9, '조가비갑옷', defensive=['critical_nullification']),
    AbilityInfo(10, '오기', util=['rank_change']),
    AbilityInfo(11, '이판사판', offensive=['damage_buff']),
    AbilityInfo(12, '심술꾸러기', util=['etc']),
    AbilityInfo(13, '방탄', defensive=['damage_nullification']),
    AbilityInfo(14, '변환자재', offensive=['type_change']),
    AbilityInfo(15, '위협', appear=['rank_change']),
    AbilityInfo(16, '리베로', offensive=['type_change']),
    AbilityInfo(17, '그래스메이커', appear=['field_change']),
    AbilityInfo(18, '스나이퍼', offensive=['damage_buff']),
    AbilityInfo(19, '천진', util=['rank_nullification']),
    AbilityInfo(20, '변환자재', offensive=['type_change']),
    AbilityInfo(21, '자기과신', offensive=['rank_change']),
    AbilityInfo(22, '타오르는불꽃', defensive=['type_nullification'])
]

# abilityData 함수 변환
def ability_data(abilities: List[str]) -> AbilityInfo:
    selected = [
        ability for ability in available_abilities
        if ability.name in abilities
    ]

    invalid_names = [name for name in abilities if not any(ability.name == name for ability in available_abilities)]

    if invalid_names:
        print(f"[abilityData] 유효하지 않은 특성 이름{'들' if len(invalid_names) > 1 else ''} 감지됨:\n- " + "\n- ".join(invalid_names))
        return available_abilities[0]  # fallback: '없음' 리턴

    return random.choice(selected)