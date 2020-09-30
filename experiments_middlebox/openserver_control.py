import sys, os
import subprocess as sub
import time, sched
import random
import threading
import requests
from flask import Flask
from flask import request
from termcolor import colored 

from chromium_factory import *

def PrintColored(string, color):
    print(colored(string, color))

#################################################################################
# Useful definitions


NETWORK_INTERFACE = "enp0s8"
#################################################################################

app = Flask(__name__)

@app.route('/startiPerf', methods=['POST'])
def startiPerf():
    PrintColored("Starting iPerf", 'red')
    args = "iperf3 -s"
    log = open('iperf_log', 'w')
    sub.Popen(args, shell = True, stdout=log, stderr=log)
    return "Starting iPerf"

@app.route('/killiPerf', methods=['POST'])
def killiPerf():
    logging, full_sample_path = request.data.split(",")
    directory = os.path.dirname(full_sample_path)

    PrintColored("Killing iPerf", 'red')
    os.system("pkill -SIGINT -f iperf3")

    if(logging == "log"):
        #Create folder for iperf logs
        if not os.path.exists(directory):
            os.makedirs(directory)
        os.system("mv iperf_log " + "\"" + full_sample_path + "\"" + "_iperf_log")
    return "Killing iPerf"


@app.route('/impairNetworkOperation', methods=['POST'])
def impairNetworkOperation():
    if(len(request.data) == 0):
        PrintColored("[P] Setting network conditions: None", 'red')
    else:
        network_condition = request.data
        PrintColored("[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " root " + network_condition, 'red')
        os.system("tc qdisc add dev " + NETWORK_INTERFACE + " root " + network_condition)
    return "Set network conditions for " + NETWORK_INTERFACE



@app.route('/resumeNetworkOperation', methods=['POST'])
def resumeNetworkOperation():
    PrintColored("Applying default network settings", 'red')
    os.system("tc qdisc del dev " + NETWORK_INTERFACE + " root")
    return "Set default network settings"

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0',port=5005)
