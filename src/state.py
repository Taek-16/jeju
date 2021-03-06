#!/usr/bin/env python
#-*-coding:utf-8-*-

# Python packages
import rospy
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))) + "/src/missions")
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))) + "/src/sensor")
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))) + "/src/path_planning")
import math
import numpy as np

# message 파일
from macaron_4.msg import erp_write

# 모듈 import
from global_path import GlobalPath
from sub_erp_state import sub_erp_state
from mission_cruising import mission_cruising
from mission_parking import mission_parking
from mission_dynamic_obstacle import mission_dynamic_obstacle
from mission_traffic import mission_traffic_straight, mission_traffic_left
from mission_delivery import mission_delivery

WHERE = 3 # 1 대운동장, 2 K city 예선, 3 K city 본선, 5 대운동장 직선, 6 대운동장 찐 직선

CRUISING_SPEED = 200

# 미션별 SL 좌표
if WHERE == 1: # 동국대
    GLOBAL_PATH_NAME = "PG.npy" 
    mission_coord = {"Parking" : [27, 64], "Static_Obstacle" : [80, 122],
                    "Dynamic_Obstacle" : [99999.5, 99999.2], "Cross_Walk" : [9999, 9999],
                    "School_Zone" : [9999, 9999], "Delivery" : [226, 630],
                    "Traffic_light_straight" : [[199948.9 - 9.0, 199948.9 + 4.0],
                                                [149998.9 - 9.0, 199948.9 + 4.0]], # 148.9
                    "Traffic_light_left" : [[9999, 9999],[9999, 9999]]}

elif WHERE == 2: # kcity 예선
    GLOBAL_PATH_NAME = "kcity_tryout.npy"
    mission_coord = {"Parking" : [9999, 9999], "Static_Obstacle" : [362.5, 409.8],
                    "Dynamic_Obstacle" : [224.6, 305.0], "Cross_Walk" : [9999, 9999],
                    "School_Zone" : [9999, 9999], "Delivery" : [9999, 9999],
                    "Traffic_light_straight" : [[110.3 - 15.0, 110.3 + 4.0],
                                                [248.6 - 15.0, 248.6 + 4.0]], # 110.3, 248.6
                    "Traffic_light_left" : [[9999, 9999],[9999, 9999]]}
elif WHERE == 3: # kcity 본선
    GLOBAL_PATH_NAME = "kcity_final.npy"
    mission_coord = {"Parking" : [77.0, 135.5], "Static_Obstacle" : [286.5, 351.5],
                    "Dynamic_Obstacle" : [9999, 9999], "Cross_Walk" : [9999, 9999],
                    "School_Zone" : [827.0, 856.0], "Delivery" : [376.0, 754.3],
                    "Traffic_light_straight" : [[178.2 - 15.0, 178.2 + 4.0],
                                                [233.0 - 15.0, 233.0 + 4.0],
                                                [366.5 - 15.0, 366.5 + 4.0],
                                                [763.9 - 15.0, 763.9 + 4.0], # 10번 신호등
                                                [901.6 - 15.0, 901.6 + 4.0],
                                                [1246.5- 15.0, 1246.5 + 4.0],
                                                [1380.5 - 15.0, 1380.5 + 4.0],
                                                [1426.4 - 15.0, 1426.4 + 4.0]], # 141.2, 196.0, 328.8, 727.2, 865.4, 1211.4, 1344.4, 1390.4
                    "Traffic_light_left" : [[1079.5 - 15.0, 1079.5 + 4.0],
                                            [1079.5 - 15.0, 1079.5 + 4.0]]} # 엥 좌회전 한번이네 1043.2

elif WHERE == 4: # 만해 배달 테스트
    GLOBAL_PATH_NAME = "MH_D.npy" 
    mission_coord = {"Parking" : [9999.2, 9999.2], "Static_Obstacle" : [9999, 9999],
                    "Dynamic_Obstacle" : [99999.5, 99999.2], "Cross_Walk" : [9999, 9999],
                    "School_Zone" : [9999, 9999], "Delivery" : [6, 1000],
                    "Traffic_light_straight" : [[9106.8 - 15.0, 9106.8 + 4.0],
                                                [9106.8 - 15.0, 9106.8 + 4.0],],
                    "Traffic_light_left" : [[9999, 9999],[9999, 9999]]}

elif WHERE == 5: # 직선 테스트
    GLOBAL_PATH_NAME = "MH_straight.npy" 
    mission_coord = {"Parking" : [9999.2, 9999.2], "Static_Obstacle" : [9999, 9999],
                    "Dynamic_Obstacle" : [9999, 9999], "Cross_Walk" : [9999, 9999],
                    "School_Zone" : [9999, 9999], "Delivery" : [6000, 7000],
                    "Traffic_light_straight" : [[360.5 - 15.0, 360.5 + 4.0],
                                                [360.5 - 15.0, 360.5 + 4.0],],
                    "Traffic_light_left" : [[9999, 9999],[9999, 9999]]}

elif WHERE == 6: # 직선 테스트
    GLOBAL_PATH_NAME = "DP_straight.npy" 
    mission_coord = {"Parking" : [9999.2, 9999.2], "Static_Obstacle" : [9999, 9999],
                    "Dynamic_Obstacle" : [99999.5, 99999.2], "Cross_Walk" : [9999, 9999],
                    "School_Zone" : [9999, 9999], "Delivery" : [6000, 7000],
                    "Traffic_light_straight" : [[9106.8 - 15.0, 9106.8 + 4.0],
                                                [9106.8 - 15.0, 9106.8 + 4.0],],
                    "Traffic_light_left" : [[9999, 9999],[9999, 9999]]}


def distance(mission_pose, s):
    determine = False
    mission_start = mission_pose[0]
    mission_final = mission_pose[1]
    if (s >= mission_start) and (s <= mission_final):
        determine = True
    return determine

class publish_erp():
    def __init__(self):
        self.erp_pub = rospy.Publisher("speed_planner", erp_write, queue_size=1)
        self.erp = erp_write()

    def pub_erp(self, speed, steer):
        self.erp.write_speed = speed
        self.erp.write_steer = steer
        self.erp_pub.publish(self.erp)

class Mission_State():
    def __init__(self):
        self.mission_state = 0
        self.mission_zone = 0
        self.mission_zone_trf = 0
        self.mission_ing = 0
        self.mission_ing_trf = 0
    
    def mission_loc(self, s):
        global mission_coord

        self.mission_zone = self.mission_zone_trf = 0

        if (distance(mission_coord["Parking"], s)):
            self.mission_zone = 1
        elif (distance(mission_coord["Dynamic_Obstacle"], s)):
            self.mission_zone = 2
        elif (distance(mission_coord["Static_Obstacle"], s)):
            self.mission_zone = 3
        elif (distance(mission_coord["Delivery"], s)):
            self.mission_zone = 4
        elif (distance(mission_coord["School_Zone"], s)):
            self.mission_zone = 5
        
        for i in mission_coord["Traffic_light_straight"]:
            if (distance(i, s)):
                self.mission_zone_trf = 8
            
        for i in mission_coord["Traffic_light_left"]:
            if (distance(i, s)):
                self.mission_zone_trf = 9

    def mission_update(self, s):
        self.mission_loc(s)

        if (self.mission_zone == 0): # 현재 미션존이 아니라면 무조건 크루징 모드
            self.mission_state = self.mission_zone
            self.mission_ing = 0

        else: # 미션존 안에 있는 경우
            if self.mission_ing == 0:
                print("미션 시작")
                self.mission_state = self.mission_zone
                self.mission_ing = 1
            elif self.mission_ing == 1:
                self.mission_state = self.mission_zone
            elif self.mission_ing == 2:
                self.mission_state = 0

        if (self.mission_zone_trf == 8) or (self.mission_zone_trf == 9):
            if self.mission_ing_trf == 0:
                print("신호등 인식 시작")
                self.mission_ing_trf = 1
            elif self.mission_ing_trf == 1:
                pass
            elif self.mission_ing_trf == 2:
                pass
        else:
            self.mission_ing_trf = 0

    def mission_done(self):
        print("미션 완료")
        self.mission_ing = 2
    
    def mission_done_trf(self):
        print("신호등 미션 완료")
        self.mission_ing_trf = 2

def main():
    global WHERE
    rate = rospy.Rate(10)
    speed, steer = 0.0, 0.0

    pub = publish_erp()
    erp = sub_erp_state()
    MS = Mission_State()

    # Global Path 선언
    PATH_ROOT=(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))+"/path/npy_file/path/"
    gp_name = PATH_ROOT + GLOBAL_PATH_NAME
    GB = GlobalPath(gp_name)

    # 미션 선언
    Mission_cruising = mission_cruising(GLOBAL_PATH_NAME)    # path_tracking 할 경로 넣어주기 (macaron_3.path 폴더 안에 있어야함)
    Mission_parking = mission_parking(WHERE)
    Mission_dynamic_obstacle = mission_dynamic_obstacle(WHERE)
    Mission_traffic_straight = mission_traffic_straight(WHERE)
    Mission_traffic_left = mission_traffic_left(WHERE)
    Mission_delivery = mission_delivery()

    print("국토교통부 장관상 내놔랏!!")
    rospy.sleep(1)

    while not rospy.is_shutdown():
        s, q = GB.xy2sl(erp.pose[0], erp.pose[1])
        print(s), 'current s'
        state = MS.mission_update(s)

        if (MS.mission_state == 0): # 크루징(디폴트) 모드 (장애물 회피 X)
            print("크루징---")
            steer = Mission_cruising.path_tracking(erp.pose, erp.heading)
            speed = CRUISING_SPEED
            
        elif (MS.mission_state == 1): # 주차 모드
            if Mission_parking.done == True:
                rospy.sleep(2)
                MS.mission_done()
                Mission_parking.reset()
            speed, steer = Mission_parking.run(erp.pose, erp.heading, erp.obs, erp.lane_dis, erp.erp_ENC, erp.erp_steer)
            if s < 87.0:
                steer = Mission_cruising.path_tracking(erp.pose, erp.heading)

        elif (MS.mission_state == 2): # 동적장애물 모드
            steer = Mission_cruising.path_tracking(erp.pose, erp.heading)
            speed = 80
            if Mission_dynamic_obstacle.scan(erp.pose, erp.obs) == "stop":
                speed = -201

        elif (MS.mission_state == 3): # 정적장애물 모드
            steer = Mission_cruising.static_obstacle(erp.pose, erp.heading, erp.obs)
            speed = 121
        
        elif (MS.mission_state == 4): # 배달 모드
            speed, steer, st_del = Mission_delivery.run(erp.pose, erp.heading, erp.delivery, erp.obs, s)
            if st_del == 1 :
                steer = Mission_cruising.path_tracking(erp.pose, erp.heading)
            elif st_del == 2:
                MS.mission_done()
        
        elif (MS.mission_state == 5): # 감속 모드
            steer = Mission_cruising.path_tracking(erp.pose, erp.heading)
            speed = 100
        
        if (MS.mission_zone_trf == 8): # 직진 신호등 교차로 모드
            for i in mission_coord["Traffic_light_straight"]:
                if i[1] - 3 <= s <= i[1]:
                    MS.mission_done_trf()
                    Mission_traffic_straight.reset()
            speed_traffic = Mission_traffic_straight.run(s, erp.trffic, erp.erp_speed)
            if speed_traffic <= speed:
                speed = speed_traffic
            if Mission_traffic_straight.done == True:
                MS.mission_done_trf()
                Mission_traffic_straight.reset()
        
        elif (MS.mission_zone_trf == 9): # 좌회전 신호등 교차로 모드
            for i in mission_coord["Traffic_light_left"]:
                if i[1] - 3 <= s <= i[1]:
                    MS.mission_done_trf()
                    Mission_traffic_left.reset()
            speed_traffic = Mission_traffic_left.run(s, erp.trffic, erp.erp_speed)
            if speed_traffic <= speed:
                speed = speed_traffic
            if Mission_traffic_left.done == True:
                MS.mission_done_trf()
                Mission_traffic_left.reset()

        # 속도를 줄이자 헿
        if 529 < s < 552 or 1108 < s < 1162:
            speed = 100

        pub.pub_erp(speed, steer)
        # print(erp.trffic, 'traffic_info')
        rate.sleep()

if __name__ == '__main__':
    rospy.init_node("state_node", anonymous=True)
    main()