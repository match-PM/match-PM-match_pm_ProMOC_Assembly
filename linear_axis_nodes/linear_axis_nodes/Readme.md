How to use the ros2 node on win

1. Open Tabby Terminal as Administrator.
2. on the top terminal icon select a Developer Promt for VS2019
3.source your ros2 installation with 
call C:\dev\ros2_jazzy\setup.bat
4. source the workspace with 
call C:\Users\admin\promoc_ros2_ws\install\setup.bat
c
5. Navigate to your ROS2 workspace with > cd C:\Users\admin\promoc_ros2_ws

6. build changes with > colcon build --merge-install
 or for more information use > colcon build --merge-install --event-handlers console_direct+

 7. run the node with> 
 ros2 run linear_axis_nodes lts300_service_node


 Dummerweise gibt es Probleme mit der ROS2 Verbindung zu den lts300 dehsalb wird der ros2 node nur als wrapper für das lts300 COntrollscript genutz zumindest ist das der plan 
