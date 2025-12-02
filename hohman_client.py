import asyncio
import json
import websockets
import uuid
import time
import math
import numpy as np

# Note that in order for this to run without external influence, we need to not have the
# Baseline AI ship in the environment

WS_URL = "ws://10.37.117.236:5500/ws"
SHIP_NAME = "PythonHohmann"

# Tolerance values for detecting when we're at the target radius and at an apsis
TARGET_RADIUS_TOLERANCE = 0.0005  # How close we need to be to target radius to trigger second burn
APSIS_TOLERANCE = 0.0005  # How close we need to be to periapsis/apoapsis

GM = 1.0
dt = 0.01
TARGET_RADIUS = 2.0 # note that the code currently only works if target radius is bigger than current radius

first_burn_applied = False
second_burn_applied = False
a1 = None
a2 = None

hohmann_ready = False
cached_state = None
my_ship_id = None
burn_phase = 0

def compute_radius(x, y):
    return math.sqrt(x*x + y*y)

def compute_tangential_velocity(x, y, vx, vy):
    r = compute_radius(x,y)
    return (x*vy - y*vx)/r if r > 1e-5 else 0


def initialize_hohmann(x, y, vx, vy):
    global hohmann_ready, a1, a2

    r1 = compute_radius(x, y)
    r2 = TARGET_RADIUS
    v_tangential_init = compute_tangential_velocity(x, y, vx, vy)

    # Determine transfer direction: inward (to smaller radius) or outward (to larger radius)
    going_inward = r1 > r2

    # Calculate semi-major axis of the Hohmann transfer ellipse
    # For a Hohmann transfer, the semi-major axis is the average of the two radii
    a_transfer = (r1 + r2) / 2

    # Calculate velocities needed for the transfer orbit using vis-viva equation
    # v = sqrt(GM * (2/r - 1/a)) where r is current radius and a is semi-major axis
    if going_inward:
        # Velocity at periapsis (r1) of transfer ellipse
        v1_transfer = np.sqrt(GM * (2/r1 - 1/a_transfer))
        # Velocity at apoapsis (r2) of transfer ellipse
        v2_transfer = np.sqrt(GM * (2/r2 - 1/a_transfer))
        
        # Delta-v required for first burn: speed up to enter transfer orbit
        delta_v1 = v1_transfer - v_tangential_init
        # Delta-v required for second burn: speed up to circularize at destination
        delta_v2 = np.sqrt(GM / r2) - v2_transfer
    else:
        # Same calculations for outward transfer
        v1_transfer = np.sqrt(GM * (2/r1 - 1/a_transfer))
        v2_transfer = np.sqrt(GM * (2/r2 - 1/a_transfer))
        
        # Delta-v required for first burn: speed up to enter transfer orbit
        delta_v1 = v1_transfer - v_tangential_init
        # Delta-v required for second burn: slow down to circularize at destination
        delta_v2 = np.sqrt(GM / r2) - v2_transfer

    # Convert delta-v to acceleration (delta-v per timestep)
    a1 = delta_v1 / dt
    a2 = delta_v2 / dt

    print("\n HOHMANN INITIALIZED")
    print(f"r1   = {r1:.4f}")
    print(f"delta_v1  = {delta_v1:.6f}")
    print(f"delta_v2  = {delta_v2:.6f}")
    print(f"a1   = {a1:.6f}")
    print(f"a2   = {a2:.6f}")
    print("======================\n")

    hohmann_ready = True


def choose_thrust():
    global first_burn_applied, second_burn_applied, burn_phase

    if cached_state is None:
        burn_phase = 0
        return 0.0

    x = cached_state["x"]
    y = cached_state["y"]
    vx = cached_state["vx"]
    vy = cached_state["vy"]
    tick = cached_state["tick"]

    r = compute_radius(x,y)
    v_tan = compute_tangential_velocity(x,y,vx,vy)
    v_rad = (x*vx + y*vy) / r if r > 1e-5 else 0

    # Phase 0: Initialize Hohmann from first real state
    if not hohmann_ready:
        burn_phase = 0
        initialize_hohmann(x, y, vx, vy)
        # don't thrust on the same tick, just wait for next tick
        return 0.0

    # Phase 1: Apply first burn to enter transfer orbit
    if not first_burn_applied:
        first_burn_applied = True
        burn_phase = 1
        print(f"[{tick}] FIRST BURN at r={r:.4f}, thrust={a1:.4f}")
        return a1

    # detect apsis
    prev_v_rad = getattr(choose_thrust, "prev_v_rad", v_rad)
    choose_thrust.prev_v_rad = v_rad

    sign_flip = (prev_v_rad > 0 and v_rad < 0) or (prev_v_rad < 0 and v_rad > 0)
    near_target = abs(r - TARGET_RADIUS) < 0.01

    # Phase 2: Travel along transfer orbit and detect when to apply second burn
    if not second_burn_applied:
        # detect apsis (radial velocity sign flip)
        prev_vr = getattr(choose_thrust, "prev_vr", v_rad)
        choose_thrust.prev_vr = v_rad
        sign_flip = (prev_vr > 0 and v_rad < 0) or \
                    (prev_vr < 0 and v_rad > 0)

        if sign_flip: #and near_target:
            # Phase 3: Apply second burn to circularize at destination orbit
            # Calculate the actual delta-v needed based on current velocity
            # This accounts for any deviations from the ideal transfer orbit
            v_circular_target = math.sqrt(GM / TARGET_RADIUS)
            delta_v2_actual = v_circular_target - v_tan
            a_2_actual = delta_v2_actual / dt

            burn_phase = 2
            print(f"[{tick}] SECOND BURN at x={x:.4f}, y={y:.4f}")
            print(f"    dv2_actual={delta_v2_actual:.5f}, thrust={a_2_actual:.4f}")
            second_burn_applied = True
            return a_2_actual

        # Continue coasting
        burn_phase = 0
        return 0.0

    # Phase 3: After both burns, continue coasting in circular orbit
    burn_phase = 0
    return 0.0

async def send_action(ws, tick, thrust):
    msg = {
        "header": {
            "version": "1.0",
            "type": "manual_action",
            "tick": tick,
            "timestamp": time.time(),
            "client_id": str(uuid.uuid4())
        },
        "payload": {
            "turn": 0.0,
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

        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            t = msg["header"]["type"]

            if t == "mode_confirmed":
                my_ship_id = msg["payload"].get("ship_id", my_ship_id)

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
                        "vy": s["vy"]
                    }

            elif t == "action_request":
                tick = msg["header"]["tick"]
                if cached_state is None:
                    await send_action(ws, tick, 0.0)
                    continue
                thrust = choose_thrust()
                await send_action(ws, tick, thrust)

            await asyncio.sleep(0.0001)


asyncio.run(main())