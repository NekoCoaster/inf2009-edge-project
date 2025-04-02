#!/bin/bash

# Give access permission to the USB port
sudo chmod 666 /dev/ttyUSB0

# Source ROS2 and workspace
source /opt/ros/jazzy/setup.bash
source /home/team24/ws_lidar/install/setup.bash

# Launch LiDAR
ros2 launch sllidar_ros2 lidar_only_launch.py


