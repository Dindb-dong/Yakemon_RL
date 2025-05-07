"""포켓몬 클래스를 정의하는 모듈"""

import random
from .moves import Move
from .types import TYPE_NAMES

class Pokemon:
    """Pokémon class with level 50 stat adjustments"""
    def __init__(self, name, types, stats, moves, level=50):
        self.name = name
        self.types = types

        # Adjust stats for level 50
        self.stats = {
            'hp': stats['hp'] + 75,  # +75 HP for level 50
            'atk': stats['atk'] + 20,  # +25 for other stats at level 50
            'def': stats['def'] + 20,
            'spa': stats['spa'] + 20,
            'spd': stats['spd'] + 20,
            'spe': stats['spe'] + 20
        }

        self.moves = moves
        self.original_moves = moves.copy()  # 원본 기술 목록 저장
        self.level = level

        # Current state
        self.current_hp = self.stats['hp']
        self.status_condition = None  # None, 'Poison', 'Paralyze', 'Burn', 'Sleep', 'Freeze'
        self.status_counter = 0  # Counter for status conditions like sleep
        self.critical_hit_stage = 0  # 치명타 확률 단계 (0~3)
        self.stat_stages = {
            'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0,
            'accuracy': 0, 'evasion': 0
        }

        # 몸부림치기 기술 정의 (미리 생성)
        self.struggle_move = Move(
            "몸부림치기",
            TYPE_NAMES["노말"],  # Normal type
            "Physical",
            50,  # Fixed power
            100,  # 100% accuracy
            1,   # PP is set to 1
            {"recoil": 0.25}  # Has recoil damage
        )

        # 몸부림치기 추가 여부 플래그
        self.struggle_added = False

    def is_fainted(self):
        """Check if fainted"""
        return self.current_hp <= 0

    def calculate_stat(self, stat_name):
        """Calculate actual stat considering stat stages and status conditions"""
        if stat_name == 'hp':
            return self.stats['hp']

        base_stat = self.stats[stat_name]
        stage = self.stat_stages[stat_name]

        # Calculate multiplier based on stat stage (Pokémon formula)
        if stage >= 0:
            multiplier = (2 + stage) / 2
        else:
            multiplier = 2 / (2 - stage)

        # Apply status condition effects
        if self.status_condition == 'Paralyze' and stat_name == 'spe':
            # Paralysis reduces speed by 50%
            multiplier *= 0.5
        elif self.status_condition == 'Burn' and stat_name == 'atk':
            # Burn reduces attack by 50%
            multiplier *= 0.5

        return int(base_stat * multiplier)

    def can_move(self):
        """Check if the Pokemon can move based on status condition"""
        if self.status_condition == 'Paralyze':
            # 25% chance of not being able to move when paralyzed
            return random.random() > 0.25
        elif self.status_condition == 'Sleep':
            # Can't move while asleep
            return False
        elif self.status_condition == 'Freeze':
            # 20% chance to thaw each turn
            if random.random() < 0.2:
                self.status_condition = None
                return True
            return False
        return True

    def apply_status_turn_end(self):
        """Apply status condition effects at the end of a turn"""
        effects = []

        if self.status_condition == 'Poison':
            # Poison damage: 1/8 of max HP
            damage = max(1, self.stats['hp'] // 8)
            self.current_hp = max(0, self.current_hp - damage)
            effects.append(f"{self.name}은(는) 독 데미지를 입었다! (-{damage} HP)")

        elif self.status_condition == 'Burn':
            # Burn damage: 1/16 of max HP
            damage = max(1, self.stats['hp'] // 16)
            self.current_hp = max(0, self.current_hp - damage)
            effects.append(f"{self.name}은(는) 화상 데미지를 입었다! (-{damage} HP)")

        elif self.status_condition == 'Sleep':
            # Sleep counter
            self.status_counter += 1
            # Sleep lasts 1-3 turns
            if self.status_counter >= random.randint(1, 3):
                self.status_condition = None
                self.status_counter = 0
                effects.append(f"{self.name}은(는) 잠에서 깨어났다!")
            else:
                effects.append(f"{self.name}은(는) 계속 자고 있다...")

        return effects

    def get_valid_moves(self):
        """Return list of valid move indices with PP > 0"""
        valid_moves = [i for i, move in enumerate(self.moves) if i < len(self.moves) and move.pp > 0]

        if not valid_moves:
            # 이미 몸부림치기가 추가되어 있는지 확인
            struggle_index = None
            for i, move in enumerate(self.moves):
                if move.name == "몸부림치기":
                    struggle_index = i
                    # 몸부림치기의 PP 리셋 (소진될 수 없음)
                    move.pp = 1
                    break

            # 몸부림치기가 없으면 추가
            if struggle_index is None:
                self.moves.append(self.struggle_move)
                self.struggle_added = True
                struggle_index = len(self.moves) - 1

            return [struggle_index]

        return valid_moves

    def reset(self):
        """Reset Pokémon to full health and clear status conditions"""
        self.current_hp = self.stats['hp']
        self.status_condition = None
        self.status_counter = 0
        self.critical_hit_stage = 0  # 치명타 단계 초기화
        self.stat_stages = {
            'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0,
            'accuracy': 0, 'evasion': 0
        }

        # 몸부림치기가 추가되었으면 원본 기술로 복원
        if self.struggle_added:
            self.moves = self.original_moves.copy()
            self.struggle_added = False

        # Reset move PP
        for move in self.moves:
            move.pp = move.max_pp
            # 배틀 효과 초기화
            if hasattr(move, 'battle_effects'):
                move.battle_effects = {} 