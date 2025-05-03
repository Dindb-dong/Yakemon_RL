from typing import List, Dict, Optional
from p_models.pokemon_info import PokemonInfo
from p_models.move_info import MoveInfo

def calculate_type_effectiveness_with_ability(
    attacker: PokemonInfo,
    defender: PokemonInfo,
    move: MoveInfo
) -> float:
    effectiveness = 1.0
    
    # Calculate type effectiveness
    for defender_type in defender.types:
        effectiveness *= get_type_effectiveness(move.type, defender_type)
        
    # Apply ability effects
    if defender.ability:
        if defender.ability.name == "부유" and move.type == "땅":
            effectiveness = 0
        elif defender.ability.name == "플레어브루" and move.type == "불꽃":
            effectiveness = 0
        elif defender.ability.name == "전기엔진" and move.type == "전기":
            effectiveness = 0
        elif defender.ability.name == "모터드라이브" and move.type == "전기":
            effectiveness = 0
        elif defender.ability.name == "저수" and move.type == "물":
            effectiveness = 0
        elif defender.ability.name == "먹보" and move.type == "풀":
            effectiveness = 0
            
    return effectiveness

def is_type_immune(type_name: str, move_type: str) -> bool:
    # Define type immunities
    immunities = {
        "노말": ["고스트"],
        "전기": ["땅"],
        "독": ["강철"],
        "땅": ["비행"],
        "고스트": ["노말"],
        "에스퍼": ["악"],
        "드래곤": ["페어리"]
    }
    
    return type_name in immunities.get(move_type, [])

def get_type_effectiveness(attack_type: str, defense_type: str) -> float:
    # Define type effectiveness chart
    effectiveness = {
        "노말": {
            "바위": 0.5,
            "고스트": 0,
            "강철": 0.5
        },
        "불꽃": {
            "불꽃": 0.5,
            "물": 0.5,
            "풀": 2,
            "얼음": 2,
            "벌레": 2,
            "바위": 0.5,
            "드래곤": 0.5,
            "강철": 2
        },
        "물": {
            "불꽃": 2,
            "물": 0.5,
            "풀": 0.5,
            "땅": 2,
            "바위": 2,
            "드래곤": 0.5
        },
        "전기": {
            "물": 2,
            "전기": 0.5,
            "풀": 0.5,
            "땅": 0,
            "비행": 2,
            "드래곤": 0.5
        },
        "풀": {
            "불꽃": 0.5,
            "물": 2,
            "풀": 0.5,
            "독": 0.5,
            "땅": 2,
            "비행": 0.5,
            "벌레": 0.5,
            "바위": 2,
            "드래곤": 0.5,
            "강철": 0.5
        },
        "얼음": {
            "불꽃": 0.5,
            "물": 0.5,
            "풀": 2,
            "얼음": 0.5,
            "땅": 2,
            "비행": 2,
            "드래곤": 2,
            "강철": 0.5
        },
        "격투": {
            "노말": 2,
            "얼음": 2,
            "독": 0.5,
            "비행": 0.5,
            "에스퍼": 0.5,
            "벌레": 0.5,
            "바위": 2,
            "고스트": 0,
            "악": 2,
            "강철": 2,
            "페어리": 0.5
        },
        "독": {
            "풀": 2,
            "독": 0.5,
            "땅": 0.5,
            "바위": 0.5,
            "고스트": 0.5,
            "강철": 0,
            "페어리": 2
        },
        "땅": {
            "불꽃": 2,
            "전기": 2,
            "풀": 0.5,
            "독": 2,
            "비행": 0,
            "벌레": 0.5,
            "바위": 2,
            "강철": 2
        },
        "비행": {
            "전기": 0.5,
            "풀": 2,
            "격투": 2,
            "벌레": 2,
            "바위": 0.5,
            "강철": 0.5
        },
        "에스퍼": {
            "격투": 2,
            "독": 2,
            "에스퍼": 0.5,
            "강철": 0.5,
            "페어리": 0.5
        },
        "벌레": {
            "불꽃": 0.5,
            "풀": 2,
            "격투": 0.5,
            "독": 0.5,
            "비행": 0.5,
            "에스퍼": 2,
            "고스트": 0.5,
            "악": 2,
            "강철": 0.5,
            "페어리": 0.5
        },
        "바위": {
            "불꽃": 2,
            "얼음": 2,
            "격투": 0.5,
            "땅": 0.5,
            "비행": 2,
            "벌레": 2,
            "강철": 0.5
        },
        "고스트": {
            "노말": 0,
            "에스퍼": 2,
            "고스트": 2,
            "악": 0.5
        },
        "드래곤": {
            "드래곤": 2,
            "강철": 0.5,
            "페어리": 0
        },
        "악": {
            "격투": 0.5,
            "에스퍼": 2,
            "고스트": 2,
            "악": 0.5,
            "페어리": 0.5
        },
        "강철": {
            "불꽃": 0.5,
            "물": 0.5,
            "전기": 0.5,
            "얼음": 2,
            "바위": 2,
            "강철": 0.5,
            "페어리": 2
        },
        "페어리": {
            "불꽃": 0.5,
            "격투": 2,
            "독": 0.5,
            "드래곤": 2,
            "악": 2,
            "강철": 0.5
        }
    }
    
    return effectiveness.get(attack_type, {}).get(defense_type, 1.0) 