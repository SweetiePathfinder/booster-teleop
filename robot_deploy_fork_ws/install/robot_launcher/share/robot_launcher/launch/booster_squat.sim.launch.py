from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get package share directories
    mujoco_share = get_package_share_directory('mujoco_robot_emulator')
    booster_controller_share = get_package_share_directory('booster_controller')
    booster_policies_share = get_package_share_directory('booster_policies')
    
    # Config file paths
    mujoco_config = os.path.join(
        mujoco_share,
        'config',
        'k1_sim.yaml'
    )
    rl_control_config = os.path.join(
        booster_controller_share,
        'config',
        'rl_control_params.yaml'
    )
    squat_agent_config = os.path.join(
        booster_policies_share,
        'config',
        'squat_agent_params.yaml'
    )
    
    return LaunchDescription([
        # MuJoCo emulator node
        Node(
            package='mujoco_robot_emulator',
            executable='node',
            name='mujoco_ros_node',
            parameters=[mujoco_config, {'use_sim_time': True}],
            arguments=['--type', 'K1'],
        ),
        
        # Squat Agent node (from booster_policies package)
        Node(
            package='booster_policies',
            executable='booster_squat_agent_node',
            name='squat_agent_node',
            parameters=[squat_agent_config, {'use_sim_time': True}],
        ),
        
        # RL Control node
        Node(
            package='booster_controller',
            executable='booster_rl_control_node',
            name='rl_control_node',
            parameters=[rl_control_config, {'use_sim_time': True}],
        )
    ])

