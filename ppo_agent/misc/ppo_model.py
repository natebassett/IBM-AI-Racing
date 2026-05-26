"""Neural network: actor + critic"""

import torch
import torch.nn as nn
from torch.distributions import MultivariateNormal

import config


class ActorCritic(nn.Module):
    def __init__(self):
        super().__init__()

        self.actor = nn.Sequential(
            nn.Linear(config.STATE_DIM, 128),
            nn.Tanh(),
            nn.Linear(128, 128),
            nn.Tanh(),
            nn.Linear(128, config.ACTION_DIM),
            nn.Tanh()
        )

        self.critic = nn.Sequential(
            nn.Linear(config.STATE_DIM, 128),
            nn.Tanh(),
            nn.Linear(128, 128),
            nn.Tanh(),
            nn.Linear(128, 1)
        )

        self.action_var = torch.full(
            (config.ACTION_DIM,),
            config.ACTION_STD_INIT ** 2
        )

    def set_action_std(self, new_std):
        self.action_var = torch.full(
            (config.ACTION_DIM,),
            new_std ** 2
        )

    def act(self, state):
        action_mean = self.actor(state)

        cov_matrix = torch.diag(self.action_var).to(state.device)
        dist = MultivariateNormal(action_mean, cov_matrix)

        action = dist.sample()
        log_prob = dist.log_prob(action)
        value = self.critic(state)

        return action.detach(), log_prob.detach(), value.detach()

    def evaluate(self, states, actions):
        action_mean = self.actor(states)

        action_var = self.action_var.expand_as(action_mean).to(states.device)
        cov_matrix = torch.diag_embed(action_var)

        dist = MultivariateNormal(action_mean, cov_matrix)

        log_probs = dist.log_prob(actions)
        entropy = dist.entropy()
        values = self.critic(states).squeeze()

        return log_probs, values, entropy