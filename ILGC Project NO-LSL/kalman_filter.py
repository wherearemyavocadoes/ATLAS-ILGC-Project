"""
kalman_filter.py — 1D Kalman filter for ultrasonic distance smoothing.

Filters noisy HC-SR04 readings to produce a stable distance estimate.
Uses a constant-velocity model to track both distance and approach speed.

State vector: [distance, velocity]
    - distance: estimated distance to the nearest object (cm)
    - velocity: rate of change of distance (cm/s, negative = approaching)

The filter also rejects outlier measurements (e.g., sudden jumps
from 50 cm to 400 cm due to sensor multipath or missed echoes).

Run target: Raspberry Pi / Thonny
"""

import time
import numpy as np
import config


class KalmanFilter1D:
    """
    1D Kalman filter with constant-velocity motion model.

    Smooths noisy ultrasonic distance readings and provides
    velocity estimates (useful for predicting collisions.

    We are estimating the state x = [distance, velocity]
    """

    '''
    | Attribute                | Meaning                               |
    | ------------------------ | ------------------------------------- |
    | `self.x`                 | estimated distance + velocity         |
    | `self.P`                 | uncertainty in estimate               |
    | `self.R`                 | sensor noise (ultrasonic error)       |
    | `self.q`                 | motion randomness                     |
    | `self.H`                 | tells what we measure (distance only) |
    | `self.outlier_threshold` | ignore crazy jumps                    |
    | `self._last_time`        | used to compute dt                    |
    | `self._initialized`      | first-time setup flag                 |
    '''

    def __init__(self):
        #State vector: [distance, velocity]
        self.x = np.array([
            config.KALMAN_INITIAL_ESTIMATE,  # initial distance (cm)
            0.0                               # initial velocity (cm/s)
        ], dtype=np.float64) 

        #Error covariance matrix
        self.P = np.array([
            [config.KALMAN_INITIAL_ERROR, 0.0],
            [0.0, config.KALMAN_INITIAL_ERROR]
        ], dtype=np.float64)

        #Measurement noise (scalar — we only measure distance)
        self.R = config.KALMAN_MEASUREMENT_NOISE

        #Process noise base (will be scaled by dt)
        self.q = config.KALMAN_PROCESS_NOISE

        #Measurement matrix: we observe distance only [1, 0]
        self.H = np.array([[1.0, 0.0]], dtype=np.float64)

        #Outlier rejection threshold (cm)
        self.outlier_threshold = config.KALMAN_OUTLIER_THRESHOLD

        #Time tracking
        self._last_time = time.time()

        #Track initialization
        self._initialized = False

    def predict(self, dt): #Two equations taking place in this method: i) x(t+dt) = F * x(t); ii) P(t+dt) = F * P(t) * F.T + Q
        """
        Prediction step: propagate state forward by dt seconds.

        Uses constant-velocity model:
            distance_new = distance + velocity * dt
            velocity_new = velocity  (constant)
        """
        #State transition matrix, A matrix in the prediction equation
        F = np.array([
            [1.0, dt],
            [0.0, 1.0]
        ], dtype=np.float64)

        #Process noise covariance (increases with dt), Error term in the prediction equation
        q_dt = self.q * dt
        Q = np.array([
            [q_dt * dt * dt / 4.0, q_dt * dt / 2.0],
            [q_dt * dt / 2.0,      q_dt]
        ], dtype=np.float64)

        #Predict state and covariance
        self.x = F @ self.x #Getting the predicted state
        self.P = F @ self.P @ F.T + Q #Predicted covariance

    def update(self, measurement): #Two steps occur, first checking for outliers (if found, then continue predicting); ii) Updating the state and covariance
        """
        Full predict-update cycle with a new distance measurement.

        Args:
            measurement (float): Raw ultrasonic distance in cm.

        Returns:
            float: Filtered (smoothed) distance estimate in cm.
        """
        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        #Keeping the time difference between 0.001 to 1.0 (time between two consecutive measurements)
        dt = max(0.001, min(dt, 1.0))

        #First measurement, initialize state directly
        if not self._initialized:
            self.x[0] = measurement
            self.x[1] = 0.0
            self._initialized = True
            return measurement

        #Outlier rejection: ignore readings that jump too far
        #from the current estimate (likely sensor noise/multipath)
        innovation = abs(measurement - self.x[0]) #Surprise term
        if innovation > self.outlier_threshold: #Rejection of outliers
            # Skipping the measurement, just predicting
            self.predict(dt)
            return max(0.0, self.x[0])

        #Predict step
        self.predict(dt)

        #Update step
        #Innovation (measurement residual)
        y = measurement - self.H @ self.x #v = y(t) - H * x(t)

        # Innovation covariance
        S = self.H @ self.P @ self.H.T + self.R #Error in predictions

        # Kalman gain
        K = self.P @ self.H.T / S

        # Update state and covariance
        self.x = self.x + (K * y).flatten()
        I = np.eye(2)
        self.P = (I - K @ self.H) @ self.P

        # Return filtered distance (clamped to non-negative)
        return max(0.0, self.x[0])

    def get_distance(self):
        """Get the current filtered distance estimate."""
        return max(0.0, self.x[0])

    def get_velocity(self):
        """
        Get the estimated velocity (cm/s).

        Negative = object is approaching.
        Positive = object is receding.
        """
        return self.x[1]

    def reset(self):
        """Reset the filter to initial state."""
        self.x = np.array([config.KALMAN_INITIAL_ESTIMATE, 0.0], dtype=np.float64)
        self.P = np.array([
            [config.KALMAN_INITIAL_ERROR, 0.0],
            [0.0, config.KALMAN_INITIAL_ERROR]
        ], dtype=np.float64)
        self._initialized = False
        self._last_time = time.time()


# ──────────────────────────────────────────────
#  Quick test (run this file directly in Thonny)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import random

    kf = KalmanFilter1D()

    print("Kalman Filter Test — Simulated noisy distance readings")
    print("-" * 55)
    print(f"{'Step':>4}  {'True':>8}  {'Noisy':>8}  {'Filtered':>8}  {'Velocity':>8}")
    print("-" * 55)

    # Simulate an object approaching from 200 cm to 30 cm
    true_distance = 200.0

    for step in range(60):
        # Object approaches at ~3 cm/step
        true_distance = max(30.0, true_distance - 3.0)

        # Add noise (±5 cm typical, occasional spike)
        noise = random.gauss(0, 5.0)
        if random.random() < 0.05:  # 5% chance of outlier spike
            noise = random.choice([-50, 50, 100])

        noisy = true_distance + noise
        noisy = max(2.0, noisy)

        # Filter
        filtered = kf.update(noisy)
        velocity = kf.get_velocity()

        print(f"{step:4d}  {true_distance:8.1f}  {noisy:8.1f}  {filtered:8.1f}  {velocity:8.1f}")

        time.sleep(0.05)

    print("-" * 55)
    print("Done. Notice how the filter tracks the true distance")
    print("and rejects the outlier spikes.")
