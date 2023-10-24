import numpy as np


class PIController:
    def __init__(self, kp, ki):
        # PI controller parameters
        self.kp = kp  # Low kp to prevent overshoot
        self.ki = ki  # Lower = more stable, higher = faster response
        self.integral_limit = np.inf
        self.integral = 0.0
        self.process_value = 0.0

    def step(self, p_target, p_observed):
        """Calculate the battery_action of a modified PI controller."""
        self.process_value += self.pi_controller(p_target, p_observed)

        return self.process_value

    def pi_controller(self, setpoint, process_value, dt=1):
        """Calculate the output of a PI controller."""
        error = setpoint - process_value
        self.integral += error * dt
        np.clip(self.integral, -self.integral_limit, self.integral_limit)

        return self.kp * error + self.ki * self.integral
