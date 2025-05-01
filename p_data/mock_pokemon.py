# env/mock_pokemon.py
def create_mock_pokemon_list():
    pokemon_list = []
    for i in range(27):
        pokemon = {
            'name': f'포켓몬{i}',
            'types': ['물', '불', '풀'][i % 3],
            'hp': 100,
            'attack': 50 + (i % 10),
            'defense': 50 + (i % 10),
            'spAttack': 50 + (i % 10),
            'spDefense': 50 + (i % 10),
            'speed': 50 + (i % 10),
            'status': [],
            'moves': [f'기술{i%4}', f'기술{(i+1)%4}'],
            'ability': '특성A',
            'unUsableMove': None
        }
        pokemon_list.append(pokemon)
    return pokemon_list