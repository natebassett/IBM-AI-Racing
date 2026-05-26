"""Custom TORCS reward.

Main idea:
- reward actual forward progress around the track
- reward aligned speed
- punish going off-track, spinning, crashing, or sitting still
- avoid over-punishing trackPos so PPO can eventually discover better racing lines
"""

import math


def get_value(obs, name, default=0.0):
    if isinstance(obs, dict):
        return obs.get(name, default)
    return getattr(obs, name, default)


def calculate_reward(obs, previous_obs=None):
    speed_x = get_value(obs, "speedX")
    speed_y = get_value(obs, "speedY")
    angle = get_value(obs, "angle")
    track_pos = get_value(obs, "trackPos")
    damage = get_value(obs, "damage")
    dist_raced = get_value(obs, "distRaced")

    reward = 0.0

    # Best signal: actual movement along the lap.
    if previous_obs is not None:
        previous_dist = get_value(previous_obs, "distRaced")
        progress = max(0.0, dist_raced - previous_dist)
        reward += progress * 20.0
    else:
        progress = 0.0

    # Reward speed only when the car is pointing in the right direction.
    alignment = max(0.0, math.cos(angle))
    reward += speed_x * alignment * 0.1

    # Punish poor alignment and sliding.
    reward -= abs(angle) * 8.0
    reward -= abs(speed_y) * 0.05

    # Soft track-position penalty. This is intentionally not too harsh,
    # otherwise the agent learns centre-line driving rather than race lines.
    abs_track_pos = abs(track_pos)
    if abs_track_pos > 1.0:
        reward -= 500.0
    elif abs_track_pos > 0.9:
        reward -= 50.0
    elif abs_track_pos > 0.75:
        reward -= 10.0

    # Damage is bad, but do not let cumulative damage dominate every step.
    if previous_obs is not None:
        previous_damage = get_value(previous_obs, "damage")
        damage_delta = max(0.0, damage - previous_damage)
        reward -= damage_delta * 2.0

    # Stop it learning to sit still.
    if speed_x < 5:
        reward -= 5.0

    return float(reward)
