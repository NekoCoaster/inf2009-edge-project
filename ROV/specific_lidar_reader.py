#!/usr/bin/env python3

import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import math

class SpecificLidarReader(Node):
    def __init__(self):
        super().__init__('specific_lidar_reader')
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.lidar_callback,
            10)
        self.latest_distance = None

    def lidar_callback(self, msg):
        # 90° in radians
        angle_90_rad = math.radians(90)
        index = int((angle_90_rad - msg.angle_min) / msg.angle_increment)

        if 0 <= index < len(msg.ranges):
            distance = msg.ranges[index]
            if math.isfinite(distance):
                with open(os.path.expanduser("~/scan_90deg.txt"), "w") as f:
                    f.write(f"{distance:.2f}")
                print(f"90° distance written: {distance:.2f}")

        # Do not print anything if no reading

def main(args=None):
    rclpy.init(args=args)
    node = SpecificLidarReader()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
