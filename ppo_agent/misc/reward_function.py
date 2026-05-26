"""Custom TORCS racing reward: speed, track position, angle, damage, off-track penalties"""

import math
import config


def get_value(obs, name, default=0.0):
    if isinstance(obs, dict):
        return obs.get(name, default)
    return getattr(obs, name, default)


def calculate_reward(obs, previous_obs=None):
    speed_x = get_value(obs, "speedX")
    angle = get_value(obs, "angle")
    track_pos = get_value(obs, "trackPos")
    damage = get_value(obs, "damage")
    dist_raced = get_value(obs, "distRaced")

    reward = 0.0

    if previous_obs is not None:
        previous_dist = get_value(previous_obs, "distRaced")
        progress = max(0.0, dist_raced - previous_dist)
        reward += progress * 10.0
    else:
        reward += speed_x * 0.1

    alignment = max(0.0, math.cos(angle))
    reward += speed_x * alignment * 0.2

    reward -= abs(angle) * 25.0

    if abs(track_pos) > 1.0:
        reward -= 500.0
    elif abs(track_pos) > 0.8:
        reward -= 40.0
    elif abs(track_pos) > 0.6:
        reward -= 10.0

    reward -= damage * 0.02

    if speed_x < 5:
        reward -= 5.0

    return reward