"""
Hohmann Transfer Orbit Simulation

This script simulates a Hohmann transfer maneuver, which is an efficient orbital transfer
method that uses two burns: one to enter an elliptical transfer orbit, and another to
circularize at the destination orbit. The transfer is optimized for minimum delta-v.
"""

import environment
import numpy as np
import matplotlib.pyplot as plt

# Tolerance values for detecting when we're at the target radius and at an apsis
TARGET_RADIUS_TOLERANCE = 0.0005  # How close we need to be to target radius to trigger second burn
APSIS_TOLERANCE = 0.0005  # How close we need to be to periapsis/apoapsis

# Initialize the orbital environment
env = environment.OrbitalEnvironment()

# Get initial state from environment
init_state = env.reset()
x_init, y_init, vx_init, vy_init = init_state[0], init_state[1], init_state[2], init_state[3]
init_r = np.sqrt(x_init**2 + y_init**2)
r_destination = 1.0  # Target orbit radius

# Extract environment parameters
GM = env.GM  # Gravitational parameter (G * M)
dt = env.dt  # Time step for simulation

# Define initial and destination radii
r1 = init_r
r2 = r_destination

# Calculate initial velocity components
v_init = np.sqrt(vx_init**2 + vy_init**2)
# Tangential velocity component (perpendicular to radius vector)
v_tangential_init = (x_init * vy_init - y_init * vx_init) / r1 if r1 > 1e-5 else 0

# Determine transfer direction: inward (to smaller radius) or outward (to larger radius)
going_inward = r1 > r2

# Calculate circular orbit velocity at initial radius
v1_circular = np.sqrt(GM / r1)

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

# Calculate circular orbit velocity at destination radius
v2_circular = np.sqrt(GM / r2)

# Convert delta-v to acceleration (delta-v per timestep)
a_1 = delta_v1 / dt
a_2 = delta_v2 / dt

# Calculate transfer time using Kepler's third law
# For a Hohmann transfer (half an ellipse), the time is half the orbital period
transfer_time = np.pi * np.sqrt(a_transfer**3 / GM)
transfer_steps = int(transfer_time / dt)

# Initialize burn tracking variables
first_burn_applied = False
second_burn_applied = False
first_burn_timestep = None
second_burn_timestep = None
a_2_actual = None  # Will be calculated when we reach the target radius

# Initialize tracking variables for apsis detection
if going_inward:
    min_r_reached = r1 * 10  # Start with a large value to track minimum radius (periapsis)
    prev_r = r1
    radii_window = []  # Sliding window to detect when we're at an extremum
else:
    max_r_reached = r1  # Start with initial radius to track maximum radius (apoapsis)
    prev_r = r1
    radii_window = []

# Store all states for visualization
states = [init_state.copy()]

# Store positions where burns occur
first_burn_pos = None
second_burn_pos = None

# Main simulation loop: execute the Hohmann transfer
for i in range(env.max_steps):
    # Get current state from environment
    x, y, vx, vy = env.x, env.y, env.vx, env.vy
    r = np.sqrt(x**2 + y**2)  # Current distance from center
    v = np.sqrt(vx**2 + vy**2)  # Current speed
    # Tangential velocity component (perpendicular to radius vector)
    v_tangential = (x * vy - y * vx) / r if r > 1e-5 else 0
    
    # Phase 1: Apply first burn to enter transfer orbit
    if not first_burn_applied:
        first_burn_pos = (x, y)
        state, _, _ = env.step(np.array([a_1]))  # Apply acceleration for first burn
        first_burn_applied = True
        first_burn_timestep = i
    
    # Phase 2: Travel along transfer orbit and detect when to apply second burn
    elif not second_burn_applied:
        # Maintain a sliding window of recent radii to detect apsis (extremum)
        radii_window.append(r)
        if len(radii_window) > 20:
            radii_window.pop(0)
        
        # Check if we're approaching the target radius (loose tolerance for early detection)
        is_near_target = abs(r - r2) < TARGET_RADIUS_TOLERANCE * 200
        # Ensure we're past the midpoint of the transfer to avoid premature burns
        is_past_midpoint = i > transfer_steps * 0.3
        
        # Initialize variables for burn condition detection
        is_near_min = False
        is_near_max = False
        is_increasing = False
        is_decreasing = False
        burn_condition = False
        apsis_name = ""
        apsis_r = r
        
        # Detect apsis and determine when to apply second burn
        if going_inward:
            # Track minimum radius reached (periapsis)
            if r < min_r_reached:
                min_r_reached = r
            
            # Check if we're close to target radius
            is_close_to_target = abs(r - r2) < TARGET_RADIUS_TOLERANCE
            # Check if we're near the minimum radius (periapsis)
            is_near_min = abs(r - min_r_reached) < APSIS_TOLERANCE
            
            # Use sliding window to detect if we're at a local minimum
            if len(radii_window) >= 3:
                recent_min = min(radii_window[-3:])
                is_at_minimum = r <= recent_min * 1.001
            else:
                is_at_minimum = True
            
            # Second burn should occur at periapsis (minimum radius) when near target
            burn_condition = is_close_to_target and is_at_minimum and is_past_midpoint
            apsis_name = "periapsis"
            apsis_r = min_r_reached
        else:
            # Track maximum radius reached (apoapsis)
            if r > max_r_reached:
                max_r_reached = r
            
            # Check if we're close to target radius
            is_close_to_target = abs(r - r2) < TARGET_RADIUS_TOLERANCE
            # Check if we're near the maximum radius (apoapsis)
            is_near_max = abs(r - max_r_reached) < APSIS_TOLERANCE
            
            # Use sliding window to detect if we're at a local maximum
            if len(radii_window) >= 3:
                recent_max = max(radii_window[-3:])
                is_at_maximum = r >= recent_max * 0.999
            else:
                is_at_maximum = True
            
            # Second burn should occur at apoapsis (maximum radius) when near target
            burn_condition = is_close_to_target and is_at_maximum and is_past_midpoint
            apsis_name = "apoapsis"
            apsis_r = max_r_reached
        
        # Phase 3: Apply second burn to circularize at destination orbit
        if burn_condition:
            # Calculate the actual delta-v needed based on current velocity
            # This accounts for any deviations from the ideal transfer orbit
            if going_inward:
                v_transfer_at_r = np.sqrt(GM * (2/r - 1/a_transfer))
                v_circular_target = np.sqrt(GM / r2)
                delta_v2_actual = v_circular_target - v_tangential
                a_2_actual = delta_v2_actual / dt
            else:
                v_transfer_at_r = np.sqrt(GM * (2/r - 1/a_transfer))
                v_circular_target = np.sqrt(GM / r2)
                delta_v2_actual = v_circular_target - v_tangential
                a_2_actual = delta_v2_actual / dt
            
            second_burn_pos = (x, y)
            state, _, _ = env.step(np.array([a_2_actual]))  # Apply acceleration for second burn
            second_burn_applied = True
            second_burn_timestep = i
        else:
            # Coast along transfer orbit (no acceleration)
            state, _, _ = env.step(np.array([0.0]))
    else:
        # Phase 4: After both burns, continue coasting in circular orbit
        state, _, _ = env.step(np.array([0.0]))

    # Store state for visualization
    states.append(state.copy())
    prev_r = r

# Calculate final state metrics
x_final, y_final, vx_final, vy_final = states[-1][0], states[-1][1], states[-1][2], states[-1][3]
r_final = np.sqrt(x_final**2 + y_final**2)
v_final = np.sqrt(vx_final**2 + vy_final**2)
# Tangential velocity (perpendicular to radius vector)
v_tangential_final = (x_final * vy_final - y_final * vx_final) / r_final if r_final > 1e-5 else 0
# Radial velocity (along radius vector)
v_radial_final = (x_final * vx_final + y_final * vy_final) / r_final if r_final > 1e-5 else 0

# Print final state summary
print(f"\n{'='*60}")
print("FINAL STATE")
print(f"{'='*60}")
print(f"  Position: ({x_final:.4f}, {y_final:.4f})")
print(f"  Velocity: ({vx_final:.4f}, {vy_final:.4f})")
print(f"  Radius (r): {r_final:.4f} (target: {r2:.4f}, error: {abs(r_final-r2):.4f})")
print(f"  Speed: {v_final:.4f} (expected circular: {v2_circular:.4f})")
print(f"  Tangential velocity (v_tang): {v_tangential_final:.4f} (expected: {v2_circular:.4f})")
print(f"  Radial velocity (v_radial): {v_radial_final:.4f}")
print(f"  Total steps: {len(states)}")
print(f"  First burn applied: {first_burn_applied}")
print(f"  Second burn applied: {second_burn_applied}")
if first_burn_timestep is not None:
    print(f"  First burn acceleration (a_1): {a_1:.4f}")
    print(f"  First burn timestep: {first_burn_timestep}")
if second_burn_timestep is not None and a_2_actual is not None:
    print(f"  Second burn acceleration (a_2): {a_2_actual:.4f}")
    print(f"  Second burn timestep: {second_burn_timestep}")
print(f"{'='*60}\n")

def plot_orbit(states, first_burn_pos=None, second_burn_pos=None):
    """
    Visualize the Hohmann transfer orbit.
    
    Args:
        states: List of state vectors [x, y, vx, vy] throughout the simulation
        first_burn_pos: Tuple (x, y) position where first burn occurred
        second_burn_pos: Tuple (x, y) position where second burn occurred
    """
    # Extract x and y coordinates from states
    x_coords = [state[0] for state in states]
    y_coords = [state[1] for state in states]
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Plot the spacecraft trajectory
    ax.plot(x_coords, y_coords, 'b-', linewidth=1.5, alpha=0.5, label='Spacecraft trajectory')
    
    # Mark first burn location (yellow star)
    if first_burn_pos is not None:
        ax.plot(first_burn_pos[0], first_burn_pos[1], 'y*', markersize=15, 
                label='First burn', zorder=6, markeredgecolor='orange', markeredgewidth=1)
    
    # Mark second burn location (magenta star)
    if second_burn_pos is not None:
        ax.plot(second_burn_pos[0], second_burn_pos[1], 'm*', markersize=15, 
                label='Second burn', zorder=6, markeredgecolor='purple', markeredgewidth=1)
    
    # Draw reference circles for initial and destination orbits
    theta = np.linspace(0, 2*np.pi, 100)
    r1 = np.sqrt(x_coords[0]**2 + y_coords[0]**2)
    r2 = 1.0
    
    # Initial orbit circle (green dashed)
    x_circle1 = r1 * np.cos(theta)
    y_circle1 = r1 * np.sin(theta)
    ax.plot(x_circle1, y_circle1, 'g--', linewidth=1, alpha=0.5, label=f'Initial orbit (r={r1:.2f})')
    
    # Destination orbit circle (red dashed)
    x_circle2 = r2 * np.cos(theta)
    y_circle2 = r2 * np.sin(theta)
    ax.plot(x_circle2, y_circle2, 'r--', linewidth=1, alpha=0.5, label=f'Destination orbit (r={r2:.2f})')
    
    # Mark the central body (blackhole)
    ax.plot(0, 0, 'ko', markersize=10, label='Blackhole', zorder=5)
    
    # Set plot limits with some padding
    max_extent = max(max(abs(x) for x in x_coords), max(abs(y) for y in y_coords))
    max_extent *= 1.1
    ax.set_xlim(-max_extent, max_extent)
    ax.set_ylim(-max_extent, max_extent)
    
    # Make plot square (equal aspect ratio) for proper orbital visualization
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_xlabel('X position')
    ax.set_ylabel('Y position')
    ax.set_title('Hohmann Transfer Orbit')
    
    plt.tight_layout()
    plt.show()

plot_orbit(states, first_burn_pos, second_burn_pos)