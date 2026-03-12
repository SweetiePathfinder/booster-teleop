import math

import rclpy
from rclpy.node import Node

from booster_interface.msg import LowCmd, LowState, MotorCmd


NUM_MOTORS = 22

# Индексы моторов рук
L_SH_PITCH = 2
L_SH_ROLL  = 3
L_EL_PITCH = 4
L_EL_YAW   = 5

R_SH_PITCH = 6
R_SH_ROLL  = 7
R_EL_PITCH = 8
R_EL_YAW   = 9

LOW_LIMITS = [
    -1.0, -0.349,
    -3.316, -1.43, -2.27, -2.44,
    -3.316, -1.57, -2.27, 0.0,
    -3.0, -0.4, -1.0, 0.0, -0.87, -0.345,
    -3.0, -1.57, -1.0, 0.0, -0.87, -0.345
]

UP_LIMITS = [
    1.0, 0.855,
    1.22, 1.57, 2.27, 0.0,
    1.22, 1.43, 2.27, 2.44,
    2.21, 1.57, 1.0, 2.23, 0.345, 0.345,
    2.21, 0.4, 1.0, 2.23, 0.345, 0.345
]


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class ArmSineTestNode(Node):
    def __init__(self):
        super().__init__("arm_sine_test_node")

        self.low_state = None
        self.base_q = None
        self.t = 0.0

        self.state_sub = self.create_subscription(
            LowState,
            "/low_state",
            self.low_state_callback,
            10
        )

        self.cmd_pub = self.create_publisher(
            LowCmd,
            "/rl2pd",
            10
        )

        self.timer = self.create_timer(1.0 / 30.0, self.timer_callback)

        self.get_logger().info("Arm sine test node started")

    def low_state_callback(self, msg: LowState):
        self.low_state = msg

        # Сохраняем базовую позу один раз
        if self.base_q is None and len(msg.motor_state_serial) >= NUM_MOTORS:
            self.base_q = [msg.motor_state_serial[i].q for i in range(NUM_MOTORS)]
            self.get_logger().info("Captured base pose from /low_state")

    def timer_callback(self):
        if self.low_state is None or self.base_q is None:
            return

        if len(self.low_state.motor_state_serial) < NUM_MOTORS:
            self.get_logger().warn("low_state has fewer than 22 motors")
            return

        self.t += 1.0 / 30.0

        # Команда: все суставы держим в базовой позе
        q_cmd = self.base_q.copy()

        # Параметры движения
        freq = 0.3
        amp_sh_pitch = 0.25
        amp_sh_roll = 0.20
        amp_el_pitch = 0.35

        s = math.sin(2.0 * math.pi * freq * self.t)

        # Левая рука
        q_cmd[L_SH_PITCH] = clamp(
            self.base_q[L_SH_PITCH] + amp_sh_pitch * s,
            LOW_LIMITS[L_SH_PITCH], UP_LIMITS[L_SH_PITCH]
        )
        q_cmd[L_SH_ROLL] = clamp(
            self.base_q[L_SH_ROLL] + amp_sh_roll * s,
            LOW_LIMITS[L_SH_ROLL], UP_LIMITS[L_SH_ROLL]
        )
        q_cmd[L_EL_PITCH] = clamp(
            self.base_q[L_EL_PITCH] + amp_el_pitch * s,
            LOW_LIMITS[L_EL_PITCH], UP_LIMITS[L_EL_PITCH]
        )

        # yaw локтя пока фиксирован
        q_cmd[L_EL_YAW] = clamp(
            self.base_q[L_EL_YAW],
            LOW_LIMITS[L_EL_YAW], UP_LIMITS[L_EL_YAW]
        )

        # Правая рука
        q_cmd[R_SH_PITCH] = clamp(
            self.base_q[R_SH_PITCH] + amp_sh_pitch * s,
            LOW_LIMITS[R_SH_PITCH], UP_LIMITS[R_SH_PITCH]
        )
        q_cmd[R_SH_ROLL] = clamp(
            self.base_q[R_SH_ROLL] - amp_sh_roll * s,
            LOW_LIMITS[R_SH_ROLL], UP_LIMITS[R_SH_ROLL]
        )
        q_cmd[R_EL_PITCH] = clamp(
            self.base_q[R_EL_PITCH] + amp_el_pitch * s,
            LOW_LIMITS[R_EL_PITCH], UP_LIMITS[R_EL_PITCH]
        )

        q_cmd[R_EL_YAW] = clamp(
            self.base_q[R_EL_YAW],
            LOW_LIMITS[R_EL_YAW], UP_LIMITS[R_EL_YAW]
        )

        msg = LowCmd()
        msg.cmd_type = LowCmd.CMD_TYPE_SERIAL
        msg.motor_cmd = []

        for i in range(NUM_MOTORS):
            cmd = MotorCmd()
            cmd.q = float(q_cmd[i])
            cmd.dq = 0.0
            cmd.tau = 0.0
            cmd.kp = 0.0
            cmd.kd = 0.0
            msg.motor_cmd.append(cmd)

        self.cmd_pub.publish(msg)


def main():
    rclpy.init()
    node = ArmSineTestNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
