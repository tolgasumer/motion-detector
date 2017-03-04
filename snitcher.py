#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import datetime
import imutils
import time
import cv2
import os
import json
import dropbox



imagenames = []
frame_1 = None
frame_2 = None
motion_num = 0
min_area = 1000
i = 0

clicked = False

# Reading user dropbox key, secret and image save path from JSON file
with open("conf.json", "r") as jsonFile:
    conf = json.load(jsonFile)
    app_key = conf['dropbox_key']
    app_secret = conf['dropbox_secret']
    path = conf['images_path']
    jsonFile.close()
    
    
# Asking the user if he/she wants to enable Dropbox integration
useDropbox = raw_input('Use Dropbox (Y/N)')

if useDropbox == 'Y':
	flow = dropbox.client.DropboxOAuth2FlowNoRedirect(app_key, app_secret)

	# Have the user sign in and authorize this token
	authorize_url = flow.start()
	print '1. Go to: ' + authorize_url
	print '2. Click "Allow" (you might have to log in first)'
	print '3. Copy the authorization code.'
	code = raw_input("Enter the authorization code here: ").strip()

	# This will fail if the user enters an invalid authorization code
	access_token, user_id = flow.finish(code)

	client = dropbox.client.DropboxClient(access_token)
	print 'linked account: ', client.account_info()
	
elif useDropbox == 'N':
	print('Images will be saved under the ' + path + ' directory in the folder that Snitcher runs')
	print('Edit the "images_path" section in conf.json file to change it')


def onMouse(event, x, y, flags, param):
	global clicked
	if event == cv2.cv.CV_EVENT_LBUTTONUP:
		clicked = True

# Function for writing the images locally to directory /images
def writeImage(frame, name):
	try:
		if not os.path.exists(path):
			os.makedirs(path)
	except:
		print "Failed to create directory in %s" % path
		exit()
	name = path + '/' + name 
	
	cv2.imwrite(name, frame)


# Function for uploading the images to Dropbox, checking the imagenames array for accurate timestamping	
def uploadImage(filename):
	f = open(path + filename, 'rb')
	client.put_file('/' + filename, f)
	print 'uploaded: '+filename
	global i
	i += 1

# Initializing the camera object and naming the window
camera = cv2.VideoCapture(0)
cv2.namedWindow('SNITCHER')
cv2.setMouseCallback('SNITCHER', onMouse)


# Starting the main loop
while True:
	# grab the current frame and initialize the occupied/unoccupied
	# text

	(grabbed, frame) = camera.read()

	if not grabbed:
		time.sleep(0.25)
		continue


	frame_2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	frame_2 = cv2.GaussianBlur(frame_2, (21, 21), 0)

	if frame_1 is None:
		frame_1 = frame_2
		continue

	frameDelta = cv2.absdiff(frame_1, frame_2)
	thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

	thresh = cv2.dilate(thresh, None, iterations = 2)
	(cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, 
		cv2.CHAIN_APPROX_SIMPLE)

	motion_num = 0

	for c in cnts:
		#if the contour is too small, ignore it
		if cv2.contourArea(c) < min_area:
			continue
		motion_num += 1

	time_now = datetime.datetime.now()
# Display the current time on the bottom left corner of the window
	cv2.putText(frame, time_now.strftime("%Y-%m-%d %H:%M:%S.%f"),
		(10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

	cv2.imshow("SNITCHER", frame)
	
# If motion occurs, call the writeImage function with timestamps as parameters
	if motion_num > 0:
		name = time_now.strftime("%H:%M:%S.%f.png")
		# Store the image names in the array 'imagenames' to use those names later for uploading
		imagenames.append(name)
		print('Motion detected - Image saved: '+name)
		writeImage(frame, name)
		

		
		

	frame_1 = frame_2.copy()
	time.sleep(0.2)
	
	# Start uploading when the motion ends (motion detecting and uploading at the same time causes major performance issues)
	
	if useDropbox == 'Y' and motion_num == 0 and len(imagenames)!=0 and i<len(imagenames):
		uploadImage(imagenames[i])
	
	

	
	

	if cv2.waitKey(1) != -1 or clicked:
		break

camera.release()
cv2.destroyAllWindows()
