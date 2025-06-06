from typing import List, Dict

def calculate_type_effectiveness(move_type: str, target_types: List[str]) -> float:
    type_chart: Dict[str, Dict[str, float]] = {
        "불": {"풀": 2, "얼음": 2, "벌레": 2, "강철": 2, "물": 0.5, "바위": 0.5, "불": 0.5, "드래곤": 0.5},
        "물": {"불": 2, "땅": 2, "바위": 2, "물": 0.5, "풀": 0.5, "드래곤": 0.5},
        "풀": {"물": 2, "땅": 2, "바위": 2, "불": 0.5, "풀": 0.5, "비행": 0.5, "벌레": 0.5, "독": 0.5, "드래곤": 0.5, "강철": 0.5},
        "전기": {"물": 2, "비행": 2, "풀": 0.5, "전기": 0.5, "드래곤": 0.5, "땅": 0},
        "얼음": {"풀": 2, "땅": 2, "비행": 2, "드래곤": 2, "불": 0.5, "물": 0.5, "강철": 0.5, "얼음": 0.5},
        "프리즈드라이": {"풀": 2, "땅": 2, "비행": 2, "드래곤": 2, "물": 2, "불": 0.5, "강철": 0.5, "얼음": 0.5},
        "격투": {"얼음": 2, "바위": 2, "악": 2, "노말": 2, "강철": 2, "벌레": 0.5, "독": 0.5, "비행": 0.5, "에스퍼": 0.5, "페어리": 0.5, "고스트": 0},
        "독": {"풀": 2, "페어리": 2, "독": 0.5, "땅": 0.5, "바위": 0.5, "고스트": 0.5, "강철": 0},
        "땅": {"불": 2, "전기": 2, "독": 2, "바위": 2, "강철": 2, "풀": 0.5, "벌레": 0.5, "비행": 0},
        "비행": {"풀": 2, "격투": 2, "벌레": 2, "전기": 0.5, "바위": 0.5, "강철": 0.5},
        "에스퍼": {"격투": 2, "독": 2, "에스퍼": 0.5, "악": 0, "강철": 0.5},
        "벌레": {"풀": 2, "에스퍼": 2, "악": 2, "불": 0.5, "격투": 0.5, "독": 0.5, "비행": 0.5, "고스트": 0.5, "강철": 0.5, "페어리": 0.5},
        "바위": {"불": 2, "얼음": 2, "비행": 2, "벌레": 2, "격투": 0.5, "땅": 0.5, "강철": 0.5},
        "고스트": {"에스퍼": 2, "고스트": 2, "악": 0.5, "노말": 0},
        "드래곤": {"드래곤": 2, "강철": 0.5, "페어리": 0},
        "악": {"에스퍼": 2, "고스트": 2, "격투": 0.5, "악": 0.5, "페어리": 0.5},
        "강철": {"얼음": 2, "바위": 2, "페어리": 2, "불": 0.5, "물": 0.5, "전기": 0.5, "강철": 0.5},
        "페어리": {"격투": 2, "악": 2, "드래곤": 2, "불": 0.5, "독": 0.5, "강철": 0.5},
        "노말": {"바위": 0.5, "강철": 0.5, "고스트": 0},
    }

    modifier = 1.0

    for target_type in target_types:
        effectiveness = type_chart.get(move_type, {}).get(target_type, 1.0)
        if effectiveness == 0:
            return 0.0
        modifier *= effectiveness

    return modifier