#!/usr/bin/env python

# license removed for brevity

import rospy
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import actionlib
from actionlib_msgs.msg import *
from std_msgs.msg import String  # Importa il tipo di messaggio String
from geometry_msgs.msg import PoseWithCovarianceStamped
from tf.transformations import euler_from_quaternion
import math
from nav_msgs.msg import Path

class GoForwardAvoid():
    def __init__(self):
        rospy.init_node('navigation', anonymous=False)

        # Inizializzazione e setup
        self.current_pose = None
        self.path_length = 0.0

        # what to do if shut down (e.g. ctrl + C or failure)
        rospy.on_shutdown(self.shutdown)

        self._point_list = rospy.get_param('navigation/Locations')
        self._sleep_timer = rospy.Rate(5.0)
        
        # Aggiungi un subscriber al topic 'target_location'
        rospy.Subscriber('target_location', String, self.target_location_callback)
        rospy.Subscriber('amcl_pose', PoseWithCovarianceStamped, self.pose_callback)
        rospy.Subscriber("move_base/TebLocalPlannerROS/local_plan", Path, self.path_callback)
        # Inizializza la variabile target
        self.target = None


    def pose_callback(self, msg):
        self.current_pose = msg.pose.pose

    def path_callback(self, msg):
        self.path_length = self.calculate_path_length(msg)
        rospy.loginfo(f"Current path length: {self.path_length} meters")

    def calculate_path_length(self, path):
        length = 0.0
        for i in range(len(path.poses) - 1):
            pose1 = path.poses[i].pose
            pose2 = path.poses[i + 1].pose
            dx = pose1.position.x - pose2.position.x
            dy = pose1.position.y - pose2.position.y
            length += math.sqrt(dx**2 + dy**2)
        return length

    def target_location_callback(self, msg):
        # Imposta la variabile target con il messaggio ricevuto
        self.target = msg.data
        rospy.loginfo(f"Target location updated to: {self.target}")
        # tell the action client that we want to spin a thread by default
        self.move_base = actionlib.SimpleActionClient("move_base", MoveBaseAction)
        rospy.loginfo("wait for the action server to come up")
        # allow up to 5 seconds for the action server to come up
        self.move_base.wait_for_server(rospy.Duration(5))
        
        # Create a new goal with the MoveBaseGoal constructor
        goal = MoveBaseGoal()
        for location in self._point_list:
            if self.target in location:
                data = location[self.target]  # Usa self.target per accedere al punto corretto
                position = data['position']
                orientation = data['orientation']
                print(f"Target Position: {position}")
                print(f"Target Orientation: {orientation}")


                #set up the frame parameters
                goal.target_pose.header.frame_id = 'map'
                goal.target_pose.header.stamp = rospy.Time.now()
                goal.target_pose.pose.position.x = position['x']
                goal.target_pose.pose.position.y = position['y']
                goal.target_pose.pose.position.z = position['z']
                goal.target_pose.pose.orientation.x = orientation['x']
                goal.target_pose.pose.orientation.y = orientation['y']
                goal.target_pose.pose.orientation.z = orientation['z']
                goal.target_pose.pose.orientation.w = orientation['w']

                #start moving
                self.move_base.send_goal(goal)
                while not rospy.is_shutdown():
                    state = self.move_base.get_state()
                    if state in [GoalStatus.SUCCEEDED, GoalStatus.ABORTED, GoalStatus.REJECTED]:
                        break
                    if self.path_length < 1.0:
                        rospy.loginfo("Goal is within 1 meter.")
                    rospy.sleep(1)
                if state == GoalStatus.SUCCEEDED:
                    rospy.loginfo("Goal reached successfully.")
                else:
                    rospy.loginfo("Failed to reach the goal.")
    
    
    def shutdown(self):
        rospy.loginfo("Stop")


if __name__ == '__main__':
    try:
        point_mb = GoForwardAvoid()
        rospy.spin()

    except rospy.ROSInterruptException:
        rospy.loginfo("Exception thrown")