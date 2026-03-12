#!/usr/bin/env python3
"""K1-specific MuJoCo ROS2 node that extends MujocoRosNode with low_state publishing."""
import numpy as np
from std_msgs.msg import Float32MultiArray
from booster_interface.msg import LowState, ImuState, MotorState, LowCmd
from .general import General


class K1(General):
    """K1-specific MuJoCo ROS2 node with low_state publishing for booster_interface compatibility."""

    def __init__(self):
        """Initialize K1 node with low_state publishing capabilities."""
        # Call parent constructor
        super().__init__()

        # Declare and read ROS2 parameter for low_state publishing frequency
        self.declare_parameter('low_state_pub_freq', 0.0)
        low_state_pub_freq = self.get_parameter('low_state_pub_freq').get_parameter_value().double_value
        self.low_state_pub_freq = low_state_pub_freq

        # Store last tau for tau_est in motor states
        self.tau_last = np.zeros((self.act_dim,), dtype=np.float32)
        
        # Store impedance control parameters from LowCmd message
        self.kp_cmd = np.zeros((self.act_dim,), dtype=np.float32)
        self.kd_cmd = np.zeros((self.act_dim,), dtype=np.float32)
        self.tau_cmd = np.zeros((self.act_dim,), dtype=np.float32)

        # Publisher for low_state
        self.pub_low_state = self.create_publisher(
            LowState,
            'low_state',
            10)

        # Timer for low_state publication
        self.low_state_timer = self.create_timer(
            1.0 / max(1e-6, self.low_state_pub_freq), self._low_state_timer_cb
        )

        # Override subscription: destroy parent's rl2pd subscription and use low_cmd instead
        self.destroy_subscription(self.sub)
        self.sub_low_cmd = self.create_subscription(
            LowCmd,
            'joint_ctrl',
            # 'rl2pd',
            self.low_cmd_callback,
            10)

        self.get_logger().info(
            f'K1 Mujoco node initialized with low_state publishing at {self.low_state_pub_freq} Hz'
        )

    def low_cmd_callback(self, msg: LowCmd):
        """Override: receive LowCmd and extract impedance control parameters."""
        # Extract q, kp, kd, and tau from each MotorCmd for impedance control
        q_targets = np.array([m.q for m in msg.motor_cmd], dtype=np.float32)
        kp_values = np.array([m.kp for m in msg.motor_cmd], dtype=np.float32)
        kd_values = np.array([m.kd for m in msg.motor_cmd], dtype=np.float32)
        tau_values = np.array([m.tau for m in msg.motor_cmd], dtype=np.float32)
        
        with self.lock:
            self.q_target_last[:] = q_targets
            self.kp_cmd[:] = kp_values
            self.kd_cmd[:] = kd_values
            self.tau_cmd[:] = tau_values

    def _apply_control_locked(self):
        """Impedance control: tau = kp * (q_target - q) - kd * qdot + tau_cmd (lock must be held)."""
        q_curr = self.mj_data.qpos[self.jnt_qposadr].copy()
        qd_curr = self.mj_data.qvel[self.jnt_dofadr].copy()
        tau = self.kp_cmd * (self.q_target_last - q_curr) - self.kd_cmd * qd_curr + self.tau_cmd
        self.tau_last[:] = tau
        self.mj_data.ctrl[:] = np.clip(tau, self.ctrl_low, self.ctrl_high)

    def _quat_to_rpy(self, quat_wxyz):
        """Convert quaternion (w, x, y, z) to RPY (roll, pitch, yaw) in radians."""
        w, x, y, z = quat_wxyz
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)
        # Pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = np.copysign(np.pi / 2, sinp)  # use 90 degrees if out of range
        else:
            pitch = np.arcsin(sinp)
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)
        return np.array([roll, pitch, yaw], dtype=np.float32)

    def _low_state_timer_cb(self):
        """Publish low_state message with IMU and motor states."""
        with self.lock:
            # Get root quaternion (w, x, y, z) and convert to RPY
            root_quat_wxyz = self.mj_data.qpos[3:7].astype(np.float32, copy=False).copy()
            rpy = self._quat_to_rpy(root_quat_wxyz)
            
            # Get angular velocity (gyro) - root angular velocity
            gyro = self.mj_data.qvel[3:6].astype(np.float32, copy=False).copy()
            
            # Get linear acceleration (acc) - root linear acceleration
            root_lin_acc = (
                self.mj_data.qacc[0:3].astype(np.float32, copy=False).copy()
                if hasattr(self.mj_data, 'qacc') and self.mj_data.qacc is not None
                else np.zeros(3, dtype=np.float32)
            )
            
            # Create IMU state
            imu_state = ImuState()
            imu_state.rpy = rpy.tolist()
            imu_state.gyro = gyro.tolist()
            imu_state.acc = root_lin_acc.tolist()
            
            # Get motor states
            q_curr = self.mj_data.qpos[self.jnt_qposadr].astype(np.float32, copy=False).copy()
            qd_curr = self.mj_data.qvel[self.jnt_dofadr].astype(np.float32, copy=False).copy()
            # Get joint accelerations (ddq)
            qdd_curr = (
                self.mj_data.qacc[self.jnt_dofadr].astype(np.float32, copy=False).copy()
                if hasattr(self.mj_data, 'qacc') and self.mj_data.qacc is not None
                else np.zeros(self.act_dim, dtype=np.float32)
            )
            tau_est = self.tau_last.astype(np.float32, copy=False).copy()
            
            # Create motor states for all actuators
            motor_states_serial = []
            for i in range(self.act_dim):
                motor_state = MotorState()
                motor_state.mode = 0  # Default mode
                motor_state.q = float(q_curr[i])
                motor_state.dq = float(qd_curr[i])
                motor_state.ddq = float(qdd_curr[i])
                motor_state.tau_est = float(tau_est[i])
                motor_state.temperature = 25  # Default temperature (room temperature)
                motor_state.lost = 0  # No packet loss in simulation
                motor_state.reserve = [0, 0]  # Default reserve values
                motor_states_serial.append(motor_state)
            
            # Create low_state message
            low_state = LowState()
            low_state.imu_state = imu_state
            low_state.motor_state_serial = motor_states_serial
            low_state.motor_state_parallel = []  # Empty for now, can be populated if needed
            
        self.pub_low_state.publish(low_state)

