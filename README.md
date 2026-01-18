# Nexhacks - Assistive Communication Interface

An assistive communication system that enables users to communicate through biosignal gestures. The system uses AI-powered word prediction, real-time signal processing, and voice synthesis to help users build and speak sentences naturally.

---

## How We Use APIs for Compound Insights (150 Words)

Our system creates a **compound AI pipeline** by chaining three specialized APIs to transform raw biosignals into natural speech.

**WoodWide AI** serves as our biosignal intelligence layer. We upload labeled EMG data collected from OpenBCI hardware to train a Prediction model that classifies gestures with high accuracy. WoodWide's numeric reasoning eliminates false positives from noisy sensor data by learning semantic patterns rather than relying on brittle thresholds. This gives us production-ready biosignal detection without building custom ML infrastructure.

**ElevenLabs** powers our voice pipeline. We clone the user's biological voice from a 10-second sample, then synthesize their constructed sentences in real-time. The transcription service captures conversation context, feeding it to our word prediction engine for contextually relevant suggestions.

**OpenRouter (Gemini 2.0 Flash)** generates intelligent word predictions based on partial sentences and conversation context, enabling users to communicate faster with fewer selections.

Together, these APIs create a seamless biosignal-to-speech experience.

---

## Features

- **Biosignal Navigation**: Control the interface using biosignal inputs (single signal = move right, double signal = move down, hold = select)
- **AI-Powered Word Prediction**: Context-aware word suggestions using Google Gemini 2.0 Flash
- **Voice Cloning**: Synthesize speech using the user's own cloned voice
- **Real-Time Transcription**: Transcribe conversation partners for context-aware responses
- **Signal Processing**: Advanced EMG signal filtering and noise reduction

## Required API Keys

You will need the following API keys to run this application:

| Service | Key Name | Purpose | Get it from |
|---------|----------|---------|-------------|
| OpenRouter | `OPENROUTER_API_KEY` | AI word prediction (Gemini 2.0 Flash) | [openrouter.ai](https://openrouter.ai/) |
| ElevenLabs | `ELEVEN_API_KEY` | Text-to-speech & voice cloning | [elevenlabs.io](https://elevenlabs.io/) |
| WoodWide AI | `WOODWIDE_API_KEY` | Biosignal prediction model | [woodwide.ai](https://woodwide.ai/) |

## Project Structure

```
Nexhacks/
├── backend/                 # FastAPI Python backend (port 8000)
│   ├── main.py             # Main API endpoints
│   ├── config.py           # Configuration and API keys
│   ├── word_generator.py   # AI word prediction logic
│   └── requirements.txt    # Python dependencies
├── frontend/               # React + TypeScript frontend (port 3000)
│   ├── src/
│   │   ├── App.tsx        # Main application component
│   │   ├── components/    # UI components
│   │   └── api/           # API client functions
│   └── package.json       # Node dependencies
├── Signal_Processing/      # EMG signal processing
│   ├── ClenchDetection.py # Biosignal detection via LSL
│   └── TranscriptionService.py # Speech-to-text service
└── docker-compose.yml      # Docker orchestration
```

## Setup Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn
- (Optional) EEG/EMG hardware with Lab Streaming Layer (LSL) support

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Nexhacks.git
cd Nexhacks
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env and add your API keys
# OPENROUTER_API_KEY=sk-or-v1-your-key-here
# ELEVEN_API_KEY=sk_your-key-here
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 4. Signal Processing Setup (Optional)

If using EEG/EMG hardware for jaw clench detection:

```bash
cd Signal_Processing

# Install additional dependencies
pip install SpeechRecognition pylsl pygame brainflow mne
```

## Running the Application

### Start the Backend

```bash
cd backend
python main.py
# Server starts at http://localhost:8000
```

### Start the Frontend

```bash
cd frontend
npm run dev
# Opens at http://localhost:3000
```

### Start Signal Processing (Optional)

```bash
# For jaw clench detection (requires LSL stream)
cd Signal_Processing
python ClenchDetection.py

# For transcription service (listens to microphone)
python TranscriptionService.py
```

### Development Controls

For testing without hardware, use keyboard controls:
- `1` or `Right Arrow`: Move cursor right
- `2` or `Down Arrow`: Move cursor down
- `3`: Refresh word grid
- Wait 800ms on a word: Auto-select

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

---

## WoodWide AI - Numeric Reasoning for Biosignal Detection

We leverage **[WoodWide AI's Numeric Reasoning API](https://woodwide.ai/)** for biosignal classification, enabling accurate detection from noisy EMG sensor data without building custom ML pipelines.

### Why We Chose the Predict Model

WoodWide AI offers four model types: **Predict**, **Cluster**, **Anomaly**, and **Embedding**. For our biosignal detection use case, we selected the **Prediction Model** because:

| Model Type | Use Case | Why Not For Us |
|------------|----------|----------------|
| **Predict** | Supervised classification/regression | **Best fit** - we have labeled training data |
| Cluster | Unsupervised grouping | No ground truth labels needed, but we have them |
| Anomaly | Outlier detection | Good for unknown patterns, but we know what we're looking for |
| Embedding | Vector representations | Useful for similarity, not classification |

Our biosignal detection is a **binary classification problem** (signal detected vs. not detected) with labeled training data, making WoodWide's Prediction endpoint the optimal choice.

### How WoodWide AI Solves Our Challenges

#### 1. Eliminating False Positives

Raw biosignal data from EMG sensors is notoriously noisy. Traditional threshold-based detection produces frequent false positives from:
- Muscle artifacts from talking or swallowing
- Electrical interference from nearby devices
- Electrode movement and contact issues

WoodWide AI's prediction model learns the **semantic context** of what constitutes a true biosignal by training on labeled examples. By conditioning on units, schemas, and constraints, it produces outputs that are **accurate, interpretable, and dependable** - distinguishing genuine signals from noise artifacts.

#### 2. Handling Noisy Data

Instead of hand-tuning signal processing filters, we upload our raw CSV data to WoodWide and let the API build a **reusable representation layer**. This representation:
- Adapts to individual user physiology
- Maintains accuracy as conditions change
- Eliminates the need for constant retuning

#### 3. Focus on Technical Execution

WoodWide AI's **API-first design** means we don't build custom ML infrastructure. Our workflow:

```
1. POST /api/datasets          → Upload training CSV
2. POST /api/models/prediction/train → Train prediction model
3. GET  /api/models/{id}       → Poll until status = COMPLETE
4. POST /api/models/prediction/{id}/infer → Run inference
```

This lets us focus on the user experience and real-time signal handling while WoodWide handles the ML complexity.

### Integration Architecture

```python
# woodwide_client.py - Our WoodWide AI integration

client = WoodWideClient(api_key=WOODWIDE_API_KEY)

# 1. Upload labeled training data
dataset_id = client.upload_dataset("training_data.csv", "biosignal_training")

# 2. Train prediction model on 'is_clench' label column
model_id = client.train_model("biosignal_detector", label_column="is_clench")

# 3. Wait for async training to complete
client.wait_for_training(timeout=300)

# 4. Run inference on new data
predictions = client.predict(inference_dataset_id)
```

---

## Dataset Documentation

### Source: OpenBCI Live Signals

Our training dataset was collected from **live OpenBCI biosignal recordings**, capturing real EMG activity during controlled sessions.

#### Data Collection Setup
- **Hardware**: OpenBCI Cyton board with EMG electrodes
- **Placement**: Electrodes positioned on the masseter muscle group
- **Protocol**: Participants performed controlled biosignal gestures with rest periods
- **Streaming**: Data streamed via Lab Streaming Layer (LSL) protocol

#### Dataset Schema

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | float | Unix timestamp of sample |
| `rms` | float | Root Mean Square of signal amplitude |
| `is_clench` | int (0/1) | Ground truth label (1 = biosignal detected) |

#### Preprocessing Pipeline

Before uploading to WoodWide AI:
1. **Low-pass filtering** at 500Hz to remove high-frequency noise
2. **Reference signal subtraction** to eliminate common-mode artifacts
3. **RMS feature extraction** over sliding windows
4. **Manual labeling** of biosignal events for supervised training

The preprocessed CSV is then uploaded to WoodWide AI for model training, allowing the Reasoning API to learn patterns that generalize beyond simple threshold detection

---

## ElevenLabs - Voice & Audio Pipeline

**ElevenLabs** serves as the audio foundation for our communication system, providing both speech recognition and synthesis capabilities.

### Speech-to-Text (Real-Time Transcription)

The transcription service captures and processes audio from conversation partners:

- **Real-time transcription** of incoming speech with low latency
- **Context-aware response prediction**: Transcribed text is fed to our word prediction engine, enabling the system to suggest contextually relevant responses
- **Speaker identification** for multi-person conversations
- **Noise-robust recognition** using clinical-grade audio processing

### Voice Cloning

ElevenLabs enables users to speak in their own biological voice:

- **Instant voice cloning** from just a 10-second audio sample
- **Emotional nuance preservation**: The cloned voice maintains the user's natural speech patterns, intonation, and emotional expression
- **Real-time synthesis**: Generated speech plays immediately as sentences are constructed

### Audio Quality

We prioritize clinical-grade audio clarity:

- **High-fidelity voice output** ensures natural, human-like speech
- **Emotional authenticity** preserves the subtle nuances that make communication personal
- **Adaptive volume and pacing** for different listening environments

### Integration Flow

```
User's Voice Sample (10s) ──> ElevenLabs Voice Clone
                                      │
Conversation Partner ──> Speech-to-Text ──> Word Prediction Engine
                                                      │
                              Selected Words ──> Text-to-Speech ──> Cloned Voice Output
```

---

## API Endpoints

### Word Generation
- `POST /api/words` - Generate contextual word predictions
- `POST /api/refresh` - Refresh word grid

### Voice & Speech
- `POST /api/clone-voice` - Clone voice from audio sample
- `POST /api/text-to-speech` - Convert text to speech
- `POST /api/speak-sentence` - Speak completed sentence

### Signals & Transcription
- `POST /api/signal` - Receive biosignal events
- `WebSocket /ws/signals` - Real-time signal streaming
- `WebSocket /ws/transcription` - Real-time transcription streaming

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Required
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key
ELEVEN_API_KEY=sk_your-elevenlabs-key
WOODWIDE_API_KEY=your-woodwide-api-key

# Optional (defaults shown)
OPENROUTER_MODEL=google/gemini-2.0-flash-001
```

## Troubleshooting

### Backend won't start
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that API keys are set in `.env`
- Verify port 8000 is not in use

### No word predictions
- Verify `OPENROUTER_API_KEY` is valid
- Check backend logs for API errors

### Voice cloning not working
- Verify `ELEVEN_API_KEY` is valid
- Ensure audio sample is at least 10 seconds
- Check ElevenLabs account has available credits

### Signal processing issues
- Verify LSL stream is active and discoverable
- Adjust threshold values in `ClenchDetection.py`
- Check electrode placement and signal quality

## License

MIT License

## Acknowledgments

- **WoodWide AI** for signal processing and reasoning capabilities
- **ElevenLabs** for voice cloning and speech synthesis
- **OpenRouter** for LLM API access
- Built at NexHacks 2025
