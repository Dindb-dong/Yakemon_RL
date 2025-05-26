import numpy as np
import torch as th
from sb3_contrib.common.maskable.buffers import MaskableRolloutBuffer, MaskableRolloutBufferSamples
from gymnasium import spaces
from typing import NamedTuple

class MaskableRolloutBCBufferSamples(NamedTuple):
    observations: th.Tensor
    actions: th.Tensor
    old_values: th.Tensor
    old_log_prob: th.Tensor
    advantages: th.Tensor
    returns: th.Tensor
    action_masks: th.Tensor
    expert_actions: th.Tensor

class MaskableRolloutBCBuffer(MaskableRolloutBuffer):
    """
    Maskable Rollout Buffer that also stores expert actions for BC loss.
    """
    def reset(self) -> None:
        super().reset()
        # expert_actions shape: (buffer_size, n_envs)
        self.expert_actions = np.zeros((self.buffer_size, self.n_envs), dtype=np.int64)

    def add(self, *args, expert_action=None, **kwargs) -> None:
        """
        :param expert_action: The expert (base AI) action for BC loss.
        """
        if expert_action is not None:
            # 지원: 벡터/스칼라 모두
            if isinstance(expert_action, (list, np.ndarray)):
                self.expert_actions[self.pos] = np.array(expert_action)
            else:
                self.expert_actions[self.pos] = expert_action
        else:
            # 기본값: 0
            self.expert_actions[self.pos] = 0
        super().add(*args, **kwargs)

    def get(self, batch_size=None):
        assert self.full, ""
        indices = np.random.permutation(self.buffer_size * self.n_envs)
        # Prepare the data
        if not self.generator_ready:
            for tensor in [
                "observations",
                "actions",
                "values",
                "log_probs",
                "advantages",
                "returns",
                "action_masks",
                "expert_actions",
            ]:
                self.__dict__[tensor] = self.swap_and_flatten(self.__dict__[tensor])
            self.generator_ready = True

        if batch_size is None:
            batch_size = self.buffer_size * self.n_envs

        start_idx = 0
        while start_idx < self.buffer_size * self.n_envs:
            yield self._get_samples(indices[start_idx : start_idx + batch_size])
            start_idx += batch_size

    def _get_samples(self, batch_inds, env=None):
        # 기존 MaskableRolloutBufferSamples + expert_actions 추가
        data = (
            self.observations[batch_inds],
            self.actions[batch_inds],
            self.values[batch_inds].flatten(),
            self.log_probs[batch_inds].flatten(),
            self.advantages[batch_inds].flatten(),
            self.returns[batch_inds].flatten(),
            self.action_masks[batch_inds].reshape(-1, self.mask_dims),
            self.expert_actions[batch_inds],
        )
        return MaskableRolloutBCBufferSamples(*map(self.to_torch, data))
