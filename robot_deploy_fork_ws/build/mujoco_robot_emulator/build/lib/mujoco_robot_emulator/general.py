#!/usr/bin/env python3
"""ROS2 node that runs a MuJoCo simulation and publishes /clock.

Applies simple PD control and subscribes to 'rl2pd' for targets.
"""
import os
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
import numpy as np
import threading
import time
import mujoco

# import wrapper helpers you made
from rosgraph_msgs.msg import Clock as ClockMsg
from builtin_interfaces.msg import Time as TimeMsg
from rclpy.qos import (
    QoSProfile,
    QoSHistoryPolicy,
    QoSReliabilityPolicy,
    QoSDurabilityPolicy,
)
from rclpy.clock import Clock as ROSClock, ClockType
from ament_index_python.packages import get_package_share_directory

import mujoco.viewer as mj_viewer  # type: ignore

class General(Node):
    """Single-node MuJoCo simulator with ROS2 I/O and simulated time."""

    def __init__(self):
        """Initialize MuJoCo, ROS interfaces, and PD control mapping."""
        super().__init__('mujoco_ros_node')

        # Declare and read ROS2 parameters
        self.declare_parameter('mujoco_file', rclpy.Parameter.Type.STRING)
        self.declare_parameter('sim_dt',0.0)
        self.declare_parameter('kp',rclpy.Parameter.Type.DOUBLE_ARRAY)
        self.declare_parameter('kd',rclpy.Parameter.Type.DOUBLE_ARRAY)
        self.declare_parameter('control_freq',0.0)
        self.declare_parameter('dof_pub_freq',0.0)
        self.declare_parameter('body_pub_freq',0.0)
        self.declare_parameter('imu_pub_freq',0.0)

        # self.declare_parameter('render_window_height', 240) # высота окна
        self.declare_parameter('render_offscreen', False)   # если True – использовать offscreen-рендерер (без окна)

        mujoco_file = self.get_parameter('mujoco_file').get_parameter_value().string_value
        self.dt = self.get_parameter('sim_dt').get_parameter_value().double_value
        kp = self.get_parameter('kp').get_parameter_value().double_array_value
        kd = self.get_parameter('kd').get_parameter_value().double_array_value
        control_freq = self.get_parameter('control_freq').get_parameter_value().double_value
        dof_pub_freq = self.get_parameter('dof_pub_freq').get_parameter_value().double_value
        body_pub_freq = self.get_parameter('body_pub_freq').get_parameter_value().double_value
        imu_pub_freq = self.get_parameter('imu_pub_freq').get_parameter_value().double_value

        # Resolve mujoco_file path
        pkg_share = get_package_share_directory('mimic_k1_data')
        if not os.path.isabs(mujoco_file):
            xml_path = os.path.join(pkg_share, mujoco_file)
        else:
            xml_path = mujoco_file

        # init mujoco
        self.mj_model = mujoco.MjModel.from_xml_path(xml_path)
        self.mj_data = mujoco.MjData(self.mj_model)

        # loop frequencies
        self.control_freq = control_freq
        self.dof_pub_freq = dof_pub_freq
        self.body_pub_freq = body_pub_freq
        self.imu_pub_freq = imu_pub_freq
        # simulated time in nanoseconds; publish on /clock
        self.sim_time_ns = 0
        self.wall_start = time.perf_counter()
        self._last_log_ns = 0
        clock_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self.clock_pub = self.create_publisher(ClockMsg, '/clock', clock_qos)

            # Запускаем пассивный вьювер с конфигурацией
        self.viewer = mj_viewer.launch_passive(self.mj_model, self.mj_data)
        self.scn = mujoco.MjvScene(self.mj_model, maxgeom=100)  # ограничиваем геометрию
        self.opt = mujoco.MjvOption()
        
        # Отключаем всё лишнее
        self.opt.frame = mujoco.mjtFrame.mjFRAME_NONE
        self.opt.label = mujoco.mjtLabel.mjLABEL_NONE
        
        # Отключаем визуализацию различных элементов
        self.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = False
        self.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = False
        self.opt.flags[mujoco.mjtVisFlag.mjVIS_JOINT] = False
        self.opt.flags[mujoco.mjtVisFlag.mjVIS_TENDON] = False
        self.opt.flags[mujoco.mjtVisFlag.mjVIS_ACTUATOR] = False
        # self.opt.flags[mujoco.mjtVisFlag.mjVIS_SENSOR] = False
        self.opt.flags[mujoco.mjtVisFlag.mjVIS_CAMERA] = False
        self.get_logger().info('MuJoCo viewer launched with low-quality settings.')
        # viewer: launch by default
        # self.viewer = mj_viewer.launch_passive(self.mj_model, self.mj_data)
        # self.get_logger().info('MuJoCo viewer launched.')

        # PD mapping from your script
        self.act_dim = int(self.mj_model.nu)
        act_joint_ids = np.array(
            [
                int(self.mj_model.actuator_trnid[i, 0])
                for i in range(self.mj_model.nu)
            ],
            dtype=np.int32,
        )
        self.jnt_qposadr = self.mj_model.jnt_qposadr[act_joint_ids]
        self.jnt_dofadr = self.mj_model.jnt_dofadr[act_joint_ids]
        self.ctrl_low = self.mj_model.actuator_ctrlrange[:, 0]
        self.ctrl_high = self.mj_model.actuator_ctrlrange[:, 1]

        # PD gains
        self.kp = np.asarray(kp, dtype=np.float32)
        self.kd = np.asarray(kd, dtype=np.float32)

        # target buffer
        self.q_target_last = np.zeros((self.act_dim,), dtype=np.float32)
        # last applied torque (for debug topic /robot/ctrl)
        self.tau_last = np.zeros((self.act_dim,), dtype=np.float32)

        # control scheduling (do control inside sim loop to avoid timer race/jitter)
        self._control_dt = 1.0 / max(1e-6, float(self.control_freq)) if self.control_freq > 0 else float(self.dt)
        self._control_time_accum = 0.0

        # Topics: subscribe to RL-provided targets
        self.sub = self.create_subscription(
            Float32MultiArray,
            'rl2pd',
            self.rl2pd_callback,
            10)
        # Publishers for robot state
        self.pub_dofs = self.create_publisher(
            Float32MultiArray,
            'robot/dofs',
            10)
        self.pub_body = self.create_publisher(
            Float32MultiArray,
            'robot/body',
            10)
        self.pub_imu = self.create_publisher(
            Float32MultiArray,
            'robot/imu',
            10)
        self.pub_ctrl = self.create_publisher(
            Float32MultiArray,
            'robot/ctrl',
            10)

        # Lock for thread-safety between callback and sim loop
        self.lock = threading.Lock()

        # Simulation timer on STEADY (wall) clock to drive /clock regardless of sim_time
        self.sim_timer = self.create_timer(
            float(self.dt), self._sim_timer_cb, clock=ROSClock(clock_type=ClockType.STEADY_TIME)
        )
        # ROS timers for publishers (run on ROS clock; aligned with /clock)
        self.dof_timer = self.create_timer(
            1.0 / max(1e-6, self.dof_pub_freq), self._dof_timer_cb
        )
        self.body_timer = self.create_timer(
            1.0 / max(1e-6, self.body_pub_freq), self._body_timer_cb
        )
        self.imu_timer = self.create_timer(
            1.0 / max(1e-6, self.imu_pub_freq), self._imu_timer_cb
        )

        self.get_logger().info(
            (
                f'Mujoco ROS node initialized: dt={self.dt}, '
                f'act_dim={self.act_dim}'
            )
        )

    def rl2pd_callback(self, msg: Float32MultiArray):
        """Receive target joint positions from RL policy and store them."""
        # Expect msg.data length == act_dim and contains q_target per actuator
        data = np.array(msg.data, dtype=np.float32)
        with self.lock:
            self.q_target_last[:] = data

    def _apply_control_locked(self):
        """Compute and apply PD torques to mj_data.ctrl (lock must be held)."""
        q_curr = self.mj_data.qpos[self.jnt_qposadr].copy()
        qd_curr = self.mj_data.qvel[self.jnt_dofadr].copy()
        tau = self.kp * (self.q_target_last - q_curr) - self.kd * qd_curr
        self.tau_last[:] = tau
        self.mj_data.ctrl[:] = np.clip(tau, self.ctrl_low, self.ctrl_high)

    def _sim_timer_cb(self):
        """Advance simulation by one step, publish /clock, sync viewer, periodic logs."""
        # Apply control and step simulation deterministically in one loop (avoids jitter from timer races)
        with self.lock:
            self._control_time_accum += float(self.dt)
            # Update control as many times as needed for the configured control frequency
            while self._control_time_accum + 1e-12 >= self._control_dt:
                self._apply_control_locked()
                self._control_time_accum -= self._control_dt
            mujoco.mj_step(self.mj_model, self.mj_data)

        # Publish last applied torque (debug)
        msg_ctrl = Float32MultiArray()
        msg_ctrl.data = self.tau_last.astype(np.float32, copy=False).tolist()
        self.pub_ctrl.publish(msg_ctrl)

        # advance and publish simulated time
        self.sim_time_ns += int(round(self.dt * 1e9))
        clock_msg = ClockMsg()
        tmsg = TimeMsg()
        tmsg.sec = self.sim_time_ns // 1_000_000_000
        tmsg.nanosec = self.sim_time_ns % 1_000_000_000
        clock_msg.clock = tmsg
        self.clock_pub.publish(clock_msg)
        try:
            self.viewer.sync()
        except Exception:
            pass
        
        # periodic check: warn if sim_time doesn't match ros_time
        if (self.sim_time_ns - self._last_log_ns) >= 1_000_000_000:
            ros_now_ns = self.get_clock().now().nanoseconds
            sim_time_s = self.sim_time_ns / 1e9
            ros_time_s = ros_now_ns / 1e9
            time_diff = abs(sim_time_s - ros_time_s)
            # Warn if difference is more than 0.1 seconds or 1% of sim_time
            if time_diff > max(0.1, sim_time_s * 0.01):
                wall_elapsed = time.perf_counter() - self.wall_start
                self.get_logger().warn(
                    (
                        f'Time mismatch: sim_time={sim_time_s:.3f}s '
                        f'ros_time={ros_time_s:.3f}s '
                        f'diff={time_diff:.3f}s '
                        f'wall={wall_elapsed:.3f}s'
                    )
                )
            self._last_log_ns = self.sim_time_ns

    def _dof_timer_cb(self):
        """Publish DOF data at configured frequency (ROS timer)."""
        with self.lock:
            dof_pos = self.mj_data.qpos[7:].astype(np.float32, copy=False).copy()
            dof_vel = self.mj_data.qvel[6:].astype(np.float32, copy=False).copy()
        dofs = np.concatenate([dof_pos, dof_vel]).astype(np.float32, copy=False)
        msg_dofs = Float32MultiArray()
        msg_dofs.data = dofs.tolist()
        self.pub_dofs.publish(msg_dofs)

    def _body_timer_cb(self):
        """Publish body/root poses at configured frequency (ROS timer)."""
        with self.lock:
            root_pos = self.mj_data.qpos[0:3].astype(np.float32, copy=False).copy()
            root_quat_wxyz = self.mj_data.qpos[3:7].astype(np.float32, copy=False).copy()
            body_pos_flat = self.mj_data.xpos.reshape(-1).astype(np.float32, copy=False).copy()
            body_quat_flat = self.mj_data.xquat.reshape(-1).astype(np.float32, copy=False).copy()
        body_vec = np.concatenate([root_pos, root_quat_wxyz, body_pos_flat, body_quat_flat]).astype(np.float32, copy=False)
        msg_body = Float32MultiArray()
        msg_body.data = body_vec.tolist()
        self.pub_body.publish(msg_body)

    def _imu_timer_cb(self):
        """Publish IMU-like data at configured frequency (ROS timer)."""
        with self.lock:
            root_quat_wxyz = self.mj_data.qpos[3:7].astype(np.float32, copy=False).copy()
            root_ang_vel = self.mj_data.qvel[3:6].astype(np.float32, copy=False).copy()
            root_lin_vel = self.mj_data.qvel[0:3].astype(np.float32, copy=False).copy()
            root_lin_acc = (
                self.mj_data.qacc[0:3].astype(np.float32, copy=False).copy()
                if hasattr(self.mj_data, 'qacc') else np.zeros(3, dtype=np.float32)
            )
        imu_vec = np.concatenate([root_quat_wxyz, root_ang_vel, root_lin_vel, root_lin_acc]).astype(np.float32, copy=False)
        msg_imu = Float32MultiArray()
        msg_imu.data = imu_vec.tolist()
        self.pub_imu.publish(msg_imu)
