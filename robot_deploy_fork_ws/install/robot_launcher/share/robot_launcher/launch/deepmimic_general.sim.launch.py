from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package share directories
    booster_controller_share = get_package_share_directory('booster_controller')
    mujoco_share = get_package_share_directory('mujoco_robot_emulator')
    mimic_share = get_package_share_directory('mimic_k1_data')

    # Config file paths
    # rl_control_config = os.path.join(
    #     rl_engine_share,
    #     'config',
    #     'rl_control_params.yaml'
    # )
    # k1_config = os.path.join(
    #     mujoco_share,
    #     'config',
    #     'k1.yaml'
    # )

    # DeepMimic K1 policy config (matches README invocation)
    env_yaml = os.path.join(mimic_share, 'config', 'deepmimic_k1_env.yaml')
    agent_yaml = os.path.join(mimic_share, 'config', 'deepmimic_k1_ppo_agent.yaml')
    model_file = os.path.join(mimic_share, 'weights', 'deep_mimic_look_around_noGlobalObs.pt')

    return LaunchDescription([
        # MuJoCo emulator node
        Node(
            package='mujoco_robot_emulator',
            executable='node',
            name='mujoco_emulator',
            arguments=[
                '--type', 'general',
                '--env_yaml', env_yaml,
                '--ros-args', '-p', 'use_sim_time:=true'
            ],
        ),

        # DeepMimic K1 Python policy node (instead of booster_rl_agent_node)
        Node(
            package='mimic_py_policies',
            executable='deepmimic',
            name='deepmimic_policy',
            arguments=[
                '--env_yaml', env_yaml,
                '--agent_yaml', agent_yaml,
                '--model_file', model_file,
                '--ros-args', '-p', 'use_sim_time:=true'
            ],
        ),

        # RL Control node
        # Node(
        #     package='booster_controller',
        #     executable='booster_rl_control_node',
        #     name='rl_control_node',
        #     parameters=[{'use_sim_time': True},
        #                 rl_control_config],
        # ),
    ])