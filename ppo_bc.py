import torch as th
import torch.nn.functional as F
from gymnasium import spaces
from sb3_contrib.ppo_mask import MaskablePPO
from sb3_contrib.common.maskable.utils import get_action_masks, is_masking_supported
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from stable_baselines3.common.utils import explained_variance, get_schedule_fn, obs_as_tensor
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import VecEnv
import torch
import numpy as np

from rollout_buffer import MaskableRolloutBCBuffer

from RL.base_ai_choose_action import base_ai_choose_action
from context.battle_store import store
from p_models.battle_pokemon import BattlePokemon
from typing import Dict, Union, Optional

from p_models.move_info import MoveInfo
from context.battle_store import BattleStoreState, store


class MaskableBCActorCriticPolicy(MaskableActorCriticPolicy):
    def forward(
        self,
        obs: th.Tensor,
        deterministic: bool = False,
        action_masks: Optional[np.ndarray] = None,
    ) -> tuple[th.Tensor, th.Tensor, th.Tensor]:
        """
        Forward pass in all the networks (actor and critic)

        :param obs: Observation
        :param deterministic: Whether to sample or use deterministic actions
        :param action_masks: Action masks to apply to the action distribution
        :return: action, value and log probability of the action
        """
        # Preprocess the observation if needed
        features = self.extract_features(obs)
        if self.share_features_extractor:
            latent_pi, latent_vf = self.mlp_extractor(features)
        else:
            pi_features, vf_features = features
            latent_pi = self.mlp_extractor.forward_actor(pi_features)
            latent_vf = self.mlp_extractor.forward_critic(vf_features)
        # Evaluate the values for the given observations
        values = self.value_net(latent_vf)
        distribution = self._get_action_dist_from_latent(latent_pi)
        if action_masks is not None:
            distribution.apply_masking(action_masks)
        actions = distribution.get_actions(deterministic=deterministic)
        log_prob = distribution.log_prob(actions)
        return actions, values, log_prob
    
class MaskablePPOBC(MaskablePPO):
    """
    MaskablePPO + Behavior Cloning(BC) loss.
    BC loss는 base_ai_choose_action()의 행동과 policy의 행동을 비교하여 추가 loss로 사용.
    """
    policy: MaskableBCActorCriticPolicy
    rollout_buffer: MaskableRolloutBCBuffer

    def _setup_model(self) -> None:
        self._setup_lr_schedule()
        self.set_random_seed(self.seed)

        self.policy = self.policy_class(  # type: ignore[assignment]
            self.observation_space,
            self.action_space,
            self.lr_schedule,
            **self.policy_kwargs,
        )
        self.policy = self.policy.to(self.device)

        if not isinstance(self.policy, MaskableActorCriticPolicy):
            raise ValueError("Policy must subclass MaskableActorCriticPolicy")

        # 여기서 반드시 MaskableRolloutBCBuffer로 할당
        from rollout_buffer import MaskableRolloutBCBuffer
        self.rollout_buffer_class = MaskableRolloutBCBuffer

        self.rollout_buffer = self.rollout_buffer_class(  # type: ignore[assignment]
            self.n_steps,
            self.observation_space,
            self.action_space,
            self.device,
            gamma=self.gamma,
            gae_lambda=self.gae_lambda,
            n_envs=self.n_envs,
            **self.rollout_buffer_kwargs,
        )

        # Initialize schedules for policy/value clipping
        self.clip_range = get_schedule_fn(self.clip_range)
        if self.clip_range_vf is not None:
            if isinstance(self.clip_range_vf, (float, int)):
                assert self.clip_range_vf > 0, "`clip_range_vf` must be positive, " "pass `None` to deactivate vf clipping"

            self.clip_range_vf = get_schedule_fn(self.clip_range_vf)

    def collect_rollouts(
        self,
        env: VecEnv,
        callback: BaseCallback,
        rollout_buffer: MaskableRolloutBCBuffer,
        n_rollout_steps: int,
        use_masking: bool = True,
    ) -> bool:
        assert isinstance(
            rollout_buffer, MaskableRolloutBCBuffer
        ), "RolloutBuffer doesn't support action masking"
        assert self._last_obs is not None, "No previous observation was provided"
        # Switch to eval mode (this affects batch norm / dropout)
        self.policy.set_training_mode(False)
        n_steps = 0
        action_masks = None
        rollout_buffer.reset()

        if use_masking and not is_masking_supported(env):
            raise ValueError("Environment does not support action masking. Consider using ActionMasker wrapper")

        callback.on_rollout_start()

        while n_steps < n_rollout_steps:
            with th.no_grad():
                # Convert to pytorch tensor or to TensorDict
                obs_tensor = obs_as_tensor(self._last_obs, self.device)

                # This is the only change related to invalid action masking
                if use_masking:
                    action_masks = get_action_masks(env)

                actions, values, log_probs = self.policy(obs_tensor, action_masks=action_masks)

            actions = actions.cpu().numpy()
            new_obs, rewards, dones, infos = env.step(actions)

            # Get base ai action for BC loss
            def get_action_int(action: MoveInfo | Dict[str, Union[str, int]], pokemon: BattlePokemon):
                if isinstance(action, dict):
                    state: BattleStoreState = store.get_state()
                    active_my = state["active_my"]
                    if active_my == 0:
                        return action['index'] - 1 + 4
                    elif active_my == 1:
                        if action['index'] == 0:
                            return 4
                        elif action['index'] == 2:
                            return 5
                        else:
                            raise ValueError(f"Invalid action index: {action['index']}")
                    elif active_my == 2:
                        return action['index'] + 4
                    else:
                        raise ValueError(f"Invalid active_my: {active_my}")
                else: 
                    for i, move in enumerate(pokemon.base.moves):
                        if move.name == action.name:
                            return i
                    raise ValueError(f"Invalid move name: {action.name}")

            # 환경에서 필요한 정보 추출
            # (env가 VecEnv일 경우, 아래 코드는 단일 env에만 맞춰져 있음. 병렬 환경이면 수정 필요)
            base_ai_action = 0
            if hasattr(env, 'envs'):
                # VecEnv의 경우 env.envs[0] 사용 (단일 환경만 지원)
                single_env = env.envs[0].env
                temp_action = base_ai_choose_action(
                    side="my",
                    my_team=single_env.my_team,
                    enemy_team=single_env.enemy_team,
                    active_my=single_env.battle_store.get_active_index("my"),
                    active_enemy=single_env.battle_store.get_active_index("enemy"),
                    public_env=single_env.public_env.__dict__,
                    enemy_env=single_env.my_env.__dict__,
                    my_env=single_env.enemy_env.__dict__,
                    add_log=single_env.battle_store.add_log
                )
                base_ai_action = get_action_int(temp_action, single_env.my_team[single_env.battle_store.get_active_index("my")])
            elif hasattr(env, 'my_team'):
                # 일반 환경
                temp_action = base_ai_choose_action(
                    side="my",
                    my_team=env.my_team,
                    enemy_team=env.enemy_team,
                    active_my=env.battle_store.get_active_index("my"),
                    active_enemy=env.battle_store.get_active_index("enemy"),
                    public_env=env.public_env.__dict__,
                    enemy_env=env.my_env.__dict__,
                    my_env=env.enemy_env.__dict__,
                    add_log=env.battle_store.add_log
                )
                base_ai_action = get_action_int(temp_action, env.my_team[env.battle_store.get_active_index("my")])

            self.num_timesteps += env.num_envs

            # Give access to local variables
            callback.update_locals(locals())
            if not callback.on_step():
                return False

            self._update_info_buffer(infos, dones)
            n_steps += 1

            if isinstance(self.action_space, spaces.Discrete):
                # Reshape in case of discrete action
                actions = actions.reshape(-1, 1)

            # Handle timeout by bootstraping with value function
            # see GitHub issue #633
            for idx, done in enumerate(dones):
                if (
                    done
                    and infos[idx].get("terminal_observation") is not None
                    and infos[idx].get("TimeLimit.truncated", False)
                ):
                    terminal_obs = self.policy.obs_to_tensor(infos[idx]["terminal_observation"])[0]
                    with th.no_grad():
                        terminal_value = self.policy.predict_values(terminal_obs)[0]
                    rewards[idx] += self.gamma * terminal_value

            rollout_buffer.add(
                self._last_obs,
                actions,
                rewards,
                self._last_episode_starts,
                values,
                log_probs,
                action_masks=action_masks,
                expert_action=base_ai_action,
            )
            self._last_obs = new_obs  # type: ignore[assignment]
            self._last_episode_starts = dones

        with th.no_grad():
            # Compute value for the last timestep
            # Masking is not needed here, the choice of action doesn't matter.
            # We only want the value of the current observation.
            values = self.policy.predict_values(obs_as_tensor(new_obs, self.device))  # type: ignore[arg-type]

        rollout_buffer.compute_returns_and_advantage(last_values=values, dones=dones)

        callback.on_rollout_end()

        return True

    def train(self) -> None:
        """
        Update policy using the currently gathered rollout buffer.
        """
        # Switch to train mode (this affects batch norm / dropout)
        self.policy.set_training_mode(True)
        # Update optimizer learning rate
        self._update_learning_rate(self.policy.optimizer)
        # Compute current clip range
        clip_range = self.clip_range(self._current_progress_remaining)  # type: ignore[operator]
        # Optional: clip range for the value function
        if self.clip_range_vf is not None:
            clip_range_vf = self.clip_range_vf(self._current_progress_remaining)  # type: ignore[operator]

        entropy_losses = []
        pg_losses, value_losses, bc_losses = [], [], []
        clip_fractions = []

        continue_training = True

        # train for n_epochs epochs
        for epoch in range(self.n_epochs):
            approx_kl_divs = []
            # Do a complete pass on the rollout buffer
            for rollout_data in self.rollout_buffer.get(self.batch_size):
                actions = rollout_data.actions
                if isinstance(self.action_space, spaces.Discrete):
                    # Convert discrete action from float to long
                    actions = rollout_data.actions.long().flatten()

                values, log_prob, entropy = self.policy.evaluate_actions(
                    rollout_data.observations,
                    actions,
                    action_masks=rollout_data.action_masks,
                )

                values = values.flatten()
                # Normalize advantage
                advantages = rollout_data.advantages
                if self.normalize_advantage:
                    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

                # ratio between old and new policy, should be one at the first iteration
                ratio = th.exp(log_prob - rollout_data.old_log_prob)

                # clipped surrogate loss
                policy_loss_1 = advantages * ratio
                policy_loss_2 = advantages * th.clamp(ratio, 1 - clip_range, 1 + clip_range)
                policy_loss = -th.min(policy_loss_1, policy_loss_2).mean()

                # Logging
                pg_losses.append(policy_loss.item())
                clip_fraction = th.mean((th.abs(ratio - 1) > clip_range).float()).item()
                clip_fractions.append(clip_fraction)

                if self.clip_range_vf is None:
                    # No clipping
                    values_pred = values
                else:
                    # Clip the different between old and new value
                    # NOTE: this depends on the reward scaling
                    values_pred = rollout_data.old_values + th.clamp(
                        values - rollout_data.old_values, -clip_range_vf, clip_range_vf
                    )
                # Value loss using the TD(gae_lambda) target
                value_loss = F.mse_loss(rollout_data.returns, values_pred)
                value_losses.append(value_loss.item())

                # ----------- BC loss -----------
                log_prob = self.policy.forward(rollout_data.observations, action_masks=rollout_data.action_masks)[-1]
                print(log_prob.shape, rollout_data.expert_actions.shape)
                bc_loss = -log_prob[rollout_data.expert_actions.view(-1)].mean()
                bc_losses.append(bc_loss.item())
                # ----------- BC loss 끝 -----------

                # Entropy loss favor exploration
                if entropy is None:
                    # Approximate entropy when no analytical form
                    entropy_loss = -th.mean(-log_prob)
                else:
                    entropy_loss = -th.mean(entropy)

                entropy_losses.append(entropy_loss.item())

                # 최종 loss: 기존 loss + bc_loss (가중치는 1.0, 필요시 조정)
                loss = policy_loss + self.ent_coef * entropy_loss + self.vf_coef * value_loss + bc_loss
                print(f"Epoch {epoch}, Loss: {loss.item()}, Policy Loss: {policy_loss.item()}, Entropy Loss: {entropy_loss.item()}, Value Loss: {value_loss.item()}, BC Loss: {bc_loss.item()}")
                print(f"Adjusted Policy Loss: {policy_loss.item()}, Entropy Loss: {entropy_loss.item() * self.ent_coef}, Value Loss: {value_loss.item() * self.vf_coef}, BC Loss: {bc_loss.item()}")

                # Calculate approximate form of reverse KL Divergence for early stopping
                # see issue #417: https://github.com/DLR-RM/stable-baselines3/issues/417
                # and discussion in PR #419: https://github.com/DLR-RM/stable-baselines3/pull/419
                # and Schulman blog: http://joschu.net/blog/kl-approx.html
                with th.no_grad():
                    log_ratio = log_prob - rollout_data.old_log_prob
                    approx_kl_div = th.mean((th.exp(log_ratio) - 1) - log_ratio).cpu().numpy()
                    approx_kl_divs.append(approx_kl_div)

                if self.target_kl is not None and approx_kl_div > 1.5 * self.target_kl:
                    continue_training = False
                    if self.verbose >= 1:
                        print(f"Early stopping at step {epoch} due to reaching max kl: {approx_kl_div:.2f}")
                    break

                # Optimization step
                self.policy.optimizer.zero_grad()
                loss.backward()
                # Clip grad norm
                th.nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
                self.policy.optimizer.step()

            if not continue_training:
                break

        self._n_updates += self.n_epochs
        explained_var = explained_variance(self.rollout_buffer.values.flatten(), self.rollout_buffer.returns.flatten())

        # Logs
        self.logger.record("train/entropy_loss", np.mean(entropy_losses))
        self.logger.record("train/policy_gradient_loss", np.mean(pg_losses))
        self.logger.record("train/value_loss", np.mean(value_losses))
        self.logger.record("train/bc_loss", np.mean(bc_losses))  # BC loss 로깅 추가
        self.logger.record("train/approx_kl", np.mean(approx_kl_divs))
        self.logger.record("train/clip_fraction", np.mean(clip_fractions))
        self.logger.record("train/loss", loss.item())
        self.logger.record("train/explained_variance", explained_var)
        self.logger.record("train/n_updates", self._n_updates, exclude="tensorboard")
        self.logger.record("train/clip_range", clip_range)
        if self.clip_range_vf is not None:
            self.logger.record("train/clip_range_vf", clip_range_vf)
