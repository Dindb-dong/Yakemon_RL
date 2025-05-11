"""포켓몬 템플릿 데이터 모듈"""

from .pokemon import Pokemon
from .types import TYPE_NAMES, PokemonType
from .moves import Move

# 포켓몬 템플릿 데이터
POKEMON_TEMPLATES = [
    {
        "id": 3,
        "name": "이상해꽃",  # Venusaur
        "types": [TYPE_NAMES["풀"], TYPE_NAMES["독"]],
        "stats": {"hp": 80, "atk": 82, "def": 83, "spa": 100, "spd": 100, "spe": 80},
        "moves": [
            Move("기가드레인", TYPE_NAMES["풀"], "Special", 75, 100, 15, {"heal": 0.5}),
            Move("오물폭탄", TYPE_NAMES["독"], "Special", 90, 100, 10, {"status": "Poison", "chance": 0.1}),
            Move("대지의힘", TYPE_NAMES["땅"], "Special", 90, 100, 10, {"stat_change": "spd", "chance": 0.1}),
            Move("수면가루", TYPE_NAMES["풀"], "Status", 0, 75, 15, {"status": "Sleep"})
        ]
    },
    {
        "id": 6,
        "name": "리자몽",  # Charizard
        "types": [TYPE_NAMES["불"], TYPE_NAMES["비행"]],
        "stats": {"hp": 78, "atk": 84, "def": 78, "spa": 109, "spd": 85, "spe": 100},
        "moves": [
            Move("에어슬래시", TYPE_NAMES["비행"], "Special", 75, 95, 15, {"status": "Flinch", "chance": 0.3}),
            Move("불대문자", TYPE_NAMES["불"], "Special", 110, 85, 5, {"status": "Burn", "chance": 0.1}),
            Move("지진", TYPE_NAMES["땅"], "Physical", 100, 100, 10, {}),
            Move("오버히트", TYPE_NAMES["불"], "Special", 130, 90, 5, {"stat_change": "spa", "self_change": -2})
        ]
    },
    {
        "id": 9,
        "name": "거북왕",  # Blastoise
        "types": [TYPE_NAMES["물"]],
        "stats": {"hp": 79, "atk": 83, "def": 100, "spa": 85, "spd": 105, "spe": 78},
        "moves": [
            Move("하이드로펌프", TYPE_NAMES["물"], "Special", 110, 80, 5, {}),
            Move("냉동빔", TYPE_NAMES["얼음"], "Special", 90, 100, 10, {"status": "Freeze", "chance": 0.1}),
            Move("껍질깨기", TYPE_NAMES["노말"], "Status", 0, 100, 20, {"self_stat_changes": {"def": -1, "spd": -1, "atk": 2, "spa": 2, "spe": 2}}),
            Move("악의파동", TYPE_NAMES["악"], "Special", 80, 100, 15, {"status": "Flinch", "chance": 0.3})
        ]
    },
    {
        "id": 157,
        "name": "블레이범",  # Typhlosion
        "types": [TYPE_NAMES["불"]],
        "stats": {"hp": 76, "atk": 104, "def": 71, "spa": 104, "spd": 71, "spe": 108},
        "moves": [
            Move("니트로차지", TYPE_NAMES["불"], "Physical", 50, 100, 20, {"stat_change": "spe", "self_change": 1}),
            Move("불대문자", TYPE_NAMES["불"], "Special", 110, 85, 5, {"status": "Burn", "chance": 0.1}),
            Move("와일드볼트", TYPE_NAMES["전기"], "Physical", 90, 100, 15, {"recoil": 0.25}),
            Move("지진", TYPE_NAMES["땅"], "Physical", 100, 100, 10, {})
        ]
    },
    {
        "id": 154,
        "name": "메가니움",  # Meganium
        "types": [TYPE_NAMES["풀"]],
        "stats": {"hp": 80, "atk": 82, "def": 100, "spa": 83, "spd": 100, "spe": 80},
        "moves": [
            Move("기가드레인", TYPE_NAMES["풀"], "Special", 75, 100, 10, {"heal": 0.5}),
            Move("광합성", TYPE_NAMES["풀"], "Status", 0, 100, 5, {"heal": 0.5}),
            Move("씨뿌리기", TYPE_NAMES["풀"], "Status", 0, 90, 10, {"status": "Leech Seed"}),
            Move("맹독", TYPE_NAMES["독"], "Status", 0, 90, 20, {"status": "Toxic"})
        ]
    },
    {
        "id": 160,
        "name": "장크로다일",  # Feraligatr
        "types": [TYPE_NAMES["물"]],
        "stats": {"hp": 85, "atk": 105, "def": 100, "spa": 79, "spd": 83, "spe": 78},
        "moves": [
            Move("용의춤", TYPE_NAMES["드래곤"], "Status", 0, 100, 20, {"self_stat_changes": {"atk": 1, "spe": 1}}),
            Move("아쿠아브레이크", TYPE_NAMES["물"], "Physical", 85, 100, 10, {"stat_change": "def", "chance": 0.2}),
            Move("냉동펀치", TYPE_NAMES["얼음"], "Physical", 75, 100, 15, {"status": "Freeze", "chance": 0.1}),
            Move("엄청난힘", TYPE_NAMES["노말"], "Physical", 120, 100, 5, {"self_stat_changes": {"atk": -1, "def": -1}})
        ]
    },
    {
        "id": 257,
        "name": "번치코",  # Blaziken
        "types": [TYPE_NAMES["불"], TYPE_NAMES["격투"]],
        "stats": {"hp": 80, "atk": 120, "def": 70, "spa": 110, "spd": 70, "spe": 80},
        "moves": [
            Move("칼춤", TYPE_NAMES["노말"], "Status", 0, 100, 20, {"self_stat_changes": {"atk": 2}}),
            Move("플레어드라이브", TYPE_NAMES["불"], "Physical", 120, 100, 15, {"recoil": 0.33, "status": "Burn", "chance": 0.1}),
            Move("인파이트", TYPE_NAMES["격투"], "Physical", 120, 100, 5, {"self_stat_changes": {"def": -1, "spd": -1}}),
            Move("스톤에지", TYPE_NAMES["바위"], "Physical", 100, 80, 5, {"critical_rate": 1})
        ]
    },
    {
        "id": 254,
        "name": "나무킹",  # Sceptile
        "types": [TYPE_NAMES["풀"]],
        "stats": {"hp": 70, "atk": 85, "def": 65, "spa": 105, "spd": 85, "spe": 120},
        "moves": [
            Move("용의파동", TYPE_NAMES["드래곤"], "Special", 85, 100, 15, {}),
            Move("기가드레인", TYPE_NAMES["풀"], "Special", 75, 100, 10, {"heal": 0.5}),
            Move("진공파", TYPE_NAMES["격투"], "Special", 40, 100, 30, {"priority": 1}),
            Move("광합성", TYPE_NAMES["풀"], "Status", 0, 100, 5, {"heal": 0.5})
        ]
    },
    {
        "id": 260,
        "name": "대짱이",  # Swampert
        "types": [TYPE_NAMES["물"], TYPE_NAMES["땅"]],
        "stats": {"hp": 100, "atk": 110, "def": 90, "spa": 85, "spd": 90, "spe": 60},
        "moves": [
            Move("퀵턴", TYPE_NAMES["물"], "Physical", 60, 100, 20, {"uturn": True}),
            Move("눈사태", TYPE_NAMES["얼음"], "Physical", 120, 100, 10, {"priority": -4}),
            Move("아쿠아브레이크", TYPE_NAMES["물"], "Physical", 85, 100, 10, {"stat_change": "def", "chance": 0.2}),
            Move("지진", TYPE_NAMES["땅"], "Physical", 100, 100, 10, {})
        ]
    },
    {
        "id": 392,
        "name": "초염몽",  # Infernape
        "types": [TYPE_NAMES["불"], TYPE_NAMES["격투"]],
        "stats": {"hp": 76, "atk": 104, "def": 71, "spa": 104, "spd": 71, "spe": 108},
        "moves": [
            Move("번개펀치", TYPE_NAMES["전기"], "Physical", 75, 100, 15, {"status": "Paralysis", "chance": 0.1}),
            Move("플레어드라이브", TYPE_NAMES["불"], "Physical", 120, 100, 15, {"status": "Burn", "chance": 0.1, "recoil": 0.33}),
            Move("드레인펀치", TYPE_NAMES["격투"], "Physical", 75, 100, 10, {"heal": 0.5}),
            Move("지진", TYPE_NAMES["땅"], "Physical", 100, 100, 10, {})
        ]
    },
    {
        "id": 389,
        "name": "토대부기",  # Torterra
        "types": [TYPE_NAMES["풀"], TYPE_NAMES["땅"]],
        "stats": {"hp": 95, "atk": 109, "def": 105, "spa": 75, "spd": 85, "spe": 56},
        "moves": [
            Move("껍질깨기", TYPE_NAMES["노말"], "Status", 0, 100, 20, {"self_stat_changes": {"atk": 2, "spa": 2, "spe": 2, "def": -1, "spd": -1}}),
            Move("지진", TYPE_NAMES["땅"], "Physical", 100, 100, 10, {}),
            Move("아이언헤드", TYPE_NAMES["강철"], "Physical", 80, 100, 15, {"status": "Flinch", "chance": 0.3}),
            Move("우드해머", TYPE_NAMES["풀"], "Physical", 120, 100, 15, {"recoil": 0.33})
        ]
    },
    {
        "id": 395,
        "name": "엠페르트",  # Empoleon
        "types": [TYPE_NAMES["물"], TYPE_NAMES["강철"]],
        "stats": {"hp": 84, "atk": 86, "def": 88, "spa": 111, "spd": 101, "spe": 60},
        "moves": [
            Move("하이드로펌프", TYPE_NAMES["물"], "Special", 110, 80, 5, {}),
            Move("냉동빔", TYPE_NAMES["얼음"], "Special", 90, 100, 10, {"status": "Freeze", "chance": 0.1}),
            Move("풀묶기", TYPE_NAMES["풀"], "Special", 80, 100, 15, {}),
            Move("퀵턴", TYPE_NAMES["물"], "Physical", 60, 100, 20, {"uturn": True})
        ]
    },
    {
        "id": 500,
        "name": "염무왕",  # Emboar
        "types": [TYPE_NAMES["불"], TYPE_NAMES["격투"]],
        "stats": {"hp": 110, "atk": 123, "def": 65, "spa": 100, "spd": 65, "spe": 65},
        "moves": [
            Move("양날박치기", TYPE_NAMES["바위"], "Physical", 120, 80, 15, {"recoil": 0.33}),
            Move("와일드볼트", TYPE_NAMES["전기"], "Physical", 90, 100, 15, {"recoil": 0.25}),
            Move("플레어드라이브", TYPE_NAMES["불"], "Physical", 120, 100, 15, {"recoil": 0.33, "status": "Burn", "chance": 0.1}),
            Move("니트로차지", TYPE_NAMES["불"], "Physical", 50, 100, 20, {"stat_change": "spe", "self_change": 1})
        ]
    },
    {
        "id": 497,
        "name": "샤로다",  # Serperior
        "types": [TYPE_NAMES["풀"]],
        "stats": {"hp": 75, "atk": 75, "def": 95, "spa": 75, "spd": 95, "spe": 113},
        "moves": [
            Move("리프스톰", TYPE_NAMES["풀"], "Special", 130, 90, 5, {"self_stat_changes": {"spa": -2}}),
            Move("기가드레인", TYPE_NAMES["풀"], "Special", 75, 100, 10, {"heal": 0.5}),
            Move("뱀눈초리", TYPE_NAMES["노말"], "Status", 0, 100, 30, {"status": "Paralysis"}),
            Move("용의파동", TYPE_NAMES["드래곤"], "Special", 85, 100, 10, {})
        ]
    },
    {
        "id": 503,
        "name": "대검귀",  # Samurott
        "types": [TYPE_NAMES["물"]],
        "stats": {"hp": 95, "atk": 100, "def": 85, "spa": 108, "spd": 70, "spe": 70},
        "moves": [
            Move("눈사태", TYPE_NAMES["얼음"], "Physical", 120, 100, 10, {"priority": -4}),
            Move("아쿠아브레이크", TYPE_NAMES["물"], "Physical", 85, 100, 10, {"stat_change": "def", "chance": 0.2}),
            Move("풀묶기", TYPE_NAMES["풀"], "Special", 80, 100, 15, {}),
            Move("아쿠아제트", TYPE_NAMES["물"], "Physical", 40, 100, 20, {"priority": 1})
        ]
    },
    {
        "id": 655,
        "name": "마폭시",  # Delphox
        "types": [TYPE_NAMES["불"], TYPE_NAMES["에스퍼"]],
        "stats": {"hp": 75, "atk": 69, "def": 72, "spa": 114, "spd": 100, "spe": 104},
        "moves": [
            Move("매지컬플레임", TYPE_NAMES["불"], "Special", 75, 100, 10, {"stat_change": "spa", "chance": 1.0}),
            Move("사이코키네시스", TYPE_NAMES["에스퍼"], "Special", 90, 100, 10, {"stat_change": "spd", "chance": 0.1}),
            Move("에너지볼", TYPE_NAMES["풀"], "Special", 90, 100, 10, {"stat_change": "spd", "chance": 0.1}),
            Move("명상", TYPE_NAMES["에스퍼"], "Status", 0, 100, 20, {"self_stat_changes": {"spa": 1, "spd": 1}})
        ]
    },
    {
        "id": 652,
        "name": "브리가론",  # Chesnaught
        "types": [TYPE_NAMES["풀"], TYPE_NAMES["격투"]],
        "stats": {"hp": 88, "atk": 107, "def": 122, "spa": 74, "spd": 75, "spe": 64},
        "moves": [
            Move("씨기관총", TYPE_NAMES["풀"], "Physical", 25, 100, 30, {"multi_hit": True}),
            Move("광합성", TYPE_NAMES["풀"], "Status", 0, 100, 5, {"heal": 0.5}),
            Move("바디프레스", TYPE_NAMES["격투"], "Physical", 80, 100, 10, {}),
            Move("철벽", TYPE_NAMES["강철"], "Status", 0, 100, 15, {"self_stat_changes": {"def": 2}})
        ]
    },
    {
        "id": 658,
        "name": "개굴닌자",  # Greninja
        "types": [TYPE_NAMES["물"], TYPE_NAMES["악"]],
        "stats": {"hp": 72, "atk": 95, "def": 67, "spa": 103, "spd": 71, "spe": 122},
        "moves": [
            Move("물수리검", TYPE_NAMES["물"], "Special", 15, 100, 20, {"priority": 1, "multi_hit": True, "critical_rate": 1}),
            Move("악의파동", TYPE_NAMES["악"], "Special", 80, 100, 15, {"status": "Flinch", "chance": 0.2}),
            Move("독압정", TYPE_NAMES["독"], "Status", 0, 100, 20, {"trap": "Spikes"}),
            Move("냉동빔", TYPE_NAMES["얼음"], "Special", 90, 100, 10, {"status": "Freeze", "chance": 0.1})
        ]
    },
    {
        "id": 727,
        "name": "어흥염",  # Incineroar
        "types": [TYPE_NAMES["불"], TYPE_NAMES["악"]],
        "stats": {"hp": 95, "atk": 115, "def": 90, "spa": 80, "spd": 90, "spe": 60},
        "moves": [
            Move("플레어드라이브", TYPE_NAMES["불"], "Physical", 120, 100, 15, {"recoil": 0.33, "status": "Burn", "chance": 0.1}),
            Move("도깨비불", TYPE_NAMES["불"], "Status", 0, 85, 15, {"status": "Burn"}),
            Move("DD래리어트", TYPE_NAMES["악"], "Physical", 85, 100, 10, {"rank_nullification": True}),
            Move("막말내뱉기", TYPE_NAMES["악"], "Status", 0, 100, 10, {"uturn": True, "stat_changes": {"spa": -1, "atk": -1}})
        ]
    },
    {
        "id": 724,
        "name": "모크나이퍼",  # Decidueye
        "types": [TYPE_NAMES["풀"], TYPE_NAMES["고스트"]],
        "stats": {"hp": 78, "atk": 107, "def": 75, "spa": 100, "spd": 100, "spe": 70},
        "moves": [
            Move("리프블레이드", TYPE_NAMES["풀"], "Physical", 90, 100, 15, {"critical_rate": 1}),
            Move("폴터가이스트", TYPE_NAMES["고스트"], "Physical", 110, 90, 5, {}),
            Move("칼춤", TYPE_NAMES["노말"], "Status", 0, 100, 20, {"self_stat_changes": {"atk": 2}}),
            Move("더블윙", TYPE_NAMES["비행"], "Physical", 40, 90, 10, {"double_hit": True})
        ]
    },
    {
        "id": 730,
        "name": "누리레느",  # Primarina
        "types": [TYPE_NAMES["물"], TYPE_NAMES["페어리"]],
        "stats": {"hp": 80, "atk": 74, "def": 74, "spa": 126, "spd": 116, "spe": 60},
        "moves": [
            Move("물거품아리아", TYPE_NAMES["물"], "Special", 90, 100, 10, {}),
            Move("문포스", TYPE_NAMES["페어리"], "Special", 95, 100, 15, {"stat_change": "spa", "chance": 0.3}),
            Move("아쿠아제트", TYPE_NAMES["물"], "Physical", 40, 100, 20, {"priority": 1}),
            Move("에너지볼", TYPE_NAMES["풀"], "Special", 90, 100, 10, {"stat_change": "spd", "chance": 0.1})
        ]
    },
    {
        "id": 815,
        "name": "에이스번",  # Cinderace
        "types": [TYPE_NAMES["불"]],
        "stats": {"hp": 80, "atk": 116, "def": 75, "spa": 65, "spd": 75, "spe": 119},
        "moves": [
            Move("화염볼", TYPE_NAMES["불"], "Physical", 120, 90, 5, {"status": "Burn", "chance": 0.1}),
            Move("무릎차기", TYPE_NAMES["격투"], "Physical", 130, 90, 10, {"fail_damage": 0.5}),
            Move("유턴", TYPE_NAMES["벌레"], "Physical", 70, 100, 20, {"uturn": True}),
            Move("칼춤", TYPE_NAMES["노말"], "Status", 0, 100, 20, {"self_stat_changes": {"atk": 2}})
        ]
    },
    {
        "id": 812,
        "name": "고릴타",  # Rillaboom
        "types": [TYPE_NAMES["풀"]],
        "stats": {"hp": 100, "atk": 125, "def": 90, "spa": 60, "spd": 70, "spe": 85},
        "moves": [
            Move("그래스슬라이더", TYPE_NAMES["풀"], "Physical", 55, 100, 20, {"priority": 1}),
            Move("10만마력", TYPE_NAMES["땅"], "Physical", 95, 95, 10, {}),
            Move("우드해머", TYPE_NAMES["풀"], "Physical", 120, 100, 5, {"recoil": 0.33}),
            Move("칼춤", TYPE_NAMES["노말"], "Status", 0, 100, 20, {"self_stat_changes": {"atk": 2}})
        ]
    },
    {
        "id": 818,
        "name": "인텔리레온",  # Inteleon
        "types": [TYPE_NAMES["물"]],
        "stats": {"hp": 70, "atk": 85, "def": 65, "spa": 125, "spd": 65, "spe": 120},
        "moves": [
            Move("기충전", TYPE_NAMES["노말"], "Status", 0, 100, 20, {"self_stat_changes": {"critical": 2}}),
            Move("노려맞히기", TYPE_NAMES["물"], "Physical", 80, 100, 15, {"critical_rate": 1}),
            Move("냉동빔", TYPE_NAMES["얼음"], "Special", 90, 100, 10, {"status": "Freeze", "chance": 0.1}),
            Move("섀도볼", TYPE_NAMES["고스트"], "Special", 80, 100, 15, {"stat_change": "spd", "chance": 0.2})
        ]
    },
    {
        "id": 911,
        "name": "라우드본",  # Skeledirge
        "types": [TYPE_NAMES["불"], TYPE_NAMES["고스트"]],
        "stats": {"hp": 104, "atk": 75, "def": 100, "spa": 110, "spd": 75, "spe": 66},
        "moves": [
            Move("게으름피우기", TYPE_NAMES["노말"], "Status", 0, 100, 5, {"heal": 0.5}),
            Move("플레어송", TYPE_NAMES["불"], "Special", 100, 100, 10, {"self_stat_changes": {"spa": 1}}),
            Move("섀도볼", TYPE_NAMES["고스트"], "Special", 80, 100, 15, {"stat_change": "spd", "chance": 0.2}),
            Move("도깨비불", TYPE_NAMES["불"], "Status", 0, 85, 15, {"status": "Burn"})
        ]
    },
    {
        "id": 907,
        "name": "마스카나",  # Meowscarada
        "types": [TYPE_NAMES["풀"], TYPE_NAMES["악"]],
        "stats": {"hp": 76, "atk": 110, "def": 70, "spa": 81, "spd": 70, "spe": 123},
        "moves": [
            Move("트릭플라워", TYPE_NAMES["풀"], "Physical", 70, 100, 10, {"critical_rate": 3}),
            Move("유턴", TYPE_NAMES["벌레"], "Physical", 70, 100, 20, {"uturn": True}),
            Move("깜짝베기", TYPE_NAMES["악"], "Physical", 70, 100, 15, {"critical_rate": 1}),
            Move("치근거리기", TYPE_NAMES["페어리"], "Physical", 90, 90, 10, {"stat_change": "spa", "chance": 0.1})
        ]
    },
    {
        "id": 914,
        "name": "웨이니발",  # Quaquaval
        "types": [TYPE_NAMES["물"], TYPE_NAMES["격투"]],
        "stats": {"hp": 85, "atk": 120, "def": 80, "spa": 85, "spd": 75, "spe": 105},
        "moves": [
            Move("아쿠아스텝", TYPE_NAMES["물"], "Physical", 80, 100, 10, {"stat_change": "spe", "self_change": 1}),
            Move("웨이브태클", TYPE_NAMES["물"], "Physical", 120, 100, 5, {"recoil": 0.33}),
            Move("인파이트", TYPE_NAMES["격투"], "Physical", 120, 100, 5, {"self_stat_changes": {"def": -1, "spd": -1}}),
            Move("브레이브버드", TYPE_NAMES["비행"], "Physical", 120, 100, 5, {"recoil": 0.33})
        ]
    }
]

# 타입별 포켓몬 분류
FIRE_POKEMON = [p for p in POKEMON_TEMPLATES if PokemonType.FIRE in p["types"]]
WATER_POKEMON = [p for p in POKEMON_TEMPLATES if PokemonType.WATER in p["types"]]
GRASS_POKEMON = [p for p in POKEMON_TEMPLATES if PokemonType.GRASS in p["types"]]
OTHER_POKEMON = [p for p in POKEMON_TEMPLATES if PokemonType.FIRE not in p["types"] and
                                               PokemonType.WATER not in p["types"] and
                                               PokemonType.GRASS not in p["types"]] 

def create_pokemon_from_template(template):
    """Create a Pokémon from a template"""
    # 기술 목록을 깊은 복사하여 참조 문제 방지
    moves_copy = []
    for move in template["moves"]:
        # Move 객체 속성 복사
        move_copy = Move(
            move.name,
            move.type,
            move.category,
            move.power,
            move.accuracy,
            move.pp,  # 원본 PP 값 사용
            move.effects.copy() if move.effects else {}
        )
        move_copy.max_pp = move.max_pp
        if hasattr(move, 'battle_effects'):
            move_copy.battle_effects = move.battle_effects.copy()
        moves_copy.append(move_copy)

    return Pokemon(
        name=template["name"],
        types=template["types"],
        stats=template["stats"],
        moves=moves_copy,  # 복사된 기술 목록 사용
        level=50
    )