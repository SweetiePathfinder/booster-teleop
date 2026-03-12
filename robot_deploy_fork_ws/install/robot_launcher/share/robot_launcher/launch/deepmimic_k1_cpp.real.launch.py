from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get package share directories
    booster_controller_share = get_package_share_directory('booster_controller')
    mimic_cpp_share = get_package_share_directory('mimic_cpp_policies')
    
    # Config file paths - keep consistent with sim launch, just without MuJoCo emulator.
    mimic_cpp_params = os.path.join(mimic_cpp_share, 'config', 'k1.yaml')
    booster_controller_params = os.path.join(booster_controller_share, 'config', 'mimic_control.yaml')
    
    return LaunchDescription([
        # DeepMimic Policy node (C++ version)
        Node(
            package='mimic_cpp_policies',
            executable='deepmimic_k1_node',
            name='deepmimic_policy',
            # On real robot, we normally run on wall-clock time (no /clock)
            parameters=[mimic_cpp_params, {'use_sim_time': False}],
            output='screen',
        ),
        
        # RL Control node
        Node(
            package='booster_controller',
            executable='booster_rl_control_node',
            name='rl_control_node',
            parameters=[booster_controller_params, {'use_sim_time': False}],
        )
    ])
