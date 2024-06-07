from math import cos, sin, sqrt, atan2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from filterpy.kalman import ExtendedKalmanFilter as EKF


def state_transition_function(x, dt):
    """    
    x: State vector [x, y, theta, v_x, v_y, omega, a_x, a_y, alpha]
    Unità di misura: (x, y m; theta rad; v_x, v_y m/s; w rad/s; a_x, a_y m/s**2)
    dt: Time step
    
    Returns the predicted state.
    """
    x_pos, y_pos, theta, v_x, v_y, omega, a_x, a_y, alpha = x
    
    x_pos_new = x_pos + v_x * dt 
    y_pos_new = y_pos + v_y * dt
    theta_new = theta + omega * dt
    v_x_new = v_x + a_x * dt
    v_y_new = v_y + a_y * dt
    omega_new = omega + alpha * dt
   
    
    return np.array([x_pos_new, y_pos_new, theta_new, v_x_new, v_y_new, omega_new, a_x, a_y, alpha])


# Measurement function
def hx(x):
    """
    Returns the measurement vector.
    """
    return x[:8]  # Measurements are for x, y, theta, v_x, v_y, omega, a_x, a_y


def Fjacobian(x, dt):

    F = np.array([

        [1, 0, 0, dt, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, dt, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, dt, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, dt, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, dt, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, dt],
        [0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1]
    ])

    return F


def Hjacobian(x):

    # CASO 1: no data from the uwb (when I have mesurements they are always != 0)
    if z[0] == 0 and z[1] == 0:
        
        # CASO 1.1: row of zeros in the data -> velocities are 0 (odom data)
        if z[2] == 0 and z[3] == 0 and z[4] == 0 and z[5] == 0 and z[6] == 0 and z[7] == 0:  
            jacobian_H = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 1, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 1, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 1, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0], 
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0]])
            
        
        # CASO 1.2: odom data (no imu)
        elif z[2] == 0 and z[6] == 0 and z[7] == 0:
            jacobian_H = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 1, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 1, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 1, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0]])
            
        # CASO 1.3: imu data (no odom)
        elif z[3] == 0 and z[4] == 0 and z[5] == 0:
            jacobian_H = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 1, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 1, 0, 0],
                                   [0, 0, 0, 0, 0, 0, 0, 1, 0]])
            
    
    # CASO 2: uwb data
    elif z[0] != 0 and z[1] != 0:
        jacobian_H = np.array([[1, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 1, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0]])

    return jacobian_H


# Initialize the EKF
ekf = EKF(dim_x=9, dim_z=8)

# Initialize the state 
ekf.x = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0])

ekf.F = np.eye(9)

ekf.P = np.diag([0.01, 0.01, 0.001, 0.01, 0.01, 0.001, 0.01, 0.01, 0.001])  # Initial state covariance 
ekf.Q = np.diag([0.01, 0.01, 0.001, 0.01, 0.01, 0.001, 0.001, 0.001, 0.001])  # Process noise covariance
ekf.R = np.diag([4, 4, 0.00289, 100000000, 100000000, 0.01, 100000000, 100000000])  # Measurement noise covariance


# SENSOR FUSION
sensor_data = pd.read_csv("collected_data.csv")

filter_output_list = []  # state estimates

n = 0
last_t = 0
# Iterate over the sensor data
for index, row in sensor_data.iterrows():
    # Extract measurements 
    z = np.array([row['x'], row['y'], row['yaw'], row['v_x'], row['v_y'], row['w'], row['a_x'], row['a_y']])
    t = row['time']
    dt = t - last_t
    last_t = t  

    # Handle division by zero in dt
    if dt == 0:
        dt = 1e-5  # Small value to avoid division by zero

    # Prediction step
    ekf.x = state_transition_function(ekf.x, dt)
    ekf.F = Fjacobian(ekf.x, dt)
    ekf.predict()

    # Update step 
    ekf.update(z, HJacobian=Hjacobian, Hx=hx)

    # Check for NaNs in the state vector
    if np.isnan(ekf.x).any():
        print(f"NaN detected in state vector n ° {n} at time {t}: {ekf.x}")
        break

    n = n +1
    filter_output_list.append(ekf.x)


filter_output_array = np.array(filter_output_list)
filter_output = pd.DataFrame(filter_output_array, columns=['pos_x', 'pos_y', 'yaw', 'v_x', 'v_y', 'w', 'a_x', 'a_y', 'alpha'])
filter_output.insert(0, 'time', sensor_data.time)

filter_output.to_csv('filter_output.csv')

time_filter = filter_output.time.to_numpy()
x_filter = filter_output.pos_x.to_numpy()
y_filter = filter_output.pos_y.to_numpy()
yaw_filter = filter_output.yaw.to_numpy()
v_x_filter = filter_output.v_x.to_numpy()
v_y_filter = filter_output.v_y.to_numpy()
w_filter = filter_output.w.to_numpy()

# Ground truth data
ground_truth = pd.read_csv("csv/ground_truth_data.csv")  # from the vicon: time, x, y, yaw
ground_truth_vel = pd.read_csv("csv/vicon_velocities.csv")

time_ref = ground_truth.time.to_numpy()
x_ref = ground_truth.x.to_numpy()
y_ref = ground_truth.y.to_numpy()
yaw_ref = ground_truth.yaw.to_numpy()

t_medio_ref = ground_truth_vel.t_medio.to_numpy()
v_x_ref = ground_truth_vel.v_x.to_numpy() 
v_y_ref = ground_truth_vel.v_y.to_numpy() 
w_ref = ground_truth_vel.w.to_numpy()

window_size = 10
v_x_smoothed_serie = ground_truth_vel.v_x.rolling(window=window_size, min_periods=1).mean()
v_x_smoothed = v_x_smoothed_serie.to_numpy()
v_y_smoothed_serie = ground_truth_vel.v_y.rolling(window=window_size, min_periods=1).mean()
v_y_smoothed = v_y_smoothed_serie.to_numpy()
w_smoothed_serie = ground_truth_vel.w.rolling(window=window_size, min_periods=1).mean()
w_smoothed = w_smoothed_serie.to_numpy()

# Plot
plt.plot(time_filter, x_filter, label='Filter')
plt.plot(time_ref, x_ref, color='red', label='Ground truth')
plt.xlabel('Time [sec]')
plt.ylabel('Posiition x [m]')
plt.title('Position x - Filter vs Ground truth')
plt.grid(True)
plt.legend()
plt.show()

plt.plot(time_filter, y_filter, label='Filter')
plt.plot(time_ref, y_ref, color='red', label='Ground truth')
plt.xlabel('Time [sec]')
plt.ylabel('Posiition y [m]')
plt.title('Position y - Filter vs Ground truth')
plt.grid(True)
plt.legend()
plt.show()

plt.plot(time_filter, yaw_filter, label='Filter')
plt.plot(time_ref, yaw_ref, color='red', label='Ground truth')
plt.xlabel('Time [sec]')
plt.ylabel('Theta [rad]')
plt.title('Theta - Filter vs Ground truth')
plt.grid(True)
plt.legend()
plt.show()

plt.plot(time_filter, v_x_filter, label='Filter')
plt.plot(t_medio_ref, v_x_smoothed, color='red', label='Ground truth')
plt.xlabel('Time [sec]')
plt.ylabel('Linear velocity x [m/s]')
plt.title('Linear velocity x - Filter vs Ground truth')
plt.grid(True)
plt.legend()
plt.show()

plt.plot(time_filter, v_y_filter, label='Filter')
plt.plot(t_medio_ref, v_y_smoothed, color='red', label='Ground truth')
plt.xlabel('Time [sec]')
plt.ylabel('Linear velocity y [m/s]')
plt.title('Linear velocity y - Filter vs Ground truth')
plt.grid(True)
plt.legend()
plt.show()

plt.plot(time_filter, w_filter, label='Filter')
plt.plot(t_medio_ref, w_smoothed, color='red', label='Ground truth')
plt.xlabel('Time [sec]')
plt.ylabel('Angular velocity w [rad/s]')
plt.title('Angular velocity w - Filter vs Ground truth')
plt.grid(True)
plt.legend()
plt.show()





