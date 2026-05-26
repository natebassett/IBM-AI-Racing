"""Central configuration for PPO + TORCS training."""

TRACK_NAME = "corkscrew"

# Training length
MAX_EPISODES = 500
MAX_STEPS = 3000
RELAUNCH_FREQUENCY = 25

# PPO hyperparameters
LEARNING_RATE = 3e-4
GAMMA = 0.99
GAE_LAMBDA = 0.95
CLIP_EPSILON = 0.2
PPO_EPOCHS = 10
BATCH_SIZE = 64
UPDATE_TIMESTEPS = 1024

# TORCS / action settings
MAX_STEER = 1.0
MAX_ACCEL = 1.0
MAX_BRAKE = 1.0

# Action = [steer, accel, brake]
# Gear is handled by the wrapper using RPM-based automatic shifting.
ACTION_DIM = 3

# Observation:
# track[19] + speedX + speedY + speedZ + angle + trackPos + rpm + gear + wheelSpinVel[4]
TRACK_SENSOR_COUNT = 19
STATE_DIM = 30

MODEL_SAVE_PATH = "../models/ppo/"
SAVE_INTERVAL = 50

LOG_PATH = "./logs/"
LOG_INTERVAL = 1

DEVICE = "cpu"

# Exploration
ACTION_STD_INIT = 0.6
MIN_ACTION_STD = 0.1
ACTION_STD_DECAY = 0.05
ACTION_STD_DECAY_FREQ = 250000
