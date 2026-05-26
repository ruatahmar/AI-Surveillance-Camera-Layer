# AI-Surveillance-Camera-Layer

AI-based monitoring using surveillance cameras. Detects people, loitering, crowd formation, and ID card presence in real-time.

## Architecture

```
Camera Source
  → YOLO person detection + tracking (person.py)
    → Loitering detection (loitering.py)
    → Crowd monitoring (crowd_detection.py)
    → Per-person crop → ID card classification (idCard/detector.py)
  → Annotated frame displayed locally / alert sent to frontend
```

Alerts (loitering, crowd, no_id) are POSTed to the Next.js frontend as base64-encoded JPEGs.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) or pip
- Node.js 18+ (for frontend)
- A YOLO model file (see config)

## Setup

### Backend

```bash
# Clone and enter the repo
git clone <repo-url>
cd AI-Surveillance-Camera-Layer

# Create a virtual environment and install dependencies
uv sync
# or: pip install -e .

# Copy the example config and edit to your needs
cp config.toml.example config.toml
```

### Frontend

```bash
cd frontend
npm install
```

## Configuration

See `config.toml.example` for all available settings.

| Setting | Default | Description |
|---------|---------|-------------|
| `model_path` | `data/models/best.pt` | Path to YOLO ID card detection model |
| `conf_threshold` | `0.5` | YOLO confidence threshold for person detection |
| `loitering_threshold` | `10.0` | Seconds a person must remain before loitering alert |
| `loitering_enabled` | `false` | Enable loitering detection per source |
| `alert_limit_per_track` | `1` | Max alerts per tracked person per session |
| `alert_cooldown` | `0.0` | Min seconds between alerts for the same person |
| `process_every_n_frames` | `1` | Run detection every Nth frame (3 = ~10 fps at 30 fps source) |
| `crowd_min_people` | `5` | Min people to trigger crowd alert |
| `crowd_min_duration` | `15.0` | Seconds crowd count must persist before alerting |

## Running Locally

### Backend

```bash
# With display windows (requires GUI)
python main.py

# Headless mode (no display)
python main.py --headless

# Custom config path
python main.py --config /path/to/config.toml
```

### Frontend (alert dashboard)

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000` to see the alert feed. The frontend polls the backend every 3 seconds for new alerts.

## Modes

- **Normal mode**: Displays annotated camera windows with `cv2.imshow()`. Press `q` to quit.
- **Headless mode** (`--headless`): Runs detection without GUI windows. Useful for servers or background deployment.
