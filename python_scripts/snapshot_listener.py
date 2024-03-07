#!/usr/bin/env python3

import rospy
from gmlaas.msg import GraphBuilderMsg
from apriltag_ros.msg import AprilTagDetectionArray
from gazebo_msgs.msg import ModelStates
from message_filters import Subscriber, TimeSynchronizer
import datetime as dt
import os
import time
import csv
import tf


current_dir = os.path.realpath(__file__)
package_dir = os.path.dirname(os.path.dirname(current_dir))

try :
    rospy.loginfo("Trying to get the name_arg parameter from the launch file...")
    env_csvfile = rospy.get_param('~env_arg')
    name_csvfile = rospy.get_param('~name_arg')
except KeyError as e:
    rospy.loginfo("Trying to get the name_arg parameter from the rosrun command line...")
    argv = rospy.myargv()[1:]
    print(argv)
    print(len(argv))
    if len(argv) == 2:
        env_csvfile = argv[0]
        name_csvfile = argv[1]
    else :
        rospy.loginfo("... Please set the name_arg parameter in running the launch file : roslaunch gmlaas snapshot_listener.launch nam_arg:=\"csvNameFile\"") 
        rospy.loginfo("or in running the rosrun command line : rosrun gmlaas snapshot_listener.py csvNameFile")
        raise ValueError("Arg name_arg parameter not properly called.")


file1 = open(f"{package_dir}/datasets/snapshots/{env_csvfile}/{name_csvfile}_graph_dataset.csv", "w")
file2 = open(f"{package_dir}/datasets/snapshots//{env_csvfile}/{name_csvfile}_tags_dataset.csv", "w")

file3 = open(f"{package_dir}/datasets/data/{name_csvfile}_pose.csv", "w")
filewriter3 = csv.writer(file3, delimiter=';')


datetime = dt.datetime.now()
formatted_datetime = datetime.strftime("%Y-%m-%d %H:%M")

#Headers
file1.write(f"<TITLE : Snapshot of {name_csvfile}: Graph Dataset (YYYY-MM-DD HH:MM): {formatted_datetime} >\n")
file2.write(f"<TITLE : Snapshot of {name_csvfile}: Tags Dataset (YYYY-MM-DD HH:MM): {formatted_datetime} >\n")
file1.write("timestamp sec, timpestamp nsecs, number_of_tags, adjacency_matrix, indexed_matrix\n") 
file2.write("timestamp, timpestamp nsecs, tag_id, x, y, z\n")

# Write title
filewriter3.writerow(['time', 'x', 'y', 'z', 'roll', 'pitch', 'yaw'])

success = False

def callback(graph_data, tag_detections,gaz_model):
    print("begin callback..")
    timestamp_secs = graph_data.header.stamp.secs #int
    timestamp_nsecs = graph_data.header.stamp.nsecs #int

    adjacency_matrix = graph_data.adjacency_matrix
    indexed_matrix = graph_data.indexed_matrix

    # Write data to file1
    file1.write(f"{timestamp_secs}; {timestamp_nsecs}; {len(tag_detections.detections)}; {adjacency_matrix}; {indexed_matrix}\n")


    #write data to file 3
    pose_id = 1
    x = gaz_model.pose[pose_id].position.x
    y = gaz_model.pose[pose_id].position.y
    z = gaz_model.pose[pose_id].position.z
    orientation = gaz_model.pose[pose_id].orientation
    roll, pitch, yaw = tf.euler_from_quaternion([orientation.x, orientation.y, orientation.z, orientation.w])
    filewriter3.writerow([ x, y, z, roll, pitch, yaw])


    # Process tag detections as needed
    for detection in tag_detections.detections:
        tag_id = detection.id[0]
        x = detection.pose.pose.pose.position.x
        y = detection.pose.pose.pose.position.y
        z = detection.pose.pose.pose.position.z
        print(f"Tag {tag_id} detected at coordinates ({x}, {y}, {z}) at timestamp : {timestamp_secs}.{timestamp_nsecs}")

        # Write data to file2
        file2.write(f"{timestamp_secs}; {timestamp_nsecs}; {tag_id}; {x}; {y}; {z}\n")
        
        file1.flush() 
        file2.flush() 
        file3.flush()
        success = True

    if success:
        rospy.loginfo("Data successfully written to files.")
        rospy.signal_shutdown("Data received and written to file.")

def register_callback(sync, callback):
    try:
        sync.registerCallback(callback)
    except RuntimeError as e:
        rospy.loginfo(f"Error occurred during callback registration: {e}")


if __name__ == "__main__":

    rospy.init_node("snapshot_listener", anonymous=False)

    # Use message_filters to synchronize messages from both topics based on timestamps
    graph_sub = Subscriber("graph_building/data", GraphBuilderMsg)
    tag_sub = Subscriber("/tag_detections", AprilTagDetectionArray)
    gaz_sub = Subscriber("/gazebo/model_states",ModelStates)

    
    sync = TimeSynchronizer([graph_sub, tag_sub,gaz_sub], queue_size=30)
    
    rospy.loginfo("Registering callback...")
    register_callback(sync, callback)
    rospy.spin()




            
