# utils/replay_buffer.py
import random
import numpy as np

class ReplayBuffer:
    def __init__(self, size):
        self.buffer = []
        self.max_size = size

    def push(self, transition):
        if len(self.buffer) >= self.max_size:
            self.buffer.pop(0)
        self.buffer.append(transition)

    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        return map(np.array, zip(*batch))