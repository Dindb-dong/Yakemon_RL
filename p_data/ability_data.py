import random
from typing import List, Dict, Union
from typing import Optional
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
    AbilityInfo(22, '타오르는불꽃', defensive=['type_nullification']),
    AbilityInfo(23, '재생력', util=['change_trigger']),
    AbilityInfo(24, '가뭄', appear=['weather_change']),
    AbilityInfo(25, '승기', defensive=['rank_change']),
    AbilityInfo(26, '테크니션', offensive=['damage_buff']),
    AbilityInfo(27, '불꽃몸', defensive=['status_change']),
    AbilityInfo(28, '쓱쓱', util=['rank_buff']),
    AbilityInfo(29, '독가시', defensive=['status_change']),
    AbilityInfo(30, '저수', defensive=['type_nullification']),
    AbilityInfo(31, '벌레의알림', offensive=['damage_buff']),
    AbilityInfo(32, '메가런처', offensive=['damage_buff']),
    AbilityInfo(33, '불면', util=['status_nullification']),
    AbilityInfo(34, '부식', util=['etc']),
    AbilityInfo(35, '수포', offensive=['damage_buff'], util=['status_nullification']),
    AbilityInfo(36, '여왕의위엄', defensive=['damage_nullification']),
    AbilityInfo(37, '증기기관', defensive=['rank_change']),
    AbilityInfo(38, '적응력', offensive=['damage_buff']),
    AbilityInfo(39, '의욕', offensive=['damage_buff']),
    AbilityInfo(40, '깨어진갑옷', defensive=['rank_change']),
    AbilityInfo(41, '변덕쟁이', util=['rank_change']),
    AbilityInfo(42, '리프가드', util=['status_nullification']),
    AbilityInfo(43, '정의의마음', defensive=['rank_change']),
    AbilityInfo(44, '마이페이스', util=['status_nullification', 'intimidate_nullification']),
    AbilityInfo(45, '둔감', util=['status_nullification', 'intimidate_nullification']),
    AbilityInfo(46, '하얀연기', util=['rank_nullification']),
    AbilityInfo(47, '클리어바디', util=['rank_nullification']),
    AbilityInfo(48, '메탈프로텍트', util=['rank_nullification']),
    AbilityInfo(49, '이상한비늘', defensive=['damage_reduction']),
    AbilityInfo(50, '포자', defensive=['status_change']),
    AbilityInfo(51, '의기양양', util=['status_nullification']),
    AbilityInfo(52, '수의베일', util=['status_nullification']),
    AbilityInfo(53, '자연회복', util=['etc']),
    AbilityInfo(54, '독수', offensive=['status_change']),
    AbilityInfo(55, '질풍날개', util=['etc']),
    AbilityInfo(56, '틀깨기', offensive=['ability_nullification']),
    AbilityInfo(57, '테라볼티지', offensive=['ability_nullification']),
    AbilityInfo(58, '터보블레이즈', offensive=['ability_nullification']),
    AbilityInfo(59, '균사의힘', offensive=['ability_nullification']),
    AbilityInfo(60, '곡예', util=['rank_buff'])
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