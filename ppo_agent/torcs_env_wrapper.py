"""Connects PPO to gym_torcs and builds clean observations/actions."""

import os
import sys

import numpy as np

# Change this path if your gym_torcs folder is somewhere else.
sys.path.append(os.path.abspath("../RaceYourCode/gym_torcs"))

from gym_torcs import TorcsEnv  # noqa: E402
from reward_function import calculate_reward  # noqa: E402


class TorcsEnvWrapper:
    def __init__(self):
        self.env = TorcsEnv(
            vision=False,
            throttle=True,
            gear_change=False,  # keep gears automatic in gym_torcs
            
        )
        
        self.previous_damage = 0.0
        self.previous_obs = None
        self.stuck_steps = 0
        self.prev_steer = 0.0

    def reset(self, relaunch=False):
        self.env.reset(relaunch=relaunch)

        raw_obs = self.env.client.S.d.copy()

        self.previous_damage = self.get_value(raw_obs, "damage")
        self.previous_obs = raw_obs.copy()
        self.stuck_steps = 0
        self.prev_steer = 0.0

        return self.process_obs(raw_obs), raw_obs

    def step(self, action):
        raw_steer = float(np.clip(action[0], -1.0, 1.0))
        steer = 0.75 * self.prev_steer + 0.25 * raw_steer
        self.prev_steer = steer

        accel = float((np.clip(action[1], -1.0, 1.0) + 1.0) / 2.0)
        brake = float((np.clip(action[2], -1.0, 1.0) + 1.0) / 2.0)

        accel = np.clip(accel, 0.25, 0.65)

        if accel > 0.25:
            brake = 0.0

        # gym_torcs only accepts steer + accel when throttle=True and gear_change=False.
        # Brake is applied directly to the TORCS response dictionary before stepping.
        self.env.client.R.d["brake"] = brake

        torcs_action = np.array([steer, accel], dtype=np.float32)

        _, _, done, info = self.env.step(torcs_action)

        raw_obs = self.env.client.S.d.copy()

        reward = calculate_reward(raw_obs, self.previous_obs)
        self.previous_obs = raw_obs.copy()

        failure, failure_reason = self.check_failure(raw_obs)

        if failure:
            reward -= 500.0
            done = True
            info["failure_reason"] = failure_reason

        return self.process_obs(raw_obs), reward, done, info, raw_obs

    def check_failure(self, obs):
        speed_x = self.get_value(obs, "speedX")
        angle = self.get_value(obs, "angle")
        track_pos = self.get_value(obs, "trackPos")
        damage = self.get_value(obs, "damage")

        if abs(track_pos) > 1.2:
            return True, "off_track"

        if damage > self.previous_damage + 100:
            self.previous_damage = damage
            return True, "crash_damage"

        self.previous_damage = damage

        if speed_x < 3:
            self.stuck_steps += 1
        else:
            self.stuck_steps = 0

        # 300 steps was too harsh for early learning in many TORCS setups.
        if self.stuck_steps > 500:
            return True, "stuck"

        if abs(angle) > 1.5:
            return True, "wrong_direction"

        return False, None

    def process_obs(self, obs):
        track = np.asarray(self.get_value(obs, "track"), dtype=np.float32)
        wheel_spin = np.asarray(self.get_value(obs, "wheelSpinVel"), dtype=np.float32)

        speed_x = float(self.get_value(obs, "speedX"))
        speed_y = float(self.get_value(obs, "speedY"))
        speed_z = float(self.get_value(obs, "speedZ"))
        angle = float(self.get_value(obs, "angle"))
        track_pos = float(self.get_value(obs, "trackPos"))
        rpm = float(self.get_value(obs, "rpm"))
        gear = float(self.get_value(obs, "gear", 1.0))

        # Normalise values so the neural network receives sensible scales.
        track_norm = np.clip(track / 200.0, -1.0, 1.0)
        wheel_spin_norm = np.clip(wheel_spin / 100.0, -5.0, 5.0)

        features = list(track_norm) + [
            speed_x / 300.0,
            speed_y / 100.0,
            speed_z / 100.0,
            angle,
            track_pos,
            rpm / 10000.0,
            gear / 6.0,
        ] + list(wheel_spin_norm)

        return np.asarray(features, dtype=np.float32)

    def get_value(self, obs, name, default=0.0):
        if isinstance(obs, dict):
            return obs.get(name, default)
        return getattr(obs, name, default)

    def close(self):
        self.env.end()
