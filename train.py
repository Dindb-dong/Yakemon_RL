# train.py
from env.battle_env import YakemonEnv
from agent.dddqn_agent import DDDQNAgent
from utils.replay_buffer import ReplayBuffer

env = YakemonEnv()
state_dim = env.get_state().shape[0]
action_dim = 4 + 2  # 기본 4 + 교체 2 (대충)

agent = DDDQNAgent(state_dim, action_dim)
buffer = ReplayBuffer(10000)

episodes = 500
batch_size = 32

for episode in range(episodes):
    state = env.reset()
    total_reward = 0
    done = False
    epsilon = max(0.01, 0.1 - 0.01*(episode/100))

    while not done:
        action = agent.select_action(state, epsilon)
        next_state, reward, done, _ = env.step(action)
        buffer.push((state, action, reward, next_state, done))
        state = next_state
        total_reward += reward

        if len(buffer.buffer) >= batch_size:
            agent.update(buffer.sample(batch_size))

    if episode % 10 == 0:
        print(f"Episode {episode} - Total Reward: {total_reward}")