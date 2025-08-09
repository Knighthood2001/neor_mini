#!/usr/bin/env python
# -*- coding: utf-8 -*-

import roslib
import sys
import rospy
import cv2
import numpy as np
from cv_bridge import CvBridge ,CvBridgeError
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
"""
这段代码是一个基于 ROS 的视觉循线控制器，用于让小车（如阿克曼转向小车）通过摄像头识别地面上的黄色线条，
并自动沿着线条行驶。核心逻辑是通过图像处理识别黄色线条的位置，计算偏差后控制小车转向，实现自动循线。
"""

class LineFollower(object):
    def __init__(self):
        self.cvBridge = CvBridge()  # 创建ROS图像与OpenCV图像的转换器
        # 订阅相机原始图像话题（/camera/image_raw），回调函数为camera_callback
        self.sub_image_original = rospy.Subscriber(
            '/camera/image_raw', Image, self.camera_callback, queue_size=1
        )
        # 发布速度控制指令到阿克曼转向控制器话题（/ackermann_steering_controller/cmd_vel）
        self.cmd_vel_pub = rospy.Publisher(
            '/ackermann_steering_controller/cmd_vel', Twist, queue_size=10
        )

    # ROS Image's topic callback function
    # 处理图像→识别线条→计算控制量
    def camera_callback(self, image_msg): 
        try:
            cv_image = self.cvBridge.imgmsg_to_cv2(image_msg, "bgr8")
        except CvBridgeError as e:
                print(e)
        cv2.imshow("cv_imcode_image",cv_image)

        height, width, channels = cv_image.shape  # 获取图像尺寸（高、宽、通道数）
        descentre = 50  # 裁剪区域的垂直偏移（从图像下方开始，避免天空等无关区域）
        rows_to_watch = 100  # 裁剪区域的高度（只关注地面上的线，减少计算量）
        # 裁剪图像：只保留下方的一小块区域（地面区域）
        crop_img = cv_image[(height//4) + descentre : (height//4) + (descentre + rows_to_watch)][1:width]
        #convert from RGB to HSV
        hsv = cv2.cvtColor(crop_img,cv2.COLOR_BGR2HSV)  # BGR转HSV（更适合颜色分割）
        cv2.imshow("HSV",hsv)

        # yellow colour in HSV
        lower_yellow = np.array([20,50,50])
        upper_yellow = np.array([30,255,255])

        #Threshold the HSV image to get only yellow colors
        mask = cv2.inRange(hsv,lower_yellow,upper_yellow)
        cv2.imshow("MASK",mask)
        
        #Bitwise-and musk and original image
        res = cv2.bitwise_and(crop_img,crop_img,mask = mask)
        cv2.imshow("RES",res)
  
        # 计算掩码图像的矩（moment），用于求质心
        m = cv2.moments(mask,False)
        try: 
            cx, cy = m['m10']/m['m00'], m['m01']/m['m00']
        except ZeroDivisionError:
                cx, cy = height/2, width/2
       
        # Draw the centroid in the resultut image
        cv2.circle(res , (int(cx) , int(cy)) , 20 , (255,255,0) , 2)
        cv2.waitKey(30)

        # 计算偏差：质心x坐标与图像中心x坐标的差值（误差越小，线条越居中）
        error_x = cx - width / 2

        # 创建速度控制消息（Twist）
        twist_object = Twist()
        twist_object.linear.x = 2  # 线性速度（前进速度，固定为2）
        # 角速度：与偏差成反比（负号表示反向纠正，误差越大，转向越急）
        twist_object.angular.z = -error_x / 200

        rospy.loginfo("ANGULAR VALUE SENT ===>"+str(twist_object.angular.z))
        self.cmd_vel_pub.publish(twist_object)  # 发布控制指令



def main():
    rospy.init_node('line_follower_object',anonymous=True)
    line_follower_object = LineFollower()
    ctrl_c = False
    rate = rospy.Rate(5)
    while not ctrl_c:
        rate.sleep()

if __name__ == '__main__':
    main()
