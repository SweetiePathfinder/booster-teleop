from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    """Launch a 'direct sim2sim' pipeline that matches the old deploy/sim2sim/deepmimic.py behavior.

    This launches:
    - MuJoCo emulator in `General` mode (subscribes Float32MultiArray on `rl2pd` and runs PD internally)
    - Python DeepMimic policy node (`deepmimic`) that publishes Float32MultiArray on `rl2pd`

    No booster_controller is used here, to avoid altering targets/gains.
    """
    mujoco_share = get_package_share_directory("mujoco_robot_emulator")
    mimic_k1_share = get_package_share_directory("mimic_k1_data")

    # MuJoCo emulator params (contains mujoco_file/sim_dt/kp/kd/control_freq/pub rates)
    mujoco_config = os.path.join(mujoco_share, "config", "k1_sim.yaml")

    # Policy CLI args are resolved relative to mimic_k1_data share inside deepmimic_node.py
    env_yaml_rel = "config/deepmimic_k1_env.yaml"
    agent_yaml_rel = "config/deepmimic_k1_ppo_agent.yaml"
    model_file_rel = "weights/deep_mimic_lookaround_v3.pt"

    return LaunchDescription(
        [
            Node(
                package="mujoco_robot_emulator",
                executable="node",
                name="mujoco_ros_node",  # must match the top-level key in k1_sim.yaml
                parameters=[mujoco_config, {"use_sim_time": True}],
                arguments=["--type", "General"],
                output="screen",
            ),
            Node(
                package="mimic_py_policies",
                executable="deepmimic",
                name="deepmimic_policy",
                arguments=[
                    "--env_yaml",
                    env_yaml_rel,
                    "--agent_yaml",
                    agent_yaml_rel,
                    "--model_file",
                    model_file_rel,
                    "--policy_freq",
                    "30.0",
                    "--ros-args",
                    "-p",
                    "use_sim_time:=true",
                ],
                output="screen",
            ),
        ]
    )


