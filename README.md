# Grav-Nav-RL-Multiplayer

Brown CPFU Vers. 8.28.25

A Fork of https://github.com/BrownParticleAstro/Grav-Nav-RL.git but includes multiship orbital environment & multiplayer game using authoritative server-client setup.

This project simulates 2D orbital maneuvers via RL and provides a real-time multiplayer experience. Players can control their ships manually or deploy a trained AI model to compete for the longest survival time.

---

## 🚀 Deployment to Production

For deploying this application to Google Cloud Run with automated CI/CD, see the complete deployment guide:

**📖 [Deployment Documentation](.deployment/DEPLOYMENT.md)**

### Quick Start for Deployment:
1. Complete one-time setup (GCP project, service account, GitHub secrets)
2. Trigger deployment via GitHub Actions
3. Access your game at the provided Cloud Run URL

---

## How to Run the Multiplayer Game

There are two ways to run the game: with Docker (recommended for a clean, isolated setup) or locally on your machine.

### Method 1: Run with Docker (Recommended)

This is the simplest way to get the game running.

#### Prerequisites

-   Docker and Docker Compose must be installed on your system.

#### Step 1: Build and Start the Container

1.  Open a terminal and navigate to the root directory of the project.
2.  Run the following command. It will build the Docker image and start the server.

    ```bash
    docker-compose up --build
    ```

3.  The server is now running. You will see log output in your terminal, ending with a line like: `INFO: Uvicorn running on http://0.0.0.0:5501`.

#### Step 2: Open the Game Client

1.  Open your web browser.
2.  Navigate to the following address:
    ```
    http://localhost:5501
    ```
3.  The game client will load and connect to the server running inside the Docker container.

#### Step 3: Stop the Game

1.  Return to the terminal where the server is running.
2.  Press `Ctrl + C` to stop the container.
3.  To remove the container and its network, run:
    ```bash
    docker-compose down
    ```

---

### Method 2: Run Locally (Without Docker)

Follow these steps to run the server and client directly on your machine.

#### Prerequisites

-   Python 3.8 or higher
-   A modern web browser
-   VS Code with the **Live Server** extension (recommended for hosting `index.html`)

#### Step 1: Set Up Python Environment

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv grav-nav-env
    ```
2.  **Activate the virtual environment:**
    -   **On macOS/Linux:**
        ```bash
        source grav-nav-env/bin/activate
        ```
    -   **On Windows:**
        ```bash
        grav-nav-env\Scripts\activate
        ```

#### Step 2: Install Dependencies

1.  **Install required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Verify installation:**
    ```bash
    python -c "import fastapi, uvicorn, numpy, torch, stable_baselines3; print('All dependencies installed successfully!')"
    ```

#### Step 3: Run the Multiplayer Server

1. **Start the server:**

   ```bash
   python server_multiship.py
   ```

   *Note: To run multidevice version, please run this isntead:
   ```bash
   uvicorn server_multiship:app --host 0.0.0.0 --port 5500
   ```

2. **Verify server is running:**
   - You should see output like: `INFO: Uvicorn running on http://0.0.0.0:5500`
   - The server will be accessible at `http://localhost:5500`
   - For multidevice version, the server will be accessible at `http://10.37.117.236:5500/`. This is based off the IP address of the Brown WiFi network.

#### Step 4: Open the Game Client

1.  **Open VS Code** in the project directory.
2.  Right-click on the `index.html` file in the explorer panel.
3.  Select "**Open with Live Server**".
4.  Your browser will open automatically to the game interface (e.g., `http://127.0.0.1:5501/index.html`).

#### Step 5: Join the Game

1.  **Choose your control mode:**
    -   Click "**Manual Control**" to fly your ship with the keyboard.
    -   Click "**RL Model Control**" to upload a `.zip` model file and let an AI control your ship.
2.  **Manual Controls:**
    -   **↑** (Up Arrow): Apply thrust.
    -   **←** (Left Arrow): Turn left.
    -   **→** (Right Arrow): Turn right.
3.  **Multiple Players:**
    -   Open additional browser tabs to the same address. Each tab will be a new player.

---

## 🔄 Communication Schema (Authoritative Server)

The simulation runs on an authoritative server using a tick-based system for synchronization.

### Server State Management

-   **`clients` dict**: `{client_id: {"ws": websocket, "type": "manual" | "model", "ship_id": "uuid"}}`
-   **`env.ships` dict**: `{ship_id: {x, y, vx, vy, init_r, done, ...}}`
-   **`leaderboard` dict**: `{ship_id: {name, steps, alive}}`

### Standardized Message Format

All messages follow a standard header/payload format.

```json
{
  "header": {
    "version": "1.0",
    "type": "message_type_string",
    "tick": 12345,
    "timestamp": 167...
  },
  "payload": { ... }
}
```

### Key Message Types

**Server → Client:**

-   `mode_confirmed`: Confirms the client's control mode (`observe`, `manual`, or `model`).
-   `action_request`: Sent each tick to request an action from manual-control clients.
-   `model_upload_response`: Informs the client if their AI model was successfully loaded.
-   `state_update`: Broadcasts the state of all ships, leaderboard, and trail history to all clients.

**Client → Server:**

-   `join_mode`: Client requests to join with a specific control mode (`manual` or `model`).
-   `model_upload`: Client sends a base64-encoded AI model file.
-   `manual_action`: Client sends their turn and thrust inputs for the current tick.
-   `cancel_control`: Client requests to leave the game and return to observer mode.

---

## 🛰️ Single-Player Simulation Project

The original goal was to simulate spacecraft orbital control by training a PPO model to pilot a spacecraft, achieving stable orbits with minimal fuel cost.

**Core features include:**

-   **Training**: Learn optimal control strategies with PPO.
-   **Testing**: Evaluate model performance.
-   **Rendering**: Visualize the simulation at various stages.
-   **Rendering Multiship**: Run `python3 render_multiship_trained.py` to visualize multiple AI-controlled ships orbiting a central mass.

---

### 📂 Project Structure

| File Name                     | Description                                                                                                                                                                                                           |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`environment.py`**          | Defines the `OrbitalEnvironment` (core physics) and `MultiShipOrbitalEnvironment`. Adjust physics and reward functions here.                                                                                          |
| **`model.py`**                | Contains the neural network architecture for the PPO agent.                                                                                                                                                             |
| **`render.py`**               | Handles `matplotlib` visualizations for single-ship test episodes.                                                                                                                                                    |
| **`run_and_view_episode.py`** | A primary script for training, testing, and visualizing a full single-ship episode from start to finish.                                                                                                                |
| **`train.py`**                | Trains the PPO model. Modify hyperparameters (learning rate, gamma, etc.)                                                                                                                                             |
| **`test.py`**                 | Runs multiple test episodes to evaluate a trained model's performance.                                                                                                                                                  |
| **`hohman_example.py`**       | Demonstrates a Hohmann transfer orbit, a classic two-burn maneuver to move between circular orbits efficiently.                                                                                                         |

---

### 🔄 Training

Run `train.py` to train a new AI model from scratch.
```bash
python train.py
```
_This script saves the trained model and episode data to a new timestamped folder in `./models/`._

### 🧪 Testing

Run `test.py` to evaluate a pre-trained model.```bash
python test.py --model_path /path/to/your/model.zip
```

### 🎬 Running and Visualizing Full Episodes

Use `run_and_view_episode.py` to train, test, and render in one command.
```bash
python run_and_view_episode.py
```

### 🛰️ Hohmann Transfer Example

Run `hohman_example.py` to see a demonstration of a classical Hohmann transfer orbit.
```bash
python hohman_example.py
```