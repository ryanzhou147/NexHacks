import numpy as np
import csv
import sys

# Settings
SAMPLING_RATE = 200
WINDOW_LENGTH_MS = 250 #50 samples
STEP_SAMPLES = 25 #125 ms

def to_csv(x_file, y_file, output_file="training_data.csv"):
    """Convert X, y numpy files to CSV for Wood Wide."""
    
    X = np.load(x_file)
    y = np.load(y_file)
    
    print(f"Loaded X: {X.shape}, y: {y.shape}")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp_ms', 'rms', 'mav', 'variance', 'peak', 'peak_to_rms', 'is_clench'])
        
        for i in range(len(X)):
            timestamp_ms = i * (STEP_SAMPLES / SAMPLING_RATE * 1000)
            rms, mav, variance, peak, peak_to_rms = X[i]
            label = int(y[i])
            
            writer.writerow([
                int(timestamp_ms),
                round(rms, 4),
                round(mav, 4),
                round(variance, 4),
                round(peak, 4),
                round(peak_to_rms, 4),
                label
            ])
    
    print(f"Saved: {output_file}")
    print(f"Total rows: {len(X)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python to_csv.py X_file.npy y_file.npy [output.csv]")
        sys.exit(1)
    
    x_file = sys.argv[1]
    y_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "training_data.csv"
    
    to_csv(x_file, y_file, output_file)