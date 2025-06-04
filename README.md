# Yakemon - Pokemon Battle AI Project ⚡

## What are we building?

This is a YAICON project where we're building **an AI that can beat humans at Pokemon battles**.
Our goal is simple but challenging: achieve 60%+ win rate against members of Yonsei's Pokemon club 'Pocenyeon' battle division. Pokemon battles might look simple, but they're incredibly complex - type matchups, status effects, stat changes, switching timing, probability calculations... there's a lot going on under the hood.

## Technical Approach

### Reinforcement Learning

- **Main Algorithm**: DDDQN (Dueling Double Deep Q-Network)
- **State Vector**: 1237 dimensions encoding every aspect of battle
- **Action Space**: 6 actions (4 moves + 2 switches, masking invalid actions)
- **Reward Function**: Complex strategic reward system

### Massive State-Space to represent the complexity of Pokemon battles

We went all-out on state representation to make sure our AI knows everything that's happening:

```python
# Battle global state: 51 dimensions
#   - Turn count: 1
#   - Weather effects (4 types × 6 one-hot): 24
#   - Field effects (4 types × 5 one-hot): 20
#   - Room effects (6 one-hot): 6

# Side field state (my + enemy): 52 dimensions
#   - Hazards: stealth rock, spikes, toxic spikes
#   - Screens: reflect, light screen, aurora veil

# Pokemon state (6 pokemon × 177 each): 1062 dimensions
#   - Species, ability, moves, PP
#   - Types, HP, stat boosts
#   - Status conditions, volatile effects
#   - Position, charging states, etc.

# Active Pokemon move types: 72 dimensions
# Total: 1237 dimensions
```

Every single piece of information that could affect battle decisions gets encoded.

### The Reward Function Hell

This was our biggest challenge. Started simple with "win = +10, lose = -10" but the AI just spammed healing moves and ignored type matchups.
This kind of sparse reward implementation did very bad in the early learning process, so we had to make a lot of adjustments.
As the implementation of our simulator took a long time, we didn't have enough time to analyze the total result of all of the changes, but we did our best to find the optimal reward manually.

We built a complex reward system that considers:

- **Type effectiveness**: Massive bonuses for super effective hits, penalties for resisted or immuned attacks
- **Strategic switching**: Rewards for good type matchups, penalties for switching into weaknesses type matchups
- **Status condition usage**: Penalties for using status moves on already-statused targets
- **Ability awareness**: Penalties for using moves that get nullified by abilities
- **Stat boosting timing**: Rewards for rank up move when faster than opponent
- **Damage dealing**: Scaled rewards based on damage percentage
- **Being Fainted**: Penalties for being fainted because of bad switch or attempt to use rank up moves, or just it.

```python
# Example reward calculations
was_effective = result.get('was_effective', 0)
was_null = result.get('was_null', False)
if was_effective == 2:  # 4x damage
    reward += 2.0
#####
was_effective = outcome.get('was_effective', 0)
was_null = outcome.get('was_null', False)
elif was_effective == -2:  # 1/4 damage
    reward += 0.6  # 매우 큰 보상
    if not is_monte_carlo:
        print(f"Good switch: Resistant to 1/4 damage! Reward: {reward}")
    else: print(f"Resistant to 1/4 damage! Reward: {reward}")
#####

```

## Running the Code

### Setup

```bash
git clone https://github.com/Dindb-dong/Yakemon_RL.git
cd Yakemon_RL
pip install -r requirements.txt
```

### Training

```bash
# Train DDDQN agent and Make a visualization and Test
python training_dqn.py
# You can use your own Hyperparams
```

### Key Files

```
yakemon/
├── env/battle_env.py              # Gym environment
├── RL/
│   ├── get_state_vector.py        # 1237-dim state creation
│   ├── reward_calculator.py       # Complex reward function
│   └── base_ai_choose_action.py   # base ai actions
├── agent/dddqn_agent.py           # DDDQN implementation
└── context/                       # Battle state management
```

## Challenges We Faced

### 1. Reward Sparsity

**Problem**: Win/loss rewards too sparse for learning  
**Solution**: Built detailed intermediate rewards for strategic play

### 2. State Complexity

**Problem**: 1237 dimensions is huge, hard to learn efficiently
**Solution**: Careful normalization and binning of continuous values

### 3. Opponent Too Strong

**Problem**: Rule-based AI too good for initial training
**Solution**: Curriculum learning and self-play approaches

### 4. Action Space Validity

**Problem**: Many actions invalid depending on game state  
**Solution**: Dynamic action masking system. However creating a standard, fixed action space would have been better perhaps.

### 5. Simulator Creation

**Problem**: We tried creating a custom environment, instead of the standard Poke-Env
**Solution**: We spent a lot of time trying to create an environment that replicated real Pokemon battles as closely as possible. Even though we couldn't implement items, we were able to safely implement an environment that does closely replicate a battle.
We had to spend too much time on this however, thus not allowing us too much time on the real training, evaluation process.

## Results and Interesting Discoveries

The AI is learning some cool behaviors:

- **Type matchup optimization**: Immediately switches out of bad matchups
- **Setup timing**: Uses stat boosts when faster than opponent
- **Ability awareness**: Avoids moves that get nullified
- **Hazard play**: Uses entry hazards strategically

## Team

- **김동욱**: Project lead, simulator integration
- **김재후**: RL algorithms, DDDQN implementation
- **박민우**: RL algorithms, early learning implementations
- **김현중**: Reward function design
