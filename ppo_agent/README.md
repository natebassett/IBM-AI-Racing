# PPO TORCS Training Files

## Where to put these files

Put these Python files in your PPO folder, for example:

```text
IBM-AI-Racing/
  ppo/
    config.py
    ppo_memory.py
    ppo_model.py
    reward_function.py
    torcs_env_wrapper.py
    train_ppo.py
    test_ppo.py
```

Your existing `RaceYourCode/gym_torcs/gym_torcs.py` can stay where it is.

## Important notes

This version uses:

```python
ACTION_DIM = 3
```

The model controls:

```text
steer, accel, brake
```

Gear shifting is handled automatically by your edited `gym_torcs.py`, because that file already has RPM-based shifting when `gear_change=False`.

The model sees 29 values:

```text
track[19]
speedX
speedY
speedZ
angle
trackPos
rpm
gear
wheelSpinVel[4]
```

## Run training

From the PPO folder:

```bash
python train_ppo.py
```

## Test a saved model

Edit the model name in `test_ppo.py`, then run:

```bash
python test_ppo.py
```

## Main changes made

- Fixed reset relaunch handling.
- Increased state from 22 to 29.
- Added speedY, speedZ, rpm, gear and wheelSpinVel to observations.
- Kept gear automatic for now, because your `gym_torcs.py` expects action `[steer, accel]` when `gear_change=False`.
- Added brake support by writing directly into `client.R.d["brake"]`.
- Made stuck detection less aggressive.
- Changed PPO update timesteps from 514 to 1024.
- Logged the reason each episode ended.
