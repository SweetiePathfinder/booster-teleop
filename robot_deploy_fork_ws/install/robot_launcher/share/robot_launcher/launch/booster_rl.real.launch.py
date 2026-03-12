from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get package share directories
    booster_controller_share = get_package_share_directory('booster_controller')
    booster_policies_share = get_package_share_directory('booster_policies')
    
    # Config file paths
    rl_control_config = os.path.join(
        booster_controller_share,
        'config',
        'rl_control_params.yaml'
    )
    rl_agent_config = os.path.join(
        booster_policies_share,
        'config',
        'rl_agent_params.yaml'
    )
    
    return LaunchDescription([
        # RL Agent node (from booster_policies package)
        Node(
            package='booster_policies',
            executable='booster_rl_agent_node',
            name='rl_agent_node',
            parameters=[rl_agent_config],
        ),
        
        # RL Control node
        Node(
            package='booster_controller',
            executable='booster_rl_control_node',
            name='rl_control_node',
            parameters=[rl_control_config],
        )
    ])
