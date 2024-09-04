#!/usr/bin/env python3

#https://pypi.org/project/pyubx2/
import rospy
import serial
from serial import Serial
from pyubx2 import UBXReader
import time

from ublox_msgs.msg import NavSTATUS, NavRELPOSNED9


port = '/dev/ttyGPS'
print ("Opening on port")
print (port)
connect_tries = 1
portOK = False

while not portOK:

    try: 
        s = serial.Serial(port,57600,timeout=1,writeTimeout=0)
        portOK = True
        print()
        print ('GPS is plugged in - wait 5 secs')
    except:
        print ("Port " + port + " not connected  - " + str(connect_tries) + " tries")
        time.sleep(2)
        connect_tries = connect_tries + 1
        
#s.open()
s.flush()
s.close()
time.sleep(5)



stream = Serial('/dev/ttyGPS')

from sensor_msgs.msg import NavSatFix, NavSatStatus

rospy.init_node('UBLOX', anonymous=True)
pubgps = rospy.Publisher("/gps/fix", NavSatFix, queue_size=1)
pubrelpos = rospy.Publisher("/gps/heading", NavRELPOSNED9, queue_size=1)
 
msg = NavSatFix()
relpos = NavRELPOSNED9()
#navstat = NavSTATUS()



try:
    ubr = UBXReader(stream, protfilter=2)
except:
    print("bad ubr stream read")
    
print()
print ('Running. Look at topics: gps/fix and gps/heading')
print ('Saving headings to headings_log.csv on the desktop')



for (raw_data, parsed_data) in ubr:
    try:
        if (parsed_data.identity == 'NAV-PVT'):
            msg.latitude = parsed_data.lat
            msg.longitude = parsed_data.lon
            msg.status.status = parsed_data.fixType
            #print(parsed_data)
        if (parsed_data.identity == 'NAV-RELPOSNED'):
            # set validity
            relpos.flags = parsed_data.relPosHeadingValid
            # set heading

            relpos.relPosHeading = int(parsed_data.relPosHeading)
            #print(parsed_data)
            msg.header.stamp = rospy.Time.now()
            pubgps.publish(msg)
            pubrelpos.publish(relpos)
    except:
        print("Bad read")






