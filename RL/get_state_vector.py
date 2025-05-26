import numpy as np
from typing import List, Dict

from context.battle_environment import IndividualBattleEnvironment, PublicBattleEnvironment
from context.duration_store import duration_store
from context.battle_store import BattleStore, BattleStoreState, store, SideType
from p_models.battle_pokemon import BattlePokemon

# =============================
# State Vector Length Calculation (Total: 1153)
#
# Battle global state:
#   turn: 1
#   weather (4 types × 6 one-hot): 24
#   field (4 types × 5 one-hot): 20
#   room (6 one-hot): 6
# => subtotal: 51
#
# Side field state (my, enemy):
#   (stealth rock:1 + spikes:4 + toxic spikes:3 + reflect:6 + light screen:6 + aurora veil:6) × 2 = 52
#  => subtotal: 51 + 52 = 103
#
# Pokemon state (my 3, enemy 3):
#   For each Pokemon:
#     species: 1
#     ability: 1
#     move: 4
#     move_pp: 4×5=20
#     type(s): 18
#     current hp fraction: 7
#     rank boost: 7×13=91
#     volatile effects: 8
#     status: 7
#     sleep counter: 4
#     first turn: 1
#     must recharge: 1
#     preparing: 1
#     charging move id: 1
#     active: 1
#     position: 5
#     locked move id: 1
#     last used move: 1
#     had missed: 1
#     had rank up: 1
#     received damage: 1
#     unusable move: 1
#   = 177 per Pokemon
#   6 Pokemon × 177 = 1062
#
# Total: 1 + 24 + 20 + 6 + 52 + 1062 = 1165
# =============================

# --- Utility functions ---
def one_hot(idx, length):
    arr = np.zeros(length, dtype=np.float32)
    if 0 <= idx < length:
        arr[idx] = 1.0
    return arr

def bin_hp_ratio(hp_ratio):
    # 7 bins: (0, 1/6, 2/6, ..., 6/6]
    bins = np.linspace(0, 1, 8)
    idx = np.digitize([hp_ratio], bins, right=True)[0] - 1
    return one_hot(idx, 7)

def bin_pp_ratio(pp, max_pp):
    # 5 bins: 0, (0~1/4), (1/4~2/4), (2/4~3/4), (3/4~1]
    if max_pp == 0:
        return one_hot(0, 5)
    ratio = pp / max_pp
    if ratio < 0.25:
        return one_hot(1, 5)
    elif ratio < 0.5:
        return one_hot(2, 5)
    elif ratio < 0.75:
        return one_hot(3, 5)
    else:
        return one_hot(4, 5)

def rank_one_hot(rank):
    # -6~+6 -> 13 one-hot
    idx = int(rank) + 6
    return one_hot(idx, 13)

def spikes_one_hot(n): # 압정뿌리기 횟수
    # 0~3중첩 -> 4 one-hot
    return one_hot(n, 4)

def toxic_spikes_one_hot(val):
    # 0: 없음, 1: 독압정, 2: 맹독압정
    return one_hot(val, 3)

def sleep_counter_one_hot(val):
    # 1~3턴, 0이면 [0,0,0,0]
    if val == 0:
        return np.zeros(4, dtype=np.float32)
    return one_hot(val, 4)

def position_one_hot(pos):
    # 없음, 하늘, 바다, 땅, 공허
    mapping = {"없음":0, "하늘":1, "바다":2, "땅":3, "공허":4}
    idx = mapping.get(pos, 0)
    return one_hot(idx, 5)

def type_one_hot(types):
    # 18개 타입 중 최대 2개 1
    arr = np.zeros(18, dtype=np.float32)
    type_map = {"노말":0, "불":1, "물":2, "풀":3, "전기":4, "얼음":5, "격투":6, "독":7, "땅":8, "비행":9, "에스퍼":10, "벌레":11, "바위":12, "고스트":13, "드래곤":14, "악":15, "강철":16, "페어리":17}
    for t in types:
        if t in type_map:
            arr[type_map[t]] = 1.0
    return arr

def weather_one_hot(turns, length=6):
    # 0: 없음, 1~5: 남은 턴
    arr = np.zeros(length, dtype=np.float32)
    if 1 <= turns <= 5:
        arr[turns] = 1.0
    else:
        arr[0] = 1.0
    return arr

def field_one_hot(field):
    # 그래스, 사이코, 미스트, 일렉트릭, 없음
    mapping = {"그래스필드":0, "사이코필드":1, "미스트필드":2, "일렉트릭필드":3, "없음":4}
    idx = mapping.get(field, 4)
    return one_hot(idx, 5)

def room_one_hot(turns, length=6): # 트릭룸
    # 0: 없음, 1~5: 남은 턴
    arr = np.zeros(length, dtype=np.float32)
    if 1 <= turns <= 5:
        arr[turns] = 1.0
    else:
        arr[0] = 1.0
    return arr

def reflect_one_hot(turns, length=6):
    # 0: 없음, 1~5: 남은 턴
    arr = np.zeros(length, dtype=np.float32)
    if 1 <= turns <= 5:
        arr[turns] = 1.0
    else:
        arr[0] = 1.0
    return arr

# --- Main state vector function ---
def get_pokemon_vector(pokemon: BattlePokemon, side: SideType) -> np.ndarray:
    vec = []
    # species (정수 / 1000.0)
    vec.append(pokemon.base.id / 1000.0 if hasattr(pokemon.base, 'id') else 0)
    # ability (정수 / 120.0, 첫번째 ability만)
    ab = pokemon.base.ability
    ab_id = ab.id if ab and hasattr(ab, 'id') else 0
    vec.append(ab_id / 120.0)
    # move (정수 / 253.0, 4개)
    for i in range(4):
        if i < len(pokemon.base.moves):
            vec.append(pokemon.base.moves[i].id / 253.0)
        else:
            vec.append(0)
    # move_pp (4x5 one-hot)
    for i in range(4):
        if i < len(pokemon.base.moves):
            move = pokemon.base.moves[i]
            pp = pokemon.pp.get(move.name, 0)
            vec.extend(bin_pp_ratio(pp, move.pp))
        else:
            vec.extend(one_hot(0, 5))
    # type(s) (18 one-hot)
    vec.extend(type_one_hot(pokemon.base.types))
    # current hp fraction (7 one-hot)
    hp_ratio = pokemon.current_hp / pokemon.base.hp if pokemon.base.hp > 0 else 0
    vec.extend(bin_hp_ratio(hp_ratio))
    # rank boost (7x13 one-hot)
    for stat in ['attack','defense','sp_attack','sp_defense','speed','accuracy','dodge']:
        rank = pokemon.rank.get(stat, 0)
        vec.extend(rank_one_hot(rank))
    # volatile effects (8)
    vfx = ['혼란','풀죽음','사슬묶기','소리기술사용불가','하품','교체불가','조이기','멸망의노래']
    for eff in vfx:
        vec.append(1.0 if eff in pokemon.status else 0.0)
    # status (7)
    sfx = ['독','맹독','마비','화상','잠듦','얼음','기절']
    for eff in sfx:
        if eff == '기절':
            vec.append(1.0 if pokemon.current_hp == 0 else 0.0)
        else:
            vec.append(1.0 if eff in pokemon.status else 0.0)
    # sleep counter (4 one-hot)
    sleep_list = duration_store.get_effects(side)
    sleep_effect = next((e for e in sleep_list if e.name == "잠듦"), None)
    vec.extend(sleep_counter_one_hot(sleep_effect.remaining_turn if sleep_effect else 0))
    # first turn (1)
    vec.append(1.0 if pokemon.is_first_turn else 0.0)
    # must recharge (1)
    vec.append(1.0 if pokemon.cannot_move else 0.0)
    # preparing (1)
    vec.append(1.0 if pokemon.is_charging else 0.0)
    # charging move id (1)
    charging_move = pokemon.charging_move.id if pokemon.charging_move else 254
    vec.append(charging_move)
    # active (1)
    vec.append(1.0 if pokemon.is_active else 0.0)
    # position (5 one-hot)
    pos = pokemon.position if pokemon.position else '없음'
    vec.extend(position_one_hot(pos))
    # locked move id (1)
    locked_move = pokemon.locked_move.id if pokemon.locked_move else 254
    vec.append(locked_move)
    # last used move (1)
    used_move = pokemon.used_move.id if pokemon.used_move else 254
    vec.append(used_move)
    # had missed (1)
    vec.append(1.0 if pokemon.had_missed else 0.0)
    # had rank up (1)
    vec.append(1.0 if pokemon.had_rank_up else 0.0)
    # received damage (1)
    damage = pokemon.received_damage if pokemon.received_damage is not None else 0
    vec.append(1.0 if damage > 0 else 0.0)
    # unusable move (1)
    unusable_move = pokemon.un_usable_move.id if pokemon.un_usable_move else 254
    vec.append(unusable_move)
    # get_pokemon_vector 마지막에
    #print(f"Pokemon vector length: {len(vec)}")
    return np.array(vec, dtype=np.float32)

def get_side_field_vector(side: SideType) -> np.ndarray:
    vec = []
    state: BattleStoreState = store.get_state()
    side_env: IndividualBattleEnvironment = state["my_env"] if side == "my" else state["enemy_env"]
    # stealth rock (1)
    vec.append(1.0 if "스텔스록" in side_env.trap else 0.0)
    # spikes (4 one-hot)
    spikes = 0
    if "압정뿌리기" in side_env.trap:
        spikes = 1
    elif "압정뿌리기2" in side_env.trap:
        spikes = 2
    elif "압정뿌리기3" in side_env.trap:
        spikes = 3
    vec.extend(spikes_one_hot(spikes))
    # toxic spikes (3 one-hot)
    toxic_spikes = 0
    if "독압정" in side_env.trap:
        toxic_spikes = 1
    elif "맹독압정" in side_env.trap:
        toxic_spikes = 2
    vec.extend(toxic_spikes_one_hot(toxic_spikes))
    sc_list = duration_store.get_effects(side)
    reflect_effect = next((e for e in sc_list if e.name == "리플렉터"), None)
    screen_effect = next((e for e in sc_list if e.name == "빛의장막"), None)
    veil_effect = next((e for e in sc_list if e.name == "오로라베일"), None)
    # reflect (6 one-hot)
    vec.extend(reflect_one_hot(reflect_effect.remaining_turn if reflect_effect else 0))
    # light screen (6 one-hot)
    vec.extend(reflect_one_hot(screen_effect.remaining_turn if screen_effect else 0))
    # aurora veil (6 one-hot)
    vec.extend(reflect_one_hot(veil_effect.remaining_turn if veil_effect else 0))
    #print(f"Side field vector length: {len(vec)}")
    return np.array(vec, dtype=np.float32)

def get_state(
    store: BattleStore,
    my_team: List[BattlePokemon],
    enemy_team: List[BattlePokemon],
    active_my: int,
    active_enemy: int,
    public_env: PublicBattleEnvironment,
    my_env: IndividualBattleEnvironment,
    enemy_env: IndividualBattleEnvironment,
    turn: int,
    my_effects: List[Dict],
    enemy_effects: List[Dict],
    for_opponent: bool = False
) -> np.ndarray:
    vec = []
    # --- Battle global state ---
    # turn (1)
    vec.append(min(turn, 30) / 30.0)
    # weather (4종 × 6 one-hot)
    for w in ['쾌청','비','모래바람','싸라기눈']:
        if getattr(public_env, 'weather', None) == w:
            turns = 0
            for effect in duration_store.get_effects('public'):
                if getattr(effect, 'name', None) == w:
                    turns = getattr(effect, 'remaining_turn', 0)
                    break
            vec.extend(weather_one_hot(turns))
        else:
            vec.extend(weather_one_hot(0))
    # field (4종 × 5 one-hot)
    for f in ['그래스필드','사이코필드','미스트필드','일렉트릭필드']:
        if getattr(public_env, 'field', None) == f:
            vec.extend(field_one_hot(f))
        else:
            vec.extend(field_one_hot('없음'))
    # room (6 one-hot)
    room_turns = 0
    if getattr(public_env, 'room', None) == '트릭룸':
        for effect in duration_store.get_effects('public'):
            if getattr(effect, 'name', None) == '트릭룸':
                room_turns = getattr(effect, 'remaining_turn', 0)
                break
    vec.extend(room_one_hot(room_turns))
    # --- Side field state (my, enemy) ---
    vec.extend(get_side_field_vector('my'))
    vec.extend(get_side_field_vector('enemy'))
    # --- Pokemon state (my 3, enemy 3) ---
    for i in range(3):
        vec.extend(get_pokemon_vector(my_team[i], "my") if i < len(my_team) else np.zeros_like(get_pokemon_vector(BattlePokemon(), "my")))
    for i in range(3):
        vec.extend(get_pokemon_vector(enemy_team[i], "enemy") if i < len(enemy_team) else np.zeros_like(get_pokemon_vector(BattlePokemon(), "enemy")))
    # get_state 마지막에
    #print(f"Total state vector length: {len(vec)}")
    return np.array(vec, dtype=np.float32) 