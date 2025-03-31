# RPLIDAR A1 Integration with MQTT-Controlled Robot

## Overview
This README documents how the LiDAR system (RPLIDAR A1) is integrated with the `compmqtt.py` control system using ROS2 and custom Python utilities to assist the robot in obstacle avoidance.

## ROS2 Workspace Setup
- **Workspace:** `/home/team24/ws_lidar`
- **LiDAR utility path:** `/home/team24/ws_lidar/src/lidar_utils/lidar_utils/specific_lidar_reader.py`

## System Flow
1. **Launch RViz2 to visualize LIDAR output**:
   - This is done through a shell script or terminal command which auto-starts RViz2 using ROS2 launch files.
   - Launch file used: `view_sllidar_a1_launch.py`

2. **/scan topic**:
   - The LiDAR continuously publishes distance and angle data to the `/scan` topic.

3. **Angle Selection (Front-Facing Filter):**
   - In `specific_lidar_reader.py`, the code filters the LiDAR reading to extract distance at approximately 90° (front of the robot).
   - This angle was determined by manually inspecting RViz2 and validating which angle maps to the front of the robot.

4. **Writing to Text File**:
   - The distance value at 90° is written to a temporary file: `/scan_90deg.txt`
   - This file is constantly updated with the most recent forward-facing LiDAR distance.

5. **compmqtt.py Reads Distance Before Movement**:
   - When a valid `navdir` is received from the MQTT broker, `compmqtt.py`:
     - Opens `/tmp/scan_90deg.txt`
     - Parses the float value inside (distance in meters)
     - If the distance is **below 0.2m (20cm)**, it aborts any movement and prints a warning
     - This is to prevent the robot from crashing into nearby obstacles regardless of MQTT direction


## Suggested Directory Structure
```
ws_lidar/
├── src/
│   └── lidar_utils/
│       └── lidar_utils/
│           └── specific_lidar_reader.py
Documents/
├── team24ros/
│   └── compmqtt.py
│   └── gpiod.py
│   └── image2
│  
scan_90deg.txt
scan90.sh
```

## Startup Commands (After Reboot)
```bash
# Source ROS2 environment
source /opt/ros/jazzy/setup.bash
source ~/ws_lidar/install/setup.bash

# Launch LiDAR node and RViz2
ros2 launch sllidar_ros2 view_sllidar_a1_launch.py

# Start distance scanner in background
python3 ~/ws_lidar/src/lidar_utils/lidar_utils/specific_lidar_reader.py &

# Run main control logic
sudo python3 compmqtt.py
```

