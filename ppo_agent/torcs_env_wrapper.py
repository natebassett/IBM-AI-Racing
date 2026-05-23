"""Connects PPO to gym_torcs and cleans up observations/actions."""

import os
import sys

sys.path.append(os.path.abspath("../RaceYourCode/gym_torcs"))

import numpy as np
from gym_torcs import TorcsEnv

from reward_function import calculate_reward


class TorcsEnvWrapper:
    def __init__(self):
        self.env = TorcsEnv(
            vision=False,
            throttle=True,
            gear_change=False,
        )

        self.previous_damage = 0.0
        self.stuck_steps = 0

    def reset(self, relaunch=False):
        self.env.reset(relaunch=False)

        raw_obs = self.env.client.S.d

        self.previous_damage = self.get_value(raw_obs, "damage")
        self.stuck_steps = 0

        state = self.process_obs(raw_obs)

        return state, raw_obs

    def step(self, action):
        steer = float(np.clip(action[0], -1.0, 1.0))
        accel = float(np.clip(action[1], 0.0, 1.0))
        brake = float(np.clip(action[2], 0.0, 1.0))

        torcs_action = np.array([steer, accel, brake], dtype=np.float32)

        _, _, done, info = self.env.step(torcs_action)

        raw_obs = self.env.client.S.d

        reward = calculate_reward(raw_obs)
        failure, failure_reason = self.check_failure(raw_obs)

        if failure:
            reward -= 500.0
            done = True
            info["failure_reason"] = failure_reason

        state = self.process_obs(raw_obs)

        return state, reward, done, info, raw_obs
    
    def check_failure(self, obs):
        speed_x = self.get_value(obs, "speedX")
        angle = self.get_value(obs, "angle")
        track_pos = self.get_value(obs, "trackPos")
        damage = self.get_value(obs, "damage")

        if abs(track_pos) > 1.0:
            return True, "off_track"

        if damage > self.previous_damage + 100:
            self.previous_damage = damage
            return True, "crash_damage"

        self.previous_damage = damage

        if speed_x < 5:
            self.stuck_steps += 1
        else:
            self.stuck_steps = 0

        if self.stuck_steps > 100:
            return True, "stuck"

        if abs(angle) > 1.2:
            return True, "wrong_direction"

        return False, None

    def process_obs(self, obs):
        track = self.get_value(obs, "track")
        speed_x = self.get_value(obs, "speedX")
        angle = self.get_value(obs, "angle")
        track_pos = self.get_value(obs, "trackPos")

        return np.array(
            list(track) + [speed_x, angle, track_pos],
            dtype=np.float32
        )

    def get_value(self, obs, name):
        if isinstance(obs, dict):
            return obs[name]

        return getattr(obs, name)

    def close(self):
        self.env.end()