#! /bin/bash

#export LD_LIBRARY_PATH=/opt/opencv-4.1.0/lib:$LD_LIBRARY_PATH
#export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
#export PYTHONPATH=$PYTHONPATH:/usr/local/lib

source /opt/ros/kinetic/setup.bash
source /home/pi/catkin_ws/devel/setup.bash
source /home/pi/catkin_ws_matt/devel/setup.bash

export ROS_MASTER_URI=http://localhost:11311

roscore &
lxterminal --command /home/pi/Desktop/ceres_startup/gpsdriver.sh &
lxterminal --command /home/pi/Desktop/ceres_startup/arduino.sh &
lxterminal --command /home/pi/Desktop/ceres_startup/cmd_vel_mux.sh &
lxterminal --command /home/pi/Desktop/ceres_startup/path.sh &

#chromium-browser --incognito http://localhost:1880/ui/#firefox -private -url  http://localhost:1880/ui
firefox

#read -p "Press a key to kill ROS"


# ceresrobot@gmail.com
# harper2022
