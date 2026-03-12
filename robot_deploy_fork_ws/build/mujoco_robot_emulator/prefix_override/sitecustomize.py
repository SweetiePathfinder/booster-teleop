import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/pathfinder/Projects/Starkit/booster_teleop/robot_deploy_fork_ws/install/mujoco_robot_emulator'
