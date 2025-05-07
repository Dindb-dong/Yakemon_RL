"""포켓몬 팀 클래스를 정의하는 모듈"""

class PokemonTeam:
    """Pokémon team class"""
    def __init__(self, pokemons):
        self.pokemons = pokemons
        self.active_pokemon_index = 0

    @property
    def active_pokemon(self):
        """Currently active Pokémon"""
        return self.pokemons[self.active_pokemon_index]

    def switch_pokemon(self, index):
        """Switch Pokémon"""
        if 0 <= index < len(self.pokemons) and not self.pokemons[index].is_fainted() and index != self.active_pokemon_index:
            self.active_pokemon_index = index
            return True
        return False

    def all_fainted(self):
        """Check if all Pokémon are fainted"""
        return all(pokemon.is_fainted() for pokemon in self.pokemons)

    def get_first_non_fainted(self):
        """Get index of first non-fainted Pokémon"""
        for i, pokemon in enumerate(self.pokemons):
            if not pokemon.is_fainted():
                return i
        return -1  # All fainted

    def get_valid_switches(self):
        """Get list of valid switch indices"""
        return [i for i, pokemon in enumerate(self.pokemons)
                if i != self.active_pokemon_index and not pokemon.is_fainted()]

    def reset(self):
        """Reset all Pokémon in the team"""
        for pokemon in self.pokemons:
            pokemon.reset()

        # Set active Pokémon to first one
        first_index = self.get_first_non_fainted()
        if first_index != -1:
            self.active_pokemon_index = first_index 