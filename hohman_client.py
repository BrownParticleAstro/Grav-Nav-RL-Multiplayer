import asyncio
import json
import websockets
import uuid
import time
import math
import numpy as np

# Configuration
WS_URL = "ws://localhost:5500/ws"
SHIP_NAME = "PythonHohmann"
TARGET_RADIUS = 1.0 

# Constants
GM = 1.0
dt = 1.0/60.0 # 60Hz server tick rate

# State Globals
first_burn_applied = False
second_burn_applied = False

cached_state = None
my_ship_id = None

# ------------------------------------------------------------------
# Math Helpers
# ------------------------------------------------------------------

def compute_radius(x, y):
    return math.sqrt(x*x + y*y)

def get_orbit_direction(x, y, vx, vy):
    """Returns 1 for CCW, -1 for CW"""
    cross_product = x*vy - y*vx
    return 1 if cross_product >= 0 else -1

def calculate_maneuver_vector(x, y, vx, vy, target_speed):
    """
    Calculates the thrust and heading required to achieve a target speed
    in the purely tangential direction (killing radial velocity).
    """
    r = math.sqrt(x*x + y*y)
    
    # 1. Determine tangential unit vector based on current orbit direction
    direction = get_orbit_direction(x, y, vx, vy)
    
    # Normalized position vector
    nx, ny = x/r, y/r
    
    # Tangent vector (rotated 90 degrees)
    # CCW: (-y, x), CW: (y, -x)
    if direction == 1:
        tx, ty = -ny, nx
    else:
        tx, ty = ny, -nx
        
    # 2. Construct Target Velocity Vector
    target_vx = tx * target_speed
    target_vy = ty * target_speed
    
    # 3. Calculate Delta-V Vector
    dv_x = target_vx - vx
    dv_y = target_vy - vy
    
    # 4. Convert to Thrust and Heading
    dv_mag = math.sqrt(dv_x**2 + dv_y**2)
    thrust = dv_mag / dt
    heading = math.atan2(dv_y, dv_x)
    
    return thrust, heading, dv_mag

def calculate_orbital_elements(x, y, vx, vy):
    """Calculates specific energy, semi-major axis, and eccentricity"""
    r = math.sqrt(x*x + y*y)
    v2 = vx*vx + vy*vy
    
    # Specific Energy
    E = v2/2 - GM/r
    
    # Semi-major axis
    # E = -GM / 2a  => a = -GM / 2E
    if abs(E) < 1e-6:
        a = float('inf') # Parabolic
    else:
        a = -GM / (2*E)
        
    # Angular Momentum
    h_vec = x*vy - y*vx
    h2 = h_vec**2
    
    # Eccentricity
    # h^2 = GM * a * (1 - e^2) => e = sqrt(1 - h^2/(GM*a))
    # Be careful with floating point, clip to 0
    term = h2 / (GM * a)
    e = 0.0
    if term <= 1.0:
        e = math.sqrt(1.0 - term)
    
    return E, a, e

# ------------------------------------------------------------------
# Logic Core
# ------------------------------------------------------------------

def choose_action():
    """
    Decides the maneuver based on flight phase.
    Returns tuple: (thrust_magnitude, target_heading)
    """
    global first_burn_applied, second_burn_applied

    if cached_state is None:
        return 0.0, 0.0

    x = cached_state["x"]
    y = cached_state["y"]
    vx = cached_state["vx"]
    vy = cached_state["vy"]
    tick = cached_state["tick"]

    r = compute_radius(x,y)
    
    # Radial Velocity
    v_rad = (x*vx + y*vy) / r if r > 1e-5 else 0

    # --- Telemetry Logging (Every ~1 second) ---
    if tick % 60 == 0:
        E, a, e = calculate_orbital_elements(x, y, vx, vy)
        print(f"[DEBUG T={tick}] r={r:.4f}, v_rad={v_rad:.4f}, Energy={E:.4f}, a={a:.4f}, e={e:.4f}")

    # --- Phase 1: Injection Burn (Start Transfer) ---
    if not first_burn_applied:
        
        # Calculate Hohmann Transfer parameters
        r1 = r
        r2 = TARGET_RADIUS
        a_transfer = (r1 + r2) / 2
        
        # Vis-viva equation for velocity at periapsis of transfer orbit
        # v = sqrt(GM * (2/r - 1/a))
        v_transfer_req = math.sqrt(GM * (2/r1 - 1/a_transfer))
        
        # Calculate Vector Burn
        thrust, heading, dv = calculate_maneuver_vector(x, y, vx, vy, v_transfer_req)
        
        first_burn_applied = True
        print(f"[{tick}] BURN 1 (Injection): r={r:.4f}")
        print(f"    Target V: {v_transfer_req:.4f}")
        print(f"    Vector DV: {dv:.4f}, Thrust: {thrust:.4f}")
        
        return thrust, heading

    # Detect Apsis (Radial Velocity Flip)
    prev_v_rad = getattr(choose_action, "prev_v_rad", v_rad)
    choose_action.prev_v_rad = v_rad
    
    # Trigger when radial velocity flips sign (Apogee/Perigee)
    # AND we are reasonably close to the target radius
    apsis_reached = (prev_v_rad * v_rad < 0) 
    near_target = abs(r - TARGET_RADIUS) < 0.1

    # --- Phase 2: Circularization Burn ---
    if not second_burn_applied:
        if apsis_reached and near_target:
            
            # Calculate Circular Orbit parameters
            v_circ_req = math.sqrt(GM / r)
            
            # Calculate Vector Burn (Circularize)
            thrust, heading, dv = calculate_maneuver_vector(x, y, vx, vy, v_circ_req)

            second_burn_applied = True
            print(f"[{tick}] BURN 2 (Circularize): r={r:.4f}")
            print(f"    Target V: {v_circ_req:.4f}")
            print(f"    Vector DV: {dv:.4f}, Thrust: {thrust:.4f}")
            
            return thrust, heading
        
        # Coasting during transfer
        coasting_heading = math.atan2(vy, vx)
        return 0.0, coasting_heading

    # --- Phase 3: Coasting (Finished) ---
    # Just drift. Point along velocity vector to prevent rubberbanding.
    coasting_heading = math.atan2(vy, vx)
    return 0.0, coasting_heading

# ------------------------------------------------------------------
# Networking & Execution
# ------------------------------------------------------------------

async def send_manual_control(ws, tick, thrust, target_heading):
    if cached_state is None: return

    current_heading = cached_state.get("heading", 0.0)

    # Calculate Turn needed (Shortest path)
    diff = target_heading - current_heading
    diff = (diff + math.pi) % (2 * math.pi) - math.pi
    
    # Determine turn rate needed to snap to heading in 1 tick
    turn_action = diff / dt
    
    msg = {
        "header": {
            "version": "1.0",
            "type": "manual_action",
            "tick": tick,
            "timestamp": time.time(),
            "client_id": str(uuid.uuid4())
        },
        "payload": {
            "turn": float(turn_action),
            "thrust": float(thrust)
        }
    }
    await ws.send(json.dumps(msg))

async def main():
    global my_ship_id, cached_state

    async with websockets.connect(WS_URL) as ws:
        join_msg = {
            "header": {
                "version": "1.0",
                "type": "join_mode",
                "tick": 0,
                "timestamp": time.time(),
                "client_id": str(uuid.uuid4())
            },
            "payload": {
                "mode": "manual",
                "name": SHIP_NAME
            }
        }
        await ws.send(json.dumps(join_msg))
        print("Connected. Waiting for server...")

        while True:
            try:
                raw = await ws.recv()
                msg = json.loads(raw)
                t = msg["header"]["type"]

                if t == "mode_confirmed":
                    my_ship_id = msg["payload"].get("ship_id", my_ship_id)
                    print(f"Joined Game. Ship ID: {my_ship_id}")

                elif t == "state_update":
                    ships = msg["payload"]["ships"]
                    tick = msg["header"]["tick"]

                    if my_ship_id in ships:
                        s = ships[my_ship_id]
                        cached_state = {
                            "tick": tick,
                            "x": s["x"],
                            "y": s["y"],
                            "vx": s["vx"],
                            "vy": s["vy"],
                            "heading": s.get("heading", 0.0)
                        }

                elif t == "action_request":
                    tick = msg["header"]["tick"]
                    thrust_req, heading_req = choose_action()
                    await send_manual_control(ws, tick, thrust_req, heading_req)

            except Exception as e:
                print(f"Error: {e}")
                break
            
            await asyncio.sleep(0.0001)

if __name__ == "__main__":
    asyncio.run(main())