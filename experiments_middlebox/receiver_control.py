import sys, os
import subprocess as sub
import time, sched
import random
import threading
import requests
from flask import Flask
from flask import request
from termcolor import colored 
from automate import automateChromium, gracefullyCloseChromium

from chromium_factory import *

def PrintColored(string, color):
    print(colored(string, color))

#################################################################################
# Useful definitions

protozoa_bin_folder_location = '/home/vagrant/protozoa/bin/'
analytics_folder_location = '/home/vagrant/protozoa/analytics/'

video_folder = "/home/vagrant/SharedFolder/VideoBaselines/"
protozoa_cap_folder = "/home/vagrant/SharedFolder/ProtozoaTraffic/"
regular_cap_folder = "/home/vagrant/SharedFolder/RegularTraffic/"
chromium_builds_folder = "/home/vagrant/chromium_builds/"

headless_env = dict(os.environ)
headless_env['DISPLAY'] = ':0'

NETWORK_INTERFACE = "enp0s8"
NETWORK_INTERFACE_FOR_OPEN_SERVER = "enp0s9"
#################################################################################

app = Flask(__name__)

def startFFMPEGAtClock(video_sample):
    #If no argument is passed in sender control, use default video
    if(len(video_sample) == 0):
        video_sample = "/home/vagrant/SharedFolder/<some-video>.mp4"
    else: 
        #Else, mirror video content at the sender
        video_sample = video_sample

    PrintColored("Starting FFMPEG stream - " + video_sample, 'red')

    args = "ffmpeg -nostats -loglevel quiet -re -i " + video_sample + " -r 30 \
            -vf scale=1280:720 -vcodec rawvideo -pix_fmt yuv420p -threads 0 -f v4l2 /dev/video0"
    sub.Popen(args, shell = True, stdin = open(os.devnull))

@app.route('/startFFMPEGStream', methods=['POST'])
def startFFMPEGStream():
    if(len(request.data) == 0):
        video_sample = "/home/vagrant/SharedFolder/<some-video>.mp4"
    else:
        video_sample = request.data

    args = "ffmpeg -nostats -loglevel quiet -re -i " + video_sample + " -r 30 \
            -vf scale=1280:720 -vcodec rawvideo -pix_fmt yuv420p -threads 0 -f v4l2 /dev/video0"
    sub.Popen(args, shell = True, stdin = open(os.devnull))


@app.route('/startFFMPEGSync', methods=['POST'])
def startFFMPEGSync():
    time_sync, video_sample = request.data.split(",|,")
    s = sched.scheduler(time.time, time.sleep)
    print "Time now: " + str(time.time())
    print "Time sync: " + time_sync
    args = (video_sample, )
    s.enterabs(float(time_sync), 0, startFFMPEGAtClock, args)
    s.run()
    return "Starting FFMPEG stream"

@app.route('/killFFMPEG', methods=['POST'])
def killFFMPEG():
    PrintColored("Killing FFMPEG stream", 'red')
    os.system("pkill -9 -f ffmpeg")
    return "Killing FFMPEG stream"


def startChromiumSync(chromium_build, webrtc_application):
    PrintColored("Starting Chromium - " + chromium_build, 'red')
    args = chromium_builds_folder + chromium_build + "/chrome --disable-session-crashed-bubbles --disable-infobars --no-sandbox " + webrtc_application
    devnull = open(os.devnull,'wb')
    sub.Popen(args, env=headless_env, shell = True, stdout=devnull, stderr=devnull)


@app.route('/startChromium', methods=['POST'])
def startChromium():
    timing, chromium_build, webrtc_application = request.data.split(",")
    s = sched.scheduler(time.time, time.sleep)
    print "Time now: " + str(time.time())
    print "Time sync: " + request.data
    args = (chromium_build, webrtc_application, )
    s.enterabs(float(timing), 0, startChromiumSync, args)
    s.run()
    return "Starting Chromium - " + chromium_build

def killProxy():
    os.system("pkill -9 -f \"ssh -i\"")

@app.route('/killChromium', methods=['POST'])
def killChromium():
    PrintColored("Killing Chromium", 'red')
    os.system("ip netns exec PROTOZOA_ENV pkill -9 -f chrome")

    killProxy()
    return "Killing Chromium"

@app.route('/automateApp', methods=['POST'])
def automateApp():
    PrintColored("Automating Chromium", 'red')
    webrtc_application = request.data
    automateChromium(webrtc_application, "callee")
    return "Automated Chromium"

@app.route('/gracefullyCloseChromium', methods=['POST'])
def gracefullyCloseChromium():
    PrintColored("Gracefully closing Chromium", 'red')
    gracefullyCloseChromium()
    return "Gracefully closing Chromium"

@app.route('/startProtozoa', methods=['POST'])
def startProtozoa():
    PrintColored("Starting Protozoa", 'red')
    args = protozoa_bin_folder_location + "protozoa -m server"
    devnull = open(os.devnull,'wb')
    sub.Popen(args, shell = True, cwd = protozoa_bin_folder_location, stdout=devnull, stderr=devnull)
    return "Starting Protozoa"

@app.route('/killProtozoa', methods=['POST'])
def killProtozoa():
    PrintColored("Killing Protozoa", 'red')
    os.system("pkill -9 -f protozoa")
    return "Killing Protozoa"

@app.route('/startiPerf', methods=['POST'])
def startiPerf():
    PrintColored("Starting iPerf", 'red')
    args = "iperf3 -s"
    devnull = open(os.devnull,'wb')
    sub.Popen(args, shell = True, stdout=devnull, stderr=devnull)
    return "Starting iPerf"

@app.route('/killiPerf', methods=['POST'])
def killiPerf():
    PrintColored("Killing iPerf", 'red')
    os.system("pkill -SIGINT -f iperf3")
    return "Killing iPerf"


@app.route('/compileChromiumVersions', methods=['POST'])
def compileChromiumVersions():
    CompileChromiumVersions(chromium_builds_folder)
    return "Compiled Chromium Versions"

@app.route('/impairNetworkOperation', methods=['POST'])
def impairNetworkOperation():
    if(len(request.data) == 0):
        PrintColored("[P] Setting network conditions: None", 'red')
    else:
        network_condition = request.data
        PrintColored("[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " root " + network_condition, 'red')
        os.system("tc qdisc add dev " + NETWORK_INTERFACE + " root " + network_condition)
    return "Set network conditions for " + NETWORK_INTERFACE


#Performs multiple impairments on interface that communicates with VM1
@app.route('/impairNetworkOperationWithOpenServer', methods=['POST'])
def impairNetworkOperationWithOpenServer():
    if(len(request.data) == 0):
        PrintColored("[P] Setting network conditions: None", 'red')
    else:
        network_condition = request.data
        if(len(network_condition.split("|")) == 1):
            PrintColored("[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " root " + network_condition, 'red')
            os.system("tc qdisc add dev " + NETWORK_INTERFACE + " root " + network_condition)
        elif(len(network_condition.split("|")) == 3):
            network_condition = network_condition.split("|")
            
            #Combine netem with htb
            os.system("tc qdisc add dev " + NETWORK_INTERFACE + " root handle 1: " + network_condition[0])
            print "[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " root handle 1: " + network_condition[0]

            os.system("tc class add dev " + NETWORK_INTERFACE + " parent 1:1 classid 1:12 " + network_condition[1])
            print "[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " parent 1:1 classid 1:12 " + network_condition[1]

            os.system("tc qdisc add dev " + NETWORK_INTERFACE + " parent 1:12 " + network_condition[2])
            print "[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " parent 1:12 " + network_condition[2]
    return "Set network conditions for " + NETWORK_INTERFACE


#Changes interface that connects to OpenServer
@app.route('/impairNetworkOperationForOpenServer', methods=['POST'])
def impairNetworkOperationForOpenServer():
    if(len(request.data) == 0):
        PrintColored("[P] Setting network conditions: None", 'red')
    else:
        network_condition = request.data
        PrintColored("[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE_FOR_OPEN_SERVER + " root " + network_condition, 'red')
        os.system("tc qdisc add dev " + NETWORK_INTERFACE_FOR_OPEN_SERVER + " root " + network_condition)
    return "Set network conditions for " + NETWORK_INTERFACE_FOR_OPEN_SERVER




@app.route('/resumeNetworkOperation', methods=['POST'])
def resumeNetworkOperation():
    PrintColored("Applying default network settings", 'red')
    os.system("tc qdisc del dev " + NETWORK_INTERFACE + " root")
    os.system("tc qdisc del dev " + NETWORK_INTERFACE_FOR_OPEN_SERVER + " root")
    return "Set default network settings"

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0',port=5005)
