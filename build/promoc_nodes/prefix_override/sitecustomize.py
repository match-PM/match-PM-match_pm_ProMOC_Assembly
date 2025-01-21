import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/pmlab_mover/Documents/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/install/promoc_nodes'
