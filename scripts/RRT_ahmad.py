#!/usr/bin/env python


#--------Include modules---------------
from copy import copy
import rospy
from visualization_msgs.msg import Marker
from std_msgs.msg import String
from geometry_msgs.msg import Point
from nav_msgs.msg import OccupancyGrid
import actionlib_msgs.msg
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import actionlib
import tf



from os import system
from random import random
from numpy import array,concatenate,vstack,delete,floor,ceil,arctan2,append
from numpy import linalg as LA
from numpy import all as All
from numpy import inf
from numpy import cos,sin
#-----------------------------------------------------
# Subscribers' callbacks------------------------------
mapData=OccupancyGrid()


def mapCallBack(data):
    global mapData
    mapData=data
    


def index2point(indx,mapData):
	xdim=mapData.info.width
	ydim=mapData.info.height
	resolution=mapData.info.resolution
	Xstartx=mapData.info.origin.position.x
	Xstarty=mapData.info.origin.position.y 
	yr=ceil(indx/xdim)
	xr=indx-(floor(indx/xdim))*xdim
	xr=xr*resolution+Xstartx
	yr=yr*resolution+Xstarty
	return array([xr,yr])

class RRT:
	V=[]
	child=[]
	parent=[]


	def __init__(self,eta,xinit):
		self.eta=eta
		self.xinit=xinit
		RRT.V=array([xinit])


		self.pub = rospy.Publisher('treeMarker', Marker, queue_size=10)
		self.pub2 = rospy.Publisher('pathMarker', Marker, queue_size=10)


		self.points=Marker()
		self.line=Marker()
		self.line2=Marker()
		
		#Set the frame ID and timestamp.  See the TF tutorials for information on these.
		self.points.header.frame_id=self.line.header.frame_id="/map"
		self.line2.header.frame_id="/map"
		self.points.header.stamp=self.line.header.stamp=self.line2.header.stamp=rospy.Time.now()

		self.points.ns=self.line.ns = "tree"
		self.line2.ns="path"
		self.points.id = 0
		self.line.id =1
		self.line2.id =2

		self.points.type = Marker.POINTS
		self.line.type=Marker.LINE_LIST
		self.line2.type=Marker.LINE_LIST
		#Set the marker action.  Options are ADD, DELETE, and new in ROS Indigo: 3 (DELETEALL)
		self.points.action = self.line.action =self.line2.action = Marker.ADD;

		self.points.pose.orientation.w = self.line.pose.orientation.w = self.line2.pose.orientation.w = 1.0;

		self.line.scale.x = 0.02;
		self.line2.scale.x = 0.02;
		self.points.scale.x=0.05; 
		self.line.scale.y= 0.02;
		self.line2.scale.y= 0.02;
		self.points.scale.y=0.05; 

		self.line.color.r =9.0/255.0
		self.line.color.g= 91.0/255.0
		self.line.color.b =236.0/255.0
		self.line2.color.r =255.0/255.0
		self.line2.color.g= 0.0/255.0
		self.line2.color.b =0.0/255.0
		self.points.color.r = 255.0/255.0
		self.points.color.g = 244.0/255.0
		self.points.color.b = 0.0/255.0

		self.points.color.a=1;
		self.line.color.a = 0.6;
		self.line2.color.a = 1.0;
		self.points.lifetime =self.line.lifetime =self.line2.lifetime = rospy.Duration();

		self.marker_line_points=[]
		self.marker_points=[]
		self.temp_point_obj=Point()


		
	# Nearest function
	def nearest(self,x):
		n=inf
		for i in range(0,RRT.V.shape[0]):
			n1=LA.norm(RRT.V[i,:]-x)
			if (n1<n):
				n=n1
				result=i  
		return RRT.V[result,:]



	def steer(self,x0,x1,eta):
		r=LA.norm(x0-x1)
		if r>eta:
			r=eta
		
		theta=arctan2(x1[1]-x0[1],x1[0]-x0[0])

		a=x0[0]+r*cos(theta)
		b=x0[1]+r*sin(theta)
		xnew=array([a,b])
		return xnew



	def extend(self,x_new,x_nearest):
		RRT.V=vstack([RRT.V,x_new])
		RRT.child.append(list(x_new))
		RRT.parent.append(list(x_nearest))


		self.temp_point_obj.x=x_nearest[0]
		self.temp_point_obj.y=x_nearest[1]

		self.marker_line_points.append(copy(self.temp_point_obj))


		self.temp_point_obj.x=x_new[0]
		self.temp_point_obj.y=x_new[1]

		self.marker_points.append(copy(self.temp_point_obj))
		self.marker_line_points.append(copy(self.temp_point_obj))

	def visualize_tree(self):
		self.points.points=self.marker_points
		self.line.points=self.marker_line_points
		self.pub.publish(self.points)
		self.pub.publish(self.line)

	def gridCheck(self,mapData,Xp):
		resolution=mapData.info.resolution
		Xstartx=mapData.info.origin.position.x
		Xstarty=mapData.info.origin.position.y

		width=mapData.info.width
		Data=mapData.data
		# check if points are in freespace or not
		# c=100 means grid cell occupied
		# c=0 means grid cell is free
		#c=-1 means grid cell is unknown
		index=(  floor((Xp[1]-Xstarty)/resolution)*width)+( floor((Xp[0]-Xstartx)/resolution) )
		c=100
		if int(index) < len(Data):
			c=Data[int(index)]

		return c

		# ObstacleFree function-------------------------------------

	def obstacleFree(self,xnearest,xnew,mapsub):
		out=0

		rez=mapsub.info.resolution*.2
		stepz=int(ceil(LA.norm(xnew-xnearest))/rez)
		xi=xnearest
		obs=0
		unk=0
		 

		for c in range(0,stepz):
			xi=self.steer(xi,xnew,rez)
			if (self.gridCheck(mapsub,xi) ==100):
				obs=1
				break
			elif (self.gridCheck(mapsub,xi) ==-1):
				unk=1
				break


		if (unk==1):
			out=-1

		if (obs==1):
			out=0

		if (obs!=1 and unk!=1):
			out=1


		return out

	def makePlan(self,x):
		path=[list(x)]
		vis_path=[]
		
		row=RRT.child.index(list(x))
		temp=Point()
		while row>=0:
			parentx=RRT.parent[row]
			path.append(RRT.parent[row])
			
			temp.x=RRT.child[row][0]
			temp.y=RRT.child[row][1]
			vis_path.append(copy(temp))
			
			temp.x=RRT.parent[row][0]
			temp.y=RRT.parent[row][1]
			vis_path.append(copy(temp))
			try:
				row=RRT.child.index(parentx)
			except:
				row=-1
				
		self.line2.points=vis_path
		self.pub2.publish(self.line2)
		return path,vis_path
			
			
			



# Node----------------------------------------------
def node():
	
	global mapData

	eta=1
	x_goal=array([-3.,-3.])

	rospy.Subscriber("map", OccupancyGrid, mapCallBack)
	rospy.init_node('RRT', anonymous=False)
	rate = rospy.Rate(100)	

	
	x_init=array([0.,0.])
	ETA=1
	tree=RRT(ETA,x_init)

#-------------------------------RRT------------------------------------------
	while not rospy.is_shutdown():

	 
	# Sample free
		indxRand= floor( len(mapData.data)*random())
		x_rand = index2point(indxRand,mapData)
# Nearest
		x_nearest=tree.nearest(x_rand)
# Steer
		x_new=tree.steer(x_nearest,x_rand,ETA)
# ObstacleFree
		if tree.obstacleFree(x_nearest,x_new,mapData):
			tree.extend(x_new,x_nearest)
			tree.visualize_tree()
		
# finding path
		if LA.norm(x_new-x_goal)<ETA:
			path,visPath=tree.makePlan(x_new)
			break
			

		

		rate.sleep()



#_____________________________________________________________________________

if __name__ == '__main__':
    try:
        node()
    except rospy.ROSInterruptException:
        pass
 
 
 
 
