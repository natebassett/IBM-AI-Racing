"""Main training script"""

import os
import csv
import torch
import numpy as np
import torch.nn as nn
import torch.optim as optim

import config
from ppo_model import ActorCritic
from ppo_memory import PPOMemory
from torcs_env_wrapper import TorcsEnvWrapper


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def compute_returns_and_advantages(memory):
    rewards = []
    discounted_reward = 0

    for reward, done in zip(reversed(memory.rewards), reversed(memory.dones)):
        if done:
            discounted_reward = 0
        discounted_reward = reward + config.GAMMA * discounted_reward
        rewards.insert(0, discounted_reward)

    rewards = torch.tensor(rewards, dtype=torch.float32).to(device)
    values = torch.cat(memory.values).squeeze().to(device)

    advantages = rewards - values.detach()

    if len(advantages) > 1:
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

    return rewards, advantages


def update_policy(policy, old_policy, optimizer, memory):
    states = torch.tensor(np.array(memory.states), dtype=torch.float32).to(device)
    actions = torch.stack(memory.actions).to(device)
    old_log_probs = torch.stack(memory.log_probs).to(device)

    returns, advantages = compute_returns_and_advantages(memory)

    for _ in range(config.PPO_EPOCHS):
        log_probs, values, entropy = policy.evaluate(states, actions)

        ratios = torch.exp(log_probs - old_log_probs.detach())

        surrogate_1 = ratios * advantages
        surrogate_2 = torch.clamp(
            ratios,
            1 - config.CLIP_EPSILON,
            1 + config.CLIP_EPSILON
        ) * advantages

        actor_loss = -torch.min(surrogate_1, surrogate_2).mean()
        critic_loss = nn.MSELoss()(values, returns)
        entropy_bonus = entropy.mean()

        loss = actor_loss + 0.5 * critic_loss - 0.01 * entropy_bonus

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    old_policy.load_state_dict(policy.state_dict())


def save_log(log_file, episode, reward, steps):
    file_exists = os.path.exists(log_file)

    with open(log_file, "a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["episode", "reward", "steps"])

        writer.writerow([episode, reward, steps])


def train():
    os.makedirs(config.MODEL_SAVE_PATH, exist_ok=True)
    os.makedirs(config.LOG_PATH, exist_ok=True)

    env = TorcsEnvWrapper()

    policy = ActorCritic().to(device)
    old_policy = ActorCritic().to(device)
    old_policy.load_state_dict(policy.state_dict())

    optimizer = optim.Adam(policy.parameters(), lr=config.LEARNING_RATE)

    memory = PPOMemory()
    timestep = 0

    log_file = os.path.join(config.LOG_PATH, "ppo_training_log.csv")

    for episode in range(1, config.MAX_EPISODES + 1):
        relaunch = False

        state, raw_obs = env.reset(relaunch=False)

        episode_reward = 0

        for step in range(config.MAX_STEPS):
            state_tensor = torch.tensor(state, dtype=torch.float32).to(device)

            action, log_prob, value = old_policy.act(state_tensor)

            next_state, reward, done, info, raw_obs = env.step(action.cpu().numpy())

            memory.store(
                state,
                action.cpu(),
                log_prob.cpu(),
                reward,
                value.cpu(),
                done
            )

            state = next_state
            episode_reward += reward
            timestep += 1

            if timestep % config.UPDATE_TIMESTEPS == 0:
                update_policy(policy, old_policy, optimizer, memory)
                memory.clear()

            if done:
                if "failure_reason" in info:
                    print(f"Episode ended: {info['failure_reason']}")
                break

        save_log(log_file, episode, episode_reward, step + 1)

        print(f"Episode {episode} | Reward: {episode_reward:.2f} | Steps: {step + 1}")

        if episode % config.SAVE_INTERVAL == 0:
            model_path = os.path.join(
                config.MODEL_SAVE_PATH,
                f"ppo_torcs_episode_{episode}.pth"
            )

            torch.save(policy.state_dict(), model_path)
            print(f"Saved model: {model_path}")

    env.close()


if __name__ == "__main__":
    train()