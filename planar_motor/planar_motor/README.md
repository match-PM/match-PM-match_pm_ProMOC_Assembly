# Planar Motor Control

A ROS 2 package for controlling planar motors with an interactive service node for position control and actuator management.

## Table of Contents
- [Description](#description)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Description

This ROS 2 package allows for controlling planar motors, which are used in various robotic applications such as XY movement systems. It provides a service to control the position of the motors, activate or deactivate them, and send feedback on their status. This package is designed to be used with ROS 2 Humble and Python 3.x.

## Installation

To install this package, you need to have a ROS 2 workspace set up. Follow these steps:

1.  Clone this repository into your workspace's `src` directory:
   
    cd ~/ros2_ws/src
    git clone ("Hier unsere GIt adresse einfügen")

2.  Install any necessary dependencies using rosdep:
    
    cd ~/ros2_ws
    rosdep install --from-paths src --ignore-src -r -y

3.  Build the workspace:
    
    colcon build --symlink-install


4.  Source your workspace:
    
    source ~/ros2_ws/install/setup.bash
    (Wir haben das getan indem wir den Befehl in unsere .bashrc geschrieben haben -> wir schreiben nur source .bashrc)

 ## Usage  

1. run the servie node:
    
    ros2 run planar_motor mover_service_node

2. call a service:

    1. ros2 service call /activate_xbot planar_motor_interfaces/srv/ActivateXbots "{activate: true}"

    2. call the service via rqt 

    3. call the service via a client node for example: 
    
    ros2 run planar_motor sternberg_call_mover_node

    4. call a servie via ros_sequential_action_programmer

    (hat bei mir heut nicht funktioniert evtl nochmal niklas fragen)


##  Contributing

Wenn du was an der Service Datei änderst nicht vergessen SPeichern und dann im Terminal source .bashrc auszuführen

alle Nodes in planar_motor builden wir mit 
colcon build --packages-select planar_motor --symlink-install

bei services und msgs builden wir mit 
colcon build --packages-select planar_motor_interfaces

bei services immer drauf achten das der name  der request und response werte exakt den namen und typ haben der in der srv /msg datei festgelegt wurde

    def callback_activate_xbot(self,request,response):
            if request.activation_status == True:
                bot.activate_xbots()
                response.activation_status = True 
            else:
                bot.deactivate_xbots()
                response.xbox_status = False
            return response

so führte zum Beispiel der activate_xbot service zu einem fehler




Wenn du einen service gelöscht hast und der aber fehlermeldungen raushaut dann einmel den Workspace 
Rebuilden

dafür in den ros2_ws gehen und 

rm -rf build/ install/ log/
colcon build --symlink-install

ausführen
