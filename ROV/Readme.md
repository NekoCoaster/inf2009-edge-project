# Edge Project + ROS2 RPLIDAR A1 Documentation

## 1. System Setup

### Ubuntu Installation
- **Version:** Ubuntu Desktop 24.04.2 LTS
- **Purpose:** Main OS for RPi5 running edge processing

### GPIO Testing & PWM
- **Hardware Used:**
  - Yellow gearbox DC motors
  - L298N Motor Driver
  - LiDAR sensor (RPLIDAR A1)
  - Raspberry pi 5
  - Multimeter
  - Portable battery
  - Step up converter

- **GPIO Libraries Tested:**
  - `lgpio` - Not compatible with RPi5
  - `rgpio` - Also failed with kernel support
  - `gpiod` - Complicated setup, lacked PWM support
  - **Final working library:** `gpiozero`

- **PWM Setup:**
  - Pins used:
    - Right Motor: in1 (16), in2 (26), ENA (12 - PWMOutputDevice)
    - Left Motor: in3 (5), in4 (6), ENB (13 - PWMOutputDevice)
  - Control methods:
    - `move_forward()`, `move_backward()`, `rotate_left()`, `rotate_right()`, `stop()`

## 2. MQTT System

### MQTT Broker
- REDACTED
- Port: REDACTED
- Username: `team24`
- Password: REDACTED

### MQTT Topics Used
- `team24/rov/camera` - publishes base64 image data
- `team24/fog/goal` - publishes user-defined goal string
- `team24/fog/AI_Status` - subscribes to AI readiness (`READY`, `BUSY`)
- `team24/fog/result` - subscribes to goal detection result (`YES`, `NO`, `BUSY`)
- `team24/fog/navdir` - subscribes to navigation direction (`W`, `A`, `S`, `D`, `STOP`, `BUSY`)

### MQTT Script Summary
- Prompts user for goal input and publishes to `team24/fog/goal`
- Captures image using `fswebcam` and publishes base64 data
- Reacts to `navdir` topic to trigger GPIO-based movement
- If no `navdir` received within 10s after both `AI_Status=READY` and `result=NO`, resend image
- After `result=YES`, wait for new user input before continuing

## 3. Camera

### Image Capture
- Command tested:
  ```bash
  fswebcam -S 20 -r 1280x720 --no-banner image2.jpg
  ```
- Purpose: To remove black frames and ensure clean capture

## 4. ROS2 & LiDAR (RPLIDAR A1)

### ROS2 Setup
- **Distro:** ROS2 Jazzy
- **Workspace:** `~/ws_lidar`
- **Installation Steps:**
  - Followed official Jazzy install guide for Ubuntu 24.04
  - Sourced ROS2 in `.bashrc`
  ```bash
  source /opt/ros/jazzy/setup.bash
  source ~/ws_lidar/install/setup.bash
  ```

### LiDAR Setup
- Package used: `sllidar_ros2`
- Launch file: `view_sllidar_a1_launch.py`
- Device: `/dev/ttyUSB0` (Silicon Labs CP210x UART Bridge)

### Distance Scanning
- Subscribed to `/scan`
- Analyzed angle-distance pairs
- Chose usable angles for 90-degree forward distance check
- Distance file: `/tmp/scan_90deg.txt`

### Result:
- Created Python script to parse 90-degree angle values
- Stored latest distance to file for navigation filtering

## 5. Integration Notes

### Architecture
- Initially attempted to combine motor control + MQTT + image capture + LiDAR in one script
- Caused conflicts, dropped packets, and GPIO hangs

### Final Design
- Split into two scripts:
  - `compmqtt.py`: handles MQTT, camera, movement
  - `scan90.py`: reads LiDAR angles, writes distance

## 6. Commands After Every Boot

```bash
# Source ROS2 and workspace
source /opt/ros/jazzy/setup.bash
source ~/ws_lidar/install/setup.bash

# Run LIDAR launch
ros2 launch sllidar_ros2 view_sllidar_a1_launch.py

# Run scanner for 90° angle:
python3 scan90.py

# Run main MQTT + control script:
sudo python3 compmqtt.py
```

## 7. GPIO Testing Commands

```bash
# Test PWM pin using gpiozero interactively
python3
>>> from gpiozero import PWMOutputDevice
>>> pwm = PWMOutputDevice(12)
>>> pwm.value = 0.5
>>> pwm.off()
```

## 8. Failures and Troubleshooting
- `lgpio` / `rgpio`: Kernel incompatibility on RPi5
- `gpiod`: No PWM support for motor control
- using multimeters to test outputs of gpio pins for debugging
- `fswebcam`: Black frames until using `-S 20`
- Combining ROS2 and GPIO in one process: unstable
- MQTT disconnections if camera capture blocked main thread
