"""Custom TORCS racing reward: speed, track position, angle, damage, off-track penalties"""

import numpy as np
import config


def get_value(obs, name):
    if isinstance(obs, dict):
        return obs[name]
    return getattr(obs, name)


def calculate_reward(obs):
    speed_x = get_value(obs, "speedX")
    angle = get_value(obs, "angle")
    track_pos = get_value(obs, "trackPos")
    damage = get_value(obs, "damage")

    reward = 0.0

    reward += speed_x * config.SPEED_WEIGHT
    reward -= abs(angle) * config.ANGLE_PENALTY_WEIGHT
    reward -= abs(track_pos) * config.TRACK_POSITION_WEIGHT
    reward -= damage * config.DAMAGE_WEIGHT

    if abs(track_pos) > 1.0:
        reward -= config.OFF_TRACK_PENALTY

    return reward