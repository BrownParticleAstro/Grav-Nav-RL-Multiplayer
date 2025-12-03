import numpy as np
import gym
from gym import spaces

# OrbitalEnvironment simulates a 2D gravitational orbital system.
# Takes the gravitational constant (GM), initial radius (r0), initial velocity (v0), time step (dt),
# maximum simulation steps, and an optional reward function.
# Outputs the current state after each step (x, y, vx, vy) and reward.
class OrbitalEnvironment:
    def __init__(self, GM=1.0, r0=None, v0=1.0, dt=0.01, max_steps=5000, reward_function=None):
        """
        Args:
            GM: Gravitational constant (float).
            r0: Initial orbital radius (float). If None, a random value is generated.
            v0: Initial velocity (float).
            dt: Time step for the simulation (float).
            max_steps: Maximum number of simulation steps (int).
            reward_function: Optional function for calculating rewards. Defaults to exponential radial difference.

        Returns:
            None. Initializes the orbital environment state.
        """
        self.GM = GM
        self.dt = dt
        self.init_r = r0 if r0 is not None else np.random.uniform(0.2, 4.0)
        self.enforce_r = True if r0 is not None else False
        self.x = self.init_r
        self.y = 0.0
        self.vx = 0.0
        self.vy = np.sqrt(self.GM / self.init_r)
        self.max_steps = max_steps
        self.current_step = 0
        self.reward_function = reward_function or self.default_reward
        self.reset()

    def reset(self):
        """
        Resets the environment to the initial state.
        Returns: Initial state as a numpy array (x, y, vx, vy).
        """
        self.x = self.init_r if self.enforce_r else np.random.uniform(0.2, 4.0)
        self.y = 0.0
        self.vx = 0.0
        self.vy = np.sqrt(self.GM / self.init_r)
        self.current_step = 0
        state = np.array([self.x, self.y, self.vx, self.vy])
        return state
    
    def step(self, action):
        """
        Advances the environment state by one timestep using Runge-Kutta (RK4) integration.
        Args:
            action: Tangential thrust value (float).

        Returns:
            Tuple of (new state, reward, done):
            - new state: Updated state (x, y, vx, vy) as a numpy array.
            - reward: Calculated reward based on the current state and action.
            - done: Boolean indicating whether the simulation is complete.
        """
        
        # Helper to compute acceleration (gravity)
        def acceleration(state):
            x, y = state[:2]
            dist = np.sqrt(x**2 + y**2)
            dist = np.clip(dist, 1e-5, 5.0)
            rhat = np.array([x, y]) / dist
            return -self.GM / (dist**2) * rhat

        # State format: [x, y, vx, vy]
        state = np.array([self.x, self.y, self.vx, self.vy])

        # RK4 integration steps
        # k1
        k1_v = self.dt * acceleration(state)
        k1_p = self.dt * np.array([self.vx, self.vy])
        
        # k2
        state_mid = state + 0.5 * np.concatenate([k1_p, k1_v])
        k2_v = self.dt * acceleration(state_mid)
        k2_p = self.dt * np.array([self.vx + 0.5 * k1_v[0], self.vy + 0.5 * k1_v[1]])
        
        # k3
        state_mid = state + 0.5 * np.concatenate([k2_p, k2_v])
        k3_v = self.dt * acceleration(state_mid)
        k3_p = self.dt * np.array([self.vx + 0.5 * k2_v[0], self.vy + 0.5 * k2_v[1]])
        
        # k4
        state_end = state + np.concatenate([k3_p, k3_v])
        k4_v = self.dt * acceleration(state_end)
        k4_p = self.dt * np.array([self.vx + k3_v[0], self.vy + k3_v[1]])

        # Weighted average update
        self.vx += (k1_v[0] + 2*k2_v[0] + 2*k3_v[0] + k4_v[0]) / 6
        self.vy += (k1_v[1] + 2*k2_v[1] + 2*k3_v[1] + k4_v[1]) / 6
        self.x  += (k1_p[0] + 2*k2_p[0] + 2*k3_p[0] + k4_p[0]) / 6
        self.y  += (k1_p[1] + 2*k2_p[1] + 2*k3_p[1] + k4_p[1]) / 6

        # Apply Thrust
        action = np.array([0, action[0]])  # Tangential thrust only
        dist = np.sqrt(self.x**2 + self.y**2)
        dist = max(dist, 1e-5)  
        rhat = np.array([self.x, self.y]) / dist
        rotation_matrix = np.array([[rhat[0], -rhat[1]], [rhat[1], rhat[0]]])
        thrust = rotation_matrix @ action

        self.vx += thrust[0] * self.dt
        self.vy += thrust[1] * self.dt

        # Update state
        state = np.array([self.x, self.y, self.vx, self.vy])

        # Update reward
        reward = self.reward_function(action[1])

        # Check if the episode is done
        done = dist > 5.0 or dist < 0.1 or self.current_step >= self.max_steps
        self.current_step += 1

        return state, reward, done

    def default_reward(self, action):
        r = np.sqrt(self.x**2 + self.y**2)
        r_err = r - 1.0
        r_max_err = max(abs(self.init_r - 1), 1e-2)
        scaled_r_err = np.clip((r_err / r_max_err) * 2, -2, 2)
        reward = np.exp(-scaled_r_err**2)
        action_penalty = np.exp(-action**2)
        return reward * action_penalty

class OrbitalEnvWrapper(gym.Env):
    def __init__(self, r0=None, reward_function=None):
        super(OrbitalEnvWrapper, self).__init__()
        self.env = OrbitalEnvironment(r0=r0, reward_function=reward_function)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(9,), dtype=np.float32)
        self.state = None
        self.episode_data = []
        self.prev_r_err = None
        self.integral_r_err = 0.0

    def reset(self):
        self.episode_data = []
        self.state = self.env.reset()
        self.prev_r_err = None
        self.integral_r_err = 0.0
        return self._convert_state(self.state, 0.0, 0.0)

    def step(self, action):
        self.state, base_reward, done = self.env.step(action)

        # Extract state variables
        x, y, vx, vy = self.state[0], self.state[1], self.state[2], self.state[3]
        r = np.sqrt(x**2 + y**2)
        t = self.env.current_step * self.env.dt

        # Constants for Hohmann transfer
        r_initial = self.env.init_r
        r_final = 1.0
        transfer_time = np.pi * np.sqrt(((r_initial + r_final) / 2)**3 / self.env.GM)

        # Compute expected radius (Target)
        if t < transfer_time:
            a_transfer = (r_initial + r_final) / 2
            e_transfer = (r_final - r_initial) / (r_final + r_initial)
            n_transfer = np.sqrt(self.env.GM / a_transfer**3)
            M = n_transfer * t
            E = M  # Approximation for small eccentricities
            theta = 2 * np.arctan2(np.sqrt(1 + e_transfer) * np.sin(E / 2),
                                np.sqrt(1 - e_transfer) * np.cos(E / 2))
            r_expected = a_transfer * (1 - e_transfer**2) / (1 + e_transfer * np.cos(theta))
        else:
            r_expected = r_final

        # Compute errors
        r_err = r - r_expected
        d_r_err = (r_err - self.prev_r_err) / self.env.dt if self.prev_r_err is not None else 0.0
        self.prev_r_err = r_err
        self.integral_r_err += r_err * self.env.dt
        max_timesteps_passed = self.env.max_steps * self.env.dt

        # Normalize errors
        r_err_norm = r_err / r_expected
        d_r_err_norm = d_r_err / (r_expected / transfer_time)
        int_r_err_norm = self.integral_r_err / (r_expected * max_timesteps_passed)

        # Penalties
        time_factor = t / max_timesteps_passed
        k1, k2, k3 = 1.0, 1.0, 1.0
        penalty_r_err = np.exp(-k1 * abs(r_err_norm) * (1 + time_factor))
        penalty_d_r_err = np.exp(-k2 * abs(d_r_err_norm) * (1 + time_factor))
        penalty_int_r_err = np.exp(-k3 * abs(int_r_err_norm) * (1 + time_factor))

        base_reward = 1.0
        reward = base_reward * penalty_r_err * penalty_d_r_err * penalty_int_r_err
        min_reward = 0.01
        reward = max(reward, min_reward)

        if r > 2 * r_final or r < r_initial / 2:
            reward = min_reward

        self.episode_data.append([
            x, y, vx, vy, reward, action[0], r_err_norm, d_r_err_norm, int_r_err_norm
        ])

        info = {
            "state": (x, y, vx, vy),
            "r_err_norm": r_err_norm,
            "d_r_err_norm": d_r_err_norm,
            "int_r_err_norm": int_r_err_norm
        }

        observation = self._convert_state(self.state, d_r_err_norm, int_r_err_norm)
        return observation, reward, done, info

    def _convert_state(self, state, d_r_err_norm, int_r_err_norm):
        x, y, vx, vy = state
        r = np.sqrt(x**2 + y**2)
        r = max(r, 1e-5)
        v_radial = (x * vx + y * vy) / r
        v_tangential = (x * vy - y * vx) / r
        initial_r = self.env.init_r
        flag = 1.0 if np.abs(r - 1.0) < 0.01 else 0.0
        specific_energy = 0.5 * (vx**2 + vy**2) - self.env.GM / r
        angular_momentum = r * v_tangential

        r_err = r - 1.0
        r_max_err = max(abs(self.env.init_r - 1), 1e-2)
        scaled_r_err = np.clip((r_err / r_max_err) * 2, -2, 2)

        state = np.array([
            scaled_r_err,
            v_radial,
            v_tangential,
            1 - initial_r,
            flag,
            specific_energy,
            angular_momentum,
        ], dtype=np.float32)

        return state


class MultiShipOrbitalEnvironment:
    """
    Manages multiple ships in a shared orbital environment, where each ship can be controlled independently
    and all ships interact gravitationally.
    """
    def __init__(self, GM=1.0, dt=0.01, max_steps=None):
        self.GM = GM
        self.dt = dt
        self.max_steps = max_steps
        self.ships = {}  # ship_id: state dict
        self.current_step = 0

    def add_ship(self, ship_id, r0=None, v0=1.0, control_type='ai'):
        if r0 is None:
            r0 = np.random.uniform(0.2, 4.0)
            
        x = r0
        y = 0.0
        vx = 0.0
        vy = np.sqrt(self.GM / r0)
        self.ships[ship_id] = {
            'x': x, 'y': y, 'vx': vx, 'vy': vy, 'init_r': r0, 'done': False,
            'control_type': control_type,  # 'ai' or 'manual'
            'heading': 0.0,
            'thrust': 0.0,
            'turn_rate': 0.0,
            'steps': 0,
            'tangential_thrust': 0.0
        }

    def remove_ship(self, ship_id):
        if ship_id in self.ships:
            del self.ships[ship_id]
    
    def reset(self):
        self.ships.clear()
        self.current_step = 0

    def step(self, actions):
        """
        actions: dict of {ship_id: action}
        """
        # Gather all positions for mutual gravity
        positions = {sid: (s['x'], s['y']) for sid, s in self.ships.items() if not s['done']}
        
        for ship_id, ship in self.ships.items():
            if ship['done']:
                continue
                
            ship['steps'] += 1
                
            if ship['control_type'] == 'ai':
                action = actions.get(ship_id, 0.0)
                self._apply_ai_control(ship, action)

            elif ship['control_type'] == 'manual':
                action = actions.get(ship_id, {'turn': 0.0, 'thrust': 0.0})
                self._apply_manual_control(ship, action)
            
            # Apply physics with corrected RK4
            self._apply_physics(ship, positions, ship_id)
            
            dist = np.sqrt(ship['x']**2 + ship['y']**2)
            if dist > 5.0 or dist < 0.1:
                ship['done'] = True
                
        self.current_step += 1

    def _apply_ai_control(self, ship, action):
        ship['tangential_thrust'] = action

    def _apply_manual_control(self, ship, action):
        ship['turn_rate'] = action.get('turn', 0.0)
        ship['heading'] += ship['turn_rate'] * self.dt
        ship['thrust'] = action.get('thrust', 0.0)
        
        if 'heading' not in ship:
            ship['heading'] = 0.0

    def _compute_acc(self, x, y, ship_id, positions):
        """Helper to calculate total acceleration at a specific position"""
        # 1. Central Gravity
        dist = np.sqrt(x**2 + y**2)
        dist = max(dist, 1e-5)
        rhat = np.array([x, y]) / dist
        acc = -self.GM / (dist**2) * rhat
        
        # 2. Ship-to-Ship Gravity (Perturbations)
        for other_id, (ox, oy) in positions.items():
            # Skip self-gravity
            if ship_id == other_id:
                continue
                
            dx, dy = ox - x, oy - y
            odist = np.sqrt(dx**2 + dy**2)
            
            if odist < 1e-3: continue # Collision/overlap safety
            
            o_rhat = np.array([dx, dy]) / odist
            # Add small pull from other ships (Mass = 0.1 * CentralStar)
            acc += (self.GM * 0.1) / (odist**2) * o_rhat
            
        return acc

    def _apply_physics(self, ship, positions, ship_id):
        """Apply physics using Proper RK4 Integration"""
        x, y = ship['x'], ship['y']
        vx, vy = ship['vx'], ship['vy']
        
        # Define the thrust vector (constant during the timestep)
        thrust_acc = np.array([0.0, 0.0])
        
        if ship['control_type'] == 'ai':
            # AI uses tangential thrust
            t_thrust = ship.get('tangential_thrust', 0.0)
            dist = np.sqrt(x**2 + y**2)
            if dist > 1e-5:
                rhat = np.array([x, y]) / dist
                # Rotate 90 degrees for tangent
                rotation_matrix = np.array([[rhat[0], -rhat[1]], [rhat[1], rhat[0]]])
                thrust_acc = rotation_matrix @ np.array([0, t_thrust])
                
        elif ship['control_type'] == 'manual':
            # Manual uses heading
            if ship.get('thrust', 0) > 0:
                h = ship['heading']
                thrust_acc = np.array([np.cos(h), np.sin(h)]) * ship['thrust']

        # --- RK4 INTEGRATION ---
        # Recalculate acceleration at each RK step using _compute_acc
        
        # k1
        a1 = self._compute_acc(x, y, ship_id, positions) + thrust_acc
        k1_v = self.dt * a1
        k1_p = self.dt * np.array([vx, vy])
        
        # k2
        mid_x = x + 0.5 * k1_p[0]
        mid_y = y + 0.5 * k1_p[1]
        a2 = self._compute_acc(mid_x, mid_y, ship_id, positions) + thrust_acc
        k2_v = self.dt * a2
        k2_p = self.dt * np.array([vx + 0.5 * k1_v[0], vy + 0.5 * k1_v[1]])
        
        # k3
        mid_x = x + 0.5 * k2_p[0]
        mid_y = y + 0.5 * k2_p[1]
        a3 = self._compute_acc(mid_x, mid_y, ship_id, positions) + thrust_acc
        k3_v = self.dt * a3
        k3_p = self.dt * np.array([vx + 0.5 * k2_v[0], vy + 0.5 * k2_v[1]])
        
        # k4
        end_x = x + k3_p[0]
        end_y = y + k3_p[1]
        a4 = self._compute_acc(end_x, end_y, ship_id, positions) + thrust_acc
        k4_v = self.dt * a4
        k4_p = self.dt * np.array([vx + k3_v[0], vy + k3_v[1]])
        
        # Weighted Sum
        vx += (k1_v[0] + 2*k2_v[0] + 2*k3_v[0] + k4_v[0]) / 6.0
        vy += (k1_v[1] + 2*k2_v[1] + 2*k3_v[1] + k4_v[1]) / 6.0
        x  += (k1_p[0] + 2*k2_p[0] + 2*k3_p[0] + k4_p[0]) / 6.0
        y  += (k1_p[1] + 2*k2_p[1] + 2*k3_p[1] + k4_p[1]) / 6.0
        
        # Update ship state
        ship['x'], ship['y'] = x, y
        ship['vx'], ship['vy'] = vx, vy

    def get_states(self):
        """
        Returns a dict of {ship_id: {'x':..., 'y':..., 'vx':..., 'vy':...}}
        """
        return {sid: dict(s) for sid, s in self.ships.items()}