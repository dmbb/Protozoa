import sys, os
import subprocess as sub
import time, sched
import random
import threading
import requests
from flask import Flask
from flask import request
from termcolor import colored 

def PrintColored(string, color):
    print(colored(string, color))

#################################################################################
# Useful definitions

SRC_IP = "192.168.4.100"
DST_IP = "192.168.5.101"
NETWORK_INTERFACE_1 = "enp0s8"
NETWORK_INTERFACE_2 = "enp0s9"

headless_env = dict(os.environ)
headless_env['DISPLAY'] = ':0'

#################################################################################

app = Flask(__name__)

def startCaptureTrafficSync(video_sample_name, capture_folder, capture_duration):
    if not os.path.exists(capture_folder + video_sample_name):
        os.makedirs(capture_folder + video_sample_name)

    PrintColored("Starting Traffic Capture - " + video_sample_name, 'red')
    outbound = 'tcpdump ip host ' + SRC_IP + ' -i ' + NETWORK_INTERFACE_2 + ' -G ' + str(capture_duration) + ' -W 1 -w ' + capture_folder + "\"" + video_sample_name + "\"" + "/" + "\"" + video_sample_name + "\"" + '_out.pcap'
    outbound_process = sub.Popen(outbound, shell=True)

    return outbound_process

@app.route('/captureTraffic', methods=['POST'])
def captureTraffic():
    timing, video_sample_name, capture_folder, capture_duration = request.data.split(",")
    s = sched.scheduler(time.time, time.sleep)
    print "Time now: " + str(time.time())
    print "Time sync: " + request.data
    args = (video_sample_name, capture_folder, capture_duration, )
    s.enterabs(float(timing), 0, startCaptureTrafficSync, args)
    s.run()
    return "Starting Traffic Capture - " + video_sample_name


@app.route('/impairNetworkOperation', methods=['POST'])
def impairNetworkOperation():
    network_condition = request.data.split(",")
    if(len(network_condition) > 0):
        os.system("tc qdisc add dev " + NETWORK_INTERFACE_1 + " root " + network_condition)
        print "[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE_1 + " root " + network_condition
        os.system("tc qdisc add dev " + NETWORK_INTERFACE_2 + " root " + network_condition)
        print "[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE_2 + " root " + network_condition
    else:
        os.system("tc qdisc del dev " + NETWORK_INTERFACE_1 + " root")
        os.system("tc qdisc del dev " + NETWORK_INTERFACE_2 + " root")
        print "[P] Setting network conditions: None"
    return "Impair Network Operation - " + network_condition



if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0',port=5005)
