#!/usr/bin/env python

# Matt Butler and Sam Wane. Harper Adams University 2022.
# recieves mission as a  list of lists on argv[1], and a starting point on argv[2].
# to test from a terminal:
# python nav.py '[["-3.0953963", "52.4604236", "start"], ["-1.9692977", "53.0455683", "middle"], ["-1.0519393", "52.5941015", "end"]]' 0
# requires Python2 and ROS environment

import socket # to send out status updates (and/or recieve commnds)
import datetime

import sys
import json
import time
from math import pi, sin, cos, tan, sqrt, atan2

import rospy
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64
from std_msgs.msg import Int16
from latlongtoutm import *
from sensor_msgs.msg import NavSatFix, NavSatStatus, Imu
from ublox_msgs.msg import NavSTATUS, NavRELPOSNED9
import utm
from nav_msgs.msg import Odometry
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped

L=0.69

# Create a UDP socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Bind the socket to the port
server_address = ('127.0.0.1', 1963)
s.bind(server_address)
# print("Recieving on UDP port 1963")

# Enable broadcasting mode
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# function to send a string message
def sendUDPinfo(msg):
    b = msg.encode('utf-8')
    s.sendto(b, ("<broadcast>", 1964))

# function to send a target message to UI
def sendUDPtarget(msg):
    msg = str(msg)
    b = msg.encode('utf-8')
    s.sendto(b, ("<broadcast>", 1965))
    
# function to send a string message
def sendUDPdist(msg):
    msg = str(msg)
    b = msg.encode('utf-8')
    s.sendto(b, ("<broadcast>", 1968))
    
# function to send a heading message to UI
def sendUDPheading(msg):
    msg = str(msg)
    b = msg.encode('utf-8')
    s.sendto(b, ("<broadcast>", 1966))
    
# function to send a steering message to UI
def sendUDPsteering(msg):
    msg = str(msg)
    b = msg.encode('utf-8')
    s.sendto(b, ("<broadcast>", 1967))
    

## load passed in parameters (and check them)

try:
    mission = sys.argv[1]
except: # default values for testing. WARNING: Can't use Thonny - it uses Python 3!
    #mission = '[["-3.0953963", "52.4604236", "start"], ["-1.9692977", "53.0455683", "middle"], ["-1.0519393", "52.5941015", "end"]]'
    print('No mission argument given - quitting')
    time.sleep(3)
    sys.exit()

try:
    start_point = sys.argv[2]
    print("Starting from point " + str(int(start_point)+ 1))
    sendUDPinfo("Starting from point " + str(int(start_point)+ 1))
except: # default values for testing. WARNING: Thonny uses Python 3!!!!!!!!!
    print('No start point provided - start at beginning')
    sendUDPinfo('No start point provided - start at beginning')
    start_point = "0"

try: # use Python list
    m_list = json.loads(mission)
    maxpos=len(m_list)
except:
    print('Mission is malformed - quitting')
    sendUDPinfo('Mission is malformed - quitting')
    time.sleep(6)
    sys.exit()

time.sleep(3) # just for reading messages during development

lasttime=0.0
integError=0.0
lastError=0.0

head=0
aimbear=0
lat=0
lon=0
gpsstatus=0
Nr=0
Er=0

speed=0.0
steer=0.0
pointspeed=0.0
pointtype="start,PTP,0.7"
name="start"
movetype="PTP"
pointspeed=0.7
maxsteer=30.0
minsteer=-30.0
Ks=0.25
Kis=0.0
Kds=0
begin=0
goal_pos=0


carrotaimdist=2.0

def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)


def bearingwrap(b):
    if (b>=360):
        b=b-360
    if (b<=0):
        b=b+360
    return b

def bear_to_deg(b):
    deg=450-b
    deg=bearingwrap(deg)
    return deg

def deg_to_bear(d):
    b=450-d
    b=bearingwrap(b)
    return b


def GPScallback(msg):
    global Nr
    global Er
    global lat
    global lon
    global gpsstatus
    lat=msg.latitude
    lon=msg.longitude
    gpsstatus=msg.status.status
    c,Er,Nr = LLtoUTM(23,lat, lon) #current position, ER,Nr in UTM
    #Echo lat,lon to GUI here
    posinfo= "Lat: %f, Lon: %f " % (lat, lon) 
    sendUDPinfo(posinfo)
    
def HEADcallback(msg):
    global head
    head = float(msg.relPosHeading)
    head=bearingwrap(head+90)
    h=head
    if h<0:h=360+h
    sendUDPheading(int(h))
      

def bearing_to(ce,cn,ge,gn):
    bear=math.atan2(ge-ce,gn-cn)*57.2957795
    if (bear<0):
        bear=bear+360
    return bear



def closest_bearing_difference(current_bearing,goal_bearing):
    cl_bearing=goal_bearing-current_bearing
    if (cl_bearing>180):
        cl_bearing=(cl_bearing-360)
    if (cl_bearing<-180): 
        cl_bearing=(cl_bearing+360)
    return cl_bearing

def dist_bearing(StN,StE,EnN,EnE):
    dist=sqrt(((EnN-StN)*(EnN-StN))+((EnE-StE)*(EnE-StE)))
    bearing=atan2((EnE-StE),(EnN-StN))
    bearing=bearing*57.29578
    if bearing<0:
        bearing=360+bearing
    return (dist, bearing)


def Output_PID(Kp,  Ki,  Kd,  error,  maxerror):
        global begin
        
        global integError
        global lastError
        s=rospy.Time.now().to_sec()
        dt=s-begin      
        begin=s  
        if ((error > -maxerror) and (error < maxerror)): integError += error * dt
        compP = error * Kp
        compI = integError * Ki
        compD = ((error - lastError) / dt) * Kd
        lastError = error
        
        return compP + compI + compD


def send_twist():
 
    global steer
    global speed
    global cmdman
    twist=Twist()
    steerrad=float(steer)/180*pi
    x_speed=float(speed)
    zdot=(x_speed*tan(-steerrad))/L
    # create a twist message, fill in the details
    twist = Twist()
    twist.linear.x = x_speed                   # our forward speed
    twist.linear.y = 0; twist.linear.z = 0     # we can't use these!        
    twist.angular.x = 0; twist.angular.y = 0   #          or these!
    twist.angular.z = zdot
    cmdman.publish(twist)

def carrot_point(CN,CE,N1,E1,N2,E2,Aim):

	
	AF=((N1-CN)*(N1-N2)+(E1-CE)*(E1-E2))/(sqrt((N1-N2)**2+(E1-E2)**2))

	AB=sqrt((N1-N2)**2+(E1-E2)**2)
	FN=N1+(N2-N1)*(AF/AB)
	FE=E1+(E2-E1)*(AF/AB)

	carrot_N=FN+(N2-N1)*(Aim/AB)

	carrot_E=FE+(E2-E1)*(Aim/AB)
	
	return carrot_N,carrot_E

def seek_point_carrot(AN,AE,BN,BE):
    global aim_bear,Nr,Er,head,goal_N,goal_E
    global steer
    global carrotaimdist
    
    C_N,C_E=carrot_point(Nr,Er,AN,AE,BN,BE,carrotaimdist)
    dist2, goalbearing=dist_bearing(Nr,Er,C_N,C_E)

    aim_bear=closest_bearing_difference(head,goalbearing)
    dist, gb=dist_bearing(Nr,Er,BN,BE)
   #Control element
    
    steer=Output_PID(Ks,  Kis,  Kds,  aim_bear,  20)
    steer = clamp(steer, minsteer, maxsteer)
    sendUDPsteering(int(steer)) #GUI
    sendUDPdist(int(dist))
    
    return dist,aim_bear

def seek_point(plat,plon):
    global aim_bear,Nr,Er,head,goal_N,goal_E
    global steer
    (z, goal_E, goal_N) = utm.LLtoUTM(23, plat,plon)
    dist, goalbearing=dist_bearing(Nr,Er,goal_N,goal_E)
    aim_bear=closest_bearing_difference(head,goalbearing)
   #Control element
    
    steer=Output_PID(Ks,  Kis,  Kds,  aim_bear,  20)
    steer = clamp(steer, minsteer, maxsteer)
    sendUDPsteering(int(steer)) #GUI
    sendUDPdist(int(dist))
    
    return dist,aim_bear

def shutdown(self):
    rospy.loginfo("Stopping the robot...")
    self.cmd_vel.publish(Twist())

def get_pos(p):
    print "Get pos"+str(p)
    lat=float(m_list[p][1])
    lon=float(m_list[p][0])
    pointtype=(m_list[p][2])
    s_list = pointtype.split(",")
    name=s_list[0]
    movetype="PTP" #Values incase no values present in CSV e.g. "start,CP,0.7"
    speed=0.6
    if len(s_list)>1:
        movetype=name=s_list[1]
    if len(s_list)>2:
        speed=float(s_list[2])
    return lat,lon,name,movetype,speed




rospy.init_node('navigate_node_red_points',anonymous=False)
    
 
#pubStr=rospy.Publisher("/CeresSteer", Float64, queue_size=1)
#pubSpd=rospy.Publisher("/CeresSpeed", Float64, queue_size=1) 
cmdman = rospy.Publisher('/cmd_vel_mux/cmd_vel_nav', Twist, queue_size=1) 
rospy.Subscriber("/gps/fix", NavSatFix, GPScallback)
#rospy.Subscriber("/gps/navstatus", NavSTATUS, Statuscallback)

#rospy.Subscriber("gps/navrelposned", NavRELPOSNED9, HEADcallback)
rospy.Subscriber("gps/heading", NavRELPOSNED9, HEADcallback)
begin=rospy.Time.now().to_sec()

#pos=1
max_pos=len(m_list)

pos=int(start_point)    
sys.stderr.write(str(mission) + ' ' + start_point)
pointlat,pointlon,name,movetype,pointspeed=get_pos(pos)
print name
print movetype
print pointspeed
#wait until got GPS value
Er=0
while Er==0:
    prevE=Er
    prevN=Nr
print "Got GPS fix"
print prevN
print prevE
speed=0.0
while (pos<maxpos):
        #show_point()
    
    if movetype=="CP":
        (z, BE, BN) = utm.LLtoUTM(23, pointlat,pointlon)
        dist,aim_bearing=seek_point_carrot(prevN,prevE,BN,BE)
    else:
        dist,aim_bearing=seek_point(pointlat,pointlon)
    h=aim_bearing  #Send aim bearing to GUI
    if h<0:h=360+h
    sendUDPtarget(int(h))
    #print "dist"+str(dist)
    if dist>2:
        speed=pointspeed
    else:
        prevE=goal_E
        prevN=goal_N
        print "Got last point for prevNE"
        print prevN
        print prevE
        pos=pos+1
        if pos<maxpos:
            pointlat,pointlon,name,movetype,pointspeed=get_pos(pos)
            print name
            print movetype
            print pointspeed
            
    #publish steer and speed
    #pubSpd.publish(speed)
    send_twist()
    rospy.sleep(0.1)
n=0
while (n<5):
    speed=0.0
    send_twist()
    n=n+1
    rospy.sleep(0.5)
print "Finished"



