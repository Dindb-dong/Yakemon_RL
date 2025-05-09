# env/mock_pokemon.py
def create_mock_pokemon_list():
    pokemon_list = []
    for i in range(27):
        pokemon = {
            'currentHp': 100,
            'base': {
                'hp': 100,
                'types': [['물', '불', '풀'][i % 3]],
                'attack': 50 + (i % 10),
                'defense': 50 + (i % 10),
                'spAttack': 50 + (i % 10),
                'spDefense': 50 + (i % 10),
                'speed': 50 + (i % 10),
                'moves': [
                    {'name': f'기술{i%4}', 'pp': 20},
                    {'name': f'기술{(i+1)%4}', 'pp': 20}
                ]
            },
            'status': [],
            'rank': {
                'attack': 0,
                'defense': 0,
                'spAttack': 0,
                'spDefense': 0,
                'speed': 0,
                'accuracy': 0,
                'dodge': 0
            },
            'pp': {},
            'position': '없음',
            'is_active': False,
            'locked_move': {'id': 0},
            'locked_move_turn': 0,
            'is_protecting': False,
            'used_move': {'id': 0},
            'had_missed': False,
            'had_rank_up': False,
            'is_charging': False,
            'charging_move': {'id': 0},
            'received_damage': 0,
            'is_first_turn': False,
            'cannot_move': False,
            'un_usable_move': {'id': 0},
            'temp_type': None
        }
        pokemon_list.append(pokemon)
    return pokemon_list