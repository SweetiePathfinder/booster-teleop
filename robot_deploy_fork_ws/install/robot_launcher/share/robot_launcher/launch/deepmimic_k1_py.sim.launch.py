from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get package share directories
    mujoco_share = get_package_share_directory('mujoco_robot_emulator')
    booster_controller_share = get_package_share_directory('booster_controller')
    mimic_py_share = get_package_share_directory('mimic_py_policies')
    
    # Config file paths - each node loads from its own package
    mujoco_config = os.path.join(
        mujoco_share,
        'config',
        'k1_sim.yaml'
    )
    mimic_py_params = os.path.join(
        mimic_py_share,
        'config',
        'k1.yaml'
    )
    booster_controller_params = os.path.join(
        booster_controller_share,
        'config',
        'mimic_control.yaml'
    )
    
    return LaunchDescription([
        # MuJoCo emulator node
        Node(
            package='mujoco_robot_emulator',
            executable='node',
            name='mujoco_ros_node',
            parameters=[mujoco_config, {'use_sim_time': True}],
            arguments=['--type', 'K1'],
            output='screen',
        ),
        
        # DeepMimic Policy node (Python version)
        Node(
            package='mimic_py_policies',
            executable='deepmimic_k1',
            name='deepmimic_policy',
            parameters=[mimic_py_params, {'use_sim_time': True}],
            output='screen',
        ),
        
        # RL Control node
        Node(
            package='booster_controller',
            executable='booster_rl_control_node',
            name='rl_control_node',
            parameters=[booster_controller_params, {'use_sim_time': True}],
            output='screen',
        )
    ])
