"""Loads a saved PPO model and runs it in TORCS"""

import os
import torch
import numpy as np

import config
from ppo_model import ActorCritic
from torcs_env_wrapper import TorcsEnvWrapper


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def test(model_name):
    env = TorcsEnvWrapper()

    policy = ActorCritic().to(device)

    model_path = os.path.join(config.MODEL_SAVE_PATH, model_name)
    policy.load_state_dict(torch.load(model_path, map_location=device))
    policy.eval()

    state, raw_obs = env.reset(relaunch=True)

    total_reward = 0

    for step in range(config.MAX_STEPS):
        state_tensor = torch.tensor(state, dtype=torch.float32).to(device)

        with torch.no_grad():
            action = policy.actor(state_tensor)

        state, reward, done, info, raw_obs = env.step(action.cpu().numpy())

        total_reward += reward

        if done:
            break

    print(f"Test finished | Reward: {total_reward:.2f} | Steps: {step + 1}")

    env.close()


if __name__ == "__main__":
    test("ppo_torcs_episode_50.pth")