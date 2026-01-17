import pygame
import sys
import time
import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

# Settings
SAMPLING_RATE = 200
NUM_CHANNELS = 2
WINDOW_LENGTH_MS = 250
WINDOW_SAMPLES = int(SAMPLING_RATE * WINDOW_LENGTH_MS / 1000)  # 50 samples
STEP_SAMPLES = 25
NUM_TRIALS = 20

# Setup board
params = BrainFlowInputParams()
params.serial_port = "COM3"
board_id = 1

try:
    board = BoardShim(board_id, params)
    board.prepare_session()
    print("Successfully prepared physical board.")
except Exception as e:
    print(e)
    print("Device could not be found or is being used by another program")
    sys.exit()

# Initialize Pygame
pygame.init()
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
pygame.mouse.set_visible(False)

emg_channels = BoardShim.get_emg_channels(board_id)[:NUM_CHANNELS]
marker_channel = BoardShim.get_marker_channel(board_id)

def draw_black():
    screen.fill(BLACK)
    pygame.display.flip()

def draw_fixation():
    screen.fill(BLACK)
    pygame.draw.line(screen, WHITE, (WIDTH//2 - 30, HEIGHT//2), (WIDTH//2 + 30, HEIGHT//2), 4)
    pygame.draw.line(screen, WHITE, (WIDTH//2, HEIGHT//2 - 30), (WIDTH//2, HEIGHT//2 + 30), 4)
    pygame.display.flip()

def check_quit():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise KeyboardInterrupt
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            raise KeyboardInterrupt

def extract_features(window):
    """Extract features from multi-channel window."""
    aggregated = np.sqrt(np.mean(window ** 2, axis=0))
    rms = np.sqrt(np.mean(aggregated ** 2))
    mav = np.mean(np.abs(aggregated))
    variance = np.var(aggregated)
    peak = np.max(np.abs(aggregated))
    peak_to_rms = peak / rms if rms > 0 else 0
    return [rms, mav, variance, peak, peak_to_rms]

try:
    board.start_stream()
    print(f"Stream started. EMG channels: {emg_channels}")
    time.sleep(2)
    
    for trial in range(NUM_TRIALS):
        check_quit()
        
        # REST: Black screen 5 seconds (Label 0)
        board.insert_marker(0)
        draw_black()
        time.sleep(5.0)
        
        check_quit()
        
        # CLENCH: Black 2s, Fixation 1s, Black 2s (Label 1)
        board.insert_marker(1)
        draw_black()
        time.sleep(2.0)
        draw_fixation()
        time.sleep(1.0)
        draw_black()
        time.sleep(2.0)
        
        print(f"Trial {trial + 1}/{NUM_TRIALS}")
    
    draw_black()
    time.sleep(2)
    data = board.get_board_data()

except KeyboardInterrupt:
    print("Stopped by user")
    data = board.get_board_data()

finally:
    board.stop_stream()
    board.release_session()
    pygame.quit()

# Process into X, y
print("\nProcessing...")

emg_data = data[emg_channels, :]
markers = data[marker_channel, :]

marker_indices = np.where(markers != 0)[0]
marker_values = markers[marker_indices]

X = []
y = []

for i in range(len(marker_indices)):
    marker_idx = marker_indices[i]
    label = int(marker_values[i])
    
    end_idx = marker_indices[i + 1] if i + 1 < len(marker_indices) else emg_data.shape[1]
    
    for start in range(marker_idx, end_idx - WINDOW_SAMPLES, STEP_SAMPLES):
        window = emg_data[:, start:start + WINDOW_SAMPLES]
        features = extract_features(window)
        X.append(features)
        y.append(label)

X = np.array(X)
y = np.array(y)

print(f"X shape: {X.shape}")
print(f"y shape: {y.shape}")
print(f"Rest samples: {np.sum(y == 0)}")
print(f"Clench samples: {np.sum(y == 1)}")

timestamp = time.strftime("%Y%m%d_%H%M%S")
np.save(f"X_{timestamp}.npy", X)
np.save(f"y_{timestamp}.npy", y)
print(f"\nSaved: X_{timestamp}.npy, y_{timestamp}.npy")