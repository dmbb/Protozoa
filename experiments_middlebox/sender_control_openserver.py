import sys, os
import subprocess as sub
import time, sched
import random
import threading
import requests
from termcolor import colored 
from automate import automateChromium, gracefullyCloseChromium


def PrintColored(string, color):
    print(colored(string, color))

#################################################################################
# Useful definitions


protozoa_bin_folder_location = '/home/vagrant/protozoa/bin/'
analytics_folder_location = '/home/vagrant/protozoa/analytics/'

protozoa_cap_folder = "/home/vagrant/SharedFolder/ProtozoaTraffic/"
protozoa_multisample_cap_folder = "/home/vagrant/ProtozoaMultiSampleTraffic/"
regular_cap_folder = "/home/vagrant/SharedFolder/RegularTraffic/"
regular_multisample_cap_folder = "/home/vagrant/RegularMultiSampleTraffic/"
video_folder = "/home/vagrant/SharedFolder/VideoBaselines/"

chromium_builds_folder = "/home/vagrant/chromium_builds/"

SRC_IP = "192.168.4.100"
DST_IP = "192.168.5.101"
MIDDLEBOX_IP = "192.168.4.102"
OPENSERVER_IP = "192.168.6.101"
NETWORK_INTERFACE = "enp0s8"


capture_duration = 35
iperf_duration = 25
sync_early = 2
sync_late = 4

#############################################################################
# Choose WebRTC application to test

#WEBRTC_APPLICATION = "https://coderpad.io/<chatroom-id>"
WEBRTC_APPLICATION = "https://whereby.com/<chatroom-id>"
#WEBRTC_APPLICATION = "https://appr.tc/r/<chatroom-id>"
#APPRTC_PARAMS = "?vsc=VP8&vrc=VP8" #Choose VP8 codec for AppRTC

#############################################################################

headless_env = dict(os.environ)
headless_env['DISPLAY'] = ':0'


network_conditions = [
    
    #No changes to the network
    [[None], [None], "regular.regular"],

    #2ms, 5ms, 10ms
    #Variation of RTT between VM1 / VM3
    [["netem delay 7ms"],  ["netem delay 7ms 1ms distribution normal"],    "delay_15.delay_15"],
    [["netem delay 25ms"], ["netem delay 7ms 1ms distribution normal"],   "delay_50.delay_15"],
    [["netem delay 50ms"], ["netem delay 7ms 1ms distribution normal"],  "delay_100.delay_15"],

    
    #Set baseline RTT between VM1 / VM3, vary bandwidth conditions (TC)
    [["htb default 12", "htb rate 1500kbit ceil 1500kbit", "netem delay 25ms"],  ["netem delay 7ms 1ms distribution normal"],  "delay_50-bw_1500.delay_15"],
    [["htb default 12",   "htb rate 750kbit ceil 750kbit", "netem delay 25ms"],  ["netem delay 7ms 1ms distribution normal"],  "delay_50-bw_750.delay_15"],
    [["htb default 12",   "htb rate 250kbit ceil 250kbit", "netem delay 25ms"],  ["netem delay 7ms 1ms distribution normal"],  "delay_50-bw_250.delay_15"],
    
    #Set baseline RTT between VM1 / VM3, vary packet loss conditions
    [["netem delay 25ms loss 2%"],  ["netem delay 7ms 1ms distribution normal"],  "delay_50-loss_2.delay_15"],
    [["netem delay 25ms loss 5%"],  ["netem delay 7ms 1ms distribution normal"],  "delay_50-loss_5.delay_15"],
    [["netem delay 25ms loss 10%"], ["netem delay 7ms 1ms distribution normal"],  "delay_50-loss_10.delay_15"],

    #Openserver RTT variation for the baseline case
    [["netem delay 25ms 2ms distribution normal"], ["netem delay 25ms 2ms distribution normal"],   "delay_50.delay_50"],
    [["netem delay 25ms 2ms distribution normal"], ["netem delay 50ms 5ms distribution normal"],   "delay_50.delay_100"],

]

#################################################################################

def RESTCall(method, args=""):
    url='http://' + DST_IP + ':5005/' + method
    response = ''
    try:
        response = requests.post(url, data=args)
    except requests.exceptions.RequestException as e:
        print e

def RESTCallMiddlebox(method, args=""):
    url='http://' + MIDDLEBOX_IP + ':5005/' + method
    response = ''
    try:
        response = requests.post(url, data=args)
    except requests.exceptions.RequestException as e:
        print e

def RESTCallOpenServer(method, args=""):
    url='http://' + OPENSERVER_IP + ':5005/' + method
    response = ''
    try:
        response = requests.post(url, data=args)
    except requests.exceptions.RequestException as e:
        print e

def CaptureTraffic(sample_name, capture_folder):
    cmd = 'tcpdump ip host ' + SRC_IP + ' -i ' + NETWORK_INTERFACE + ' -G ' + str(capture_duration) + ' -W 1 -w ' + capture_folder + "\"" + sample_name + "\"" + '.pcap'
    p = sub.Popen(cmd, shell=True)
    return p


def StartFFMPEGStream(chat_video):
    args = "ffmpeg -nostats -loglevel quiet -re -i " + "\"" + chat_video + "\"" + " -r 30 \
            -vf scale=1280:720 -vcodec rawvideo -pix_fmt yuv420p -threads 0 -f v4l2 /dev/video0"
    sub.Popen(args, shell = True, stdin = open(os.devnull))


def KillFFMPEGStream():
    os.system("pkill -9 -f ffmpeg")


def StartChromium(create_log, chromium_build, webrtc_app):
    args = chromium_builds_folder + chromium_build + "/chrome --disable-session-crashed-bubbles --disable-infobars --no-sandbox " + webrtc_app
    if(create_log):
        log = open('chromium_log', 'w')
        sub.Popen(args, env = headless_env, shell = True, stdout=log, stderr=log)
    else:
        devnull = open(os.devnull,'wb')
        sub.Popen(args, env = headless_env, shell = True, stdout=devnull, stderr=devnull)


def KillChromium(sample, log_created):
    os.system("pkill -9 -f chrome")
    if(log_created):
        os.system("mv chromium_log " + "\"" + sample + "\"" + "_chromium_log")

def StartProtozoa():
    log = open('protozoa_log', 'w')
    args = protozoa_bin_folder_location + "protozoa -m client"
    sub.Popen(args, shell = True, cwd = protozoa_bin_folder_location, stdout=log, stderr=log)

def KillProtozoa(sample, log_created):
    os.system("pkill -9 -f protozoa")
    if(log_created):
        os.system("mv protozoa_log " + "\"" + sample + "\"" + "_protozoa_log")

def ProtozoaWget():
    args = "ip netns exec PROTOZOA_ENV wget " + DST_IP + "/wget_file"
    sub.Popen(args, shell = True)

def KillWget(sample):
    os.system("pkill -9 -f wget")
    os.system("mv wget_file " + "\"" + sample + "\"" + "_wget_file")

def ProtozoaiPerf(create_log):
    args = "ip netns exec PROTOZOA_ENV proxychains4 -f proxychains.conf iperf3 -c " + OPENSERVER_IP + " -t " + str(iperf_duration) + " -f K -i 5"
    if(create_log):
        log = open('iperf_log', 'w')
        sub.Popen(args, shell = True, stdout=log, stderr=log)
    else:
        devnull = open(os.devnull,'wb')
        sub.Popen(args, shell = True, stdout=devnull, stderr=devnull)

def SaveProtozoaiPerfResult(sample, log_created):
    os.system("pkill -SIGINT -f iperf3")
    if(log_created):
        os.system("mv iperf_log " + "\"" + sample + "\"" + "_iperf_log")

def ImpairNetworkOperation(network_condition):
    if(network_condition[0] is not None):
        if(len(network_condition) == 1):
            os.system("tc qdisc add dev " + NETWORK_INTERFACE + " root " + network_condition[0])
            print "[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " root " + network_condition[0]
        elif(len(network_condition) == 3):
            #Combine netem with htb
            os.system("tc qdisc add dev " + NETWORK_INTERFACE + " root handle 1: " + network_condition[0])
            print "[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " root handle 1: " + network_condition[0]

            os.system("tc class add dev " + NETWORK_INTERFACE + " parent 1:1 classid 1:12 " + network_condition[1])
            print "[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " parent 1:1 classid 1:12 " + network_condition[1]

            os.system("tc qdisc add dev " + NETWORK_INTERFACE + " parent 1:12 " + network_condition[2])
            print "[P] Setting network conditions: tc qdisc add dev " + NETWORK_INTERFACE + " parent 1:12 " + network_condition[2]
    else:
        print "[P] Setting network conditions: None"

def ResumeNetworkOperation():
    os.system("tc qdisc del dev " + NETWORK_INTERFACE + " root")



def SampleRegularExact(sample_index, config, baseline, network_condition):
    chromium_build = "regular_build"
    regular_cap_folder = config

    random.seed(a=1)
    sample_list = os.listdir(video_folder + baseline + "/")
    sample_list.sort()
    random.shuffle(sample_list)

    #Create folder for regular traffic
    if not os.path.exists(regular_cap_folder):
        os.makedirs(regular_cap_folder)

    if not os.path.exists(regular_cap_folder + baseline):
        os.makedirs(regular_cap_folder + baseline)

    if not os.path.exists(regular_cap_folder + baseline + "/" + network_condition[2]):
        os.makedirs(regular_cap_folder + baseline + "/" + network_condition[2])

    chat_sample = sample_list[sample_index]

        
    if(chat_sample[:-4].replace(" ", "") + "_" + str(i) + "_chromium_log" not in os.listdir(regular_cap_folder + baseline + "/" + network_condition[2])):
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        print "Network conditions: " + network_condition[2]
        ImpairNetworkOperation(network_condition[0])
        
        if(len(network_condition[0]) == 1):
            RESTCall("impairNetworkOperationWithOpenServer", network_condition[0][0])
        elif(len(network_condition[0]) == 3):
            RESTCall("impairNetworkOperationWithOpenServer", network_condition[0][0] + "|" + network_condition[0][1] + "|" + network_condition[0][2])

        RESTCall("impairNetworkOperationForOpenServer", network_condition[1][0])

        RESTCallOpenServer("impairNetworkOperation", network_condition[1][0])

        
        print "Chromium build - " + chromium_build
        #Start Remote iPerf server
        print "[P] Starting Remote iPerf server"
        RESTCallOpenServer("startiPerf") 

        #Start FFMPEG in sync
        s = sched.scheduler(time.time, time.sleep)
        now = time.time()
        start_remote_ffmpeg = now + sync_early
        start_local_ffmpeg = now + sync_late
        
        print "[P] Starting remote FFMPEG stream at: " + str(start_remote_ffmpeg)
        RESTCall("startFFMPEGSync", str(start_remote_ffmpeg) + ",|," + video_folder + baseline + "/" + chat_sample)
        
        print "[P] Wait to start local FFMPEG stream at: " + str(start_local_ffmpeg)
        args = (video_folder + baseline + "/" + chat_sample,)
        s.enterabs(start_local_ffmpeg, 0, StartFFMPEGStream, args)                  
        s.run()
        print "[P] Starting local FFMPEG stream: " + baseline + "/" + chat_sample + " - index " + str(i)  
        
        #Start Chromium in sync
        now = time.time()
        start_remote_chromium = now + sync_early
        start_local_chromium = now + sync_late
        
        webrtc_app = WEBRTC_APPLICATION
        if("appr.tc" in WEBRTC_APPLICATION):
            label = network_condition[2].replace(".","-")
            webrtc_app = WEBRTC_APPLICATION + "_reg_" + label + "_" + str(i) + APPRTC_PARAMS

        print "[P] Starting Remote Chromium Browser at: " + str(start_remote_chromium)
        print "[P] Starting WebRTC Application: " + webrtc_app
        RESTCall("startChromium", str(start_remote_chromium) + "," + chromium_build + "," + webrtc_app)
        
        print "[P] Wait to start local Chromium Browser at: " + str(start_local_chromium)
        args = (True, chromium_build, webrtc_app)
        s.enterabs(start_local_chromium, 0, StartChromium, args)
        s.run()
        print "[P] Starting local Chromium Browser"
        
        if("appr.tc" in WEBRTC_APPLICATION):
            time.sleep(20)

            print "[P] Performing local automation task"
            automateChromium(webrtc_app, "caller")

            time.sleep(5)

            print "[P] Performing remote automation task"
            RESTCall("automateApp", webrtc_app)

            time.sleep(20)
        elif("coderpad" in WEBRTC_APPLICATION):
            time.sleep(20)

            print "[P] Performing local automation task"
            automateChromium(webrtc_app, "caller")

            time.sleep(5)

            print "[P] Performing remote automation task"
            RESTCall("automateApp", webrtc_app)

            time.sleep(20)
        elif("whereby" in WEBRTC_APPLICATION):
            time.sleep(20) #Ten seconds were apparently not enough for starting up Chromium

            print "[P] Performing local automation task"
            automateChromium(webrtc_app, "caller")

            print "[P] Performing remote automation task"
            RESTCall("automateApp", webrtc_app)
        
        #Start Traffic Capture in sync
        now = time.time()
        start_remote_traffic_capture = now + sync_early
        
        print "[P] Starting Remote Traffic Capture at: " + str(start_remote_traffic_capture)
        print "[P] Capturing " + baseline + "/" + network_condition[2] + "/" + chat_sample[:-4] + "_" + str(i) + ".pcap"
        RESTCallMiddlebox("captureTraffic", str(start_remote_traffic_capture) + "," + chat_sample[:-4].replace(" ", "") + "_" + str(i) + "," + regular_cap_folder + baseline + "/" + network_condition[2] + "/" + "," + str(capture_duration))


        #Wait for tcpdump to finish
        print "[P] Waiting for traffic capture to finish..."
        time.sleep(capture_duration + sync_early)

        # Cleanup
        print "[P] Killing FFMPEG stream"
        KillFFMPEGStream()
        print "[P] Killing remote FFMPEG stream"
        RESTCall("killFFMPEG")

        print "[P] Killing Chromium"
        KillChromium(regular_cap_folder + baseline + "/" + network_condition[2] + "/" + chat_sample[:-4].replace(" ", "") + "_" + str(i), True)

        print "[P] Killing Remote Chromium Browser"
        RESTCall("killChromium")

        print "[P] Killing Remote iPerf server"
        RESTCallOpenServer("killiPerf", "no_log,no_log")
        time.sleep(2)
    else:
        print "[P] Already sampled " + baseline + "/" + chat_sample

    ResumeNetworkOperation()
    RESTCall("resumeNetworkOperation")
    RESTCallOpenServer("resumeNetworkOperation")


def SampleProtozoaExact(sample_index, config, baseline, network_condition, chromium_build):

    protozoa_cap_folder = config

    random.seed(a=1)
    sample_list = os.listdir(video_folder + baseline)
    sample_list.sort()
    random.shuffle(sample_list)

    #Create folder for protozoa traffic
    if not os.path.exists(protozoa_cap_folder):
        os.makedirs(protozoa_cap_folder)

    if not os.path.exists(protozoa_cap_folder + baseline):
        os.makedirs(protozoa_cap_folder + baseline)

    if not os.path.exists(protozoa_cap_folder + baseline + "/" + network_condition[2]):
        os.makedirs(protozoa_cap_folder + baseline + "/" + network_condition[2])

    chat_sample = sample_list[sample_index]

    #Check sample existence by checking whether chromium log is saved
    if(chat_sample[:-4].replace(" ", "") + "_" + str(i) + "_chromium_log" not in os.listdir(protozoa_cap_folder + baseline + "/" + network_condition[2])):
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"

        ImpairNetworkOperation(network_condition[0])
        
        if(len(network_condition[0]) == 1):
            RESTCall("impairNetworkOperationWithOpenServer", network_condition[0][0])
        elif(len(network_condition[0]) == 3):
            RESTCall("impairNetworkOperationWithOpenServer", network_condition[0][0] + "|" + network_condition[0][1] + "|" + network_condition[0][2])

        RESTCall("impairNetworkOperationForOpenServer", network_condition[1][0])

        RESTCallOpenServer("impairNetworkOperation", network_condition[1][0])

        print "Chromium build - " + chromium_build
        #Start Remote iPerf server
        print "[P] Starting Remote iPerf server"
        RESTCallOpenServer("startiPerf")  

        #Start Protozoa
        print "[P] Starting Remote Protozoa"
        RESTCall("startProtozoa")
        print "[P] Starting Protozoa"
        StartProtozoa()

        #Start FFMPEG in sync
        s = sched.scheduler(time.time, time.sleep)
        now = time.time()
        start_remote_ffmpeg = now + sync_early
        start_local_ffmpeg = now + sync_late
        
        print "[P] Starting remote FFMPEG stream at: " + str(start_remote_ffmpeg)
        RESTCall("startFFMPEGSync", str(start_remote_ffmpeg) + ",|," + video_folder + baseline + "/" + chat_sample)
        
        print "[P] Wait to start local FFMPEG stream at: " + str(start_local_ffmpeg)
        args = (video_folder + baseline + "/" + chat_sample,)
        s.enterabs(start_local_ffmpeg, 0, StartFFMPEGStream, args)                  
        s.run()
        print "[P] Starting local FFMPEG stream: " + baseline + "/" + chat_sample + " - index " + str(i)  
        
        #Start Chromium in sync
        now = time.time()
        start_remote_chromium = now + sync_early
        start_local_chromium = now + sync_late
        

        webrtc_app = WEBRTC_APPLICATION
        if("appr.tc" in WEBRTC_APPLICATION):
            label = network_condition[2].replace(".","-")
            webrtc_app = WEBRTC_APPLICATION + "_prot_" + label + "_" + str(i) + APPRTC_PARAMS

        print "[P] Starting Remote Chromium Browser at: " + str(start_remote_chromium)
        RESTCall("startChromium", str(start_remote_chromium) + "," + chromium_build + "," + webrtc_app)
        
        print "[P] Wait to start local Chromium Browser at: " + str(start_local_chromium)
        args = (True, chromium_build, webrtc_app)
        s.enterabs(start_local_chromium, 0, StartChromium, args)
        s.run()
        print "[P] Starting local Chromium Browser"
        
        if("appr.tc" in WEBRTC_APPLICATION):
            time.sleep(20)

            print "[P] Performing local automation task"
            automateChromium(webrtc_app, "caller")

            time.sleep(5)

            print "[P] Performing remote automation task"
            RESTCall("automateApp", webrtc_app)

            time.sleep(20)
        elif("coderpad" in WEBRTC_APPLICATION):
            time.sleep(20)

            print "[P] Performing local automation task"
            automateChromium(webrtc_app, "caller")

            time.sleep(5)

            print "[P] Performing remote automation task"
            RESTCall("automateApp", webrtc_app)

            time.sleep(20)
        elif("whereby" in WEBRTC_APPLICATION):
            time.sleep(20) #Ten seconds were apparently not enough for starting up Chromium

            print "[P] Performing local automation task"
            automateChromium(webrtc_app, "caller")

            print "[P] Performing remote automation task"
            RESTCall("automateApp", webrtc_app)

        #Start Traffic Capture in sync
        now = time.time()
        start_remote_traffic_capture = now + sync_early
        
        print "[P] Starting Remote Traffic Capture at: " + str(start_remote_traffic_capture)
        print "[P] Capturing " + baseline + "/" + network_condition[2] + "/" + chat_sample[:-4] + "_" + str(i) + ".pcap"
        RESTCallMiddlebox("captureTraffic", str(start_remote_traffic_capture) + "," + chat_sample[:-4].replace(" ", "") + "_" + str(i) + "," + protozoa_cap_folder + baseline + "/" + network_condition[2] + "/" + "," + str(capture_duration))

        
        #Start Protozoa data transmission after tcpdump start
        print "[P] Starting Protozoa data transmission"
        ProtozoaiPerf(False)
        
        #Wait for tcpdump to finish
        print "[P] Waiting for traffic capture to finish..."
        time.sleep(capture_duration + sync_early)

        # Cleanup
        print "[P] Killing FFMPEG stream"
        KillFFMPEGStream()
        print "[P] Killing remote FFMPEG stream"
        RESTCall("killFFMPEG")

        print "[P] Killing Chromium"
        KillChromium(protozoa_cap_folder + baseline + "/" + network_condition[2] + "/" + chat_sample[:-4].replace(" ", "") + "_" + str(i), True)

        print "[P] Killing Remote Chromium Browser"
        RESTCall("killChromium")

        print "[P] NOT saving local results for Protozoa transmission - job on remote"
        SaveProtozoaiPerfResult(protozoa_cap_folder + baseline + "/" + network_condition[2] + "/" + chat_sample[:-4].replace(" ", "") + "_" + str(i), False)

        print "[P] Killing Protozoa"
        KillProtozoa(protozoa_cap_folder + baseline + "/" + network_condition[2] + "/" + chat_sample[:-4].replace(" ", "") + "_" + str(i), True)
        print "[P] Killing Remote Protozoa instance"
        RESTCall("killProtozoa")
        print "[P] Killing Remote iPerf server and saving result"
        RESTCallOpenServer("killiPerf", "log," + protozoa_cap_folder + baseline + "/" + network_condition[2] + "/" + chat_sample[:-4].replace(" ", "") + "_" + str(i))
        time.sleep(2)
    else:
        print "[P] Already sampled " + baseline + "/" + chat_sample.replace(" ", "")

    ResumeNetworkOperation()
    RESTCall("resumeNetworkOperation")
    RESTCallOpenServer("resumeNetworkOperation")


if __name__ == "__main__":

    #Sample Regular and Protozoa flows in an interleaved fashion

    baselines = [
    "Chat",
    #"LiveCoding",
    #"Gaming",
    #"Sports"
    ]

    chromium_builds = ["protozoaReplacementFullFrame_build"]

    ResumeNetworkOperation()
    RESTCall("resumeNetworkOperation")
    RESTCallOpenServer("resumeNetworkOperation")

    for network_condition in network_conditions:
        for baseline in baselines:
            for i in range(0,250):
                SampleRegularExact(0 + i, "/home/vagrant/SharedFolder/ProtozoaCaps/RegularTraffic_1/", baseline, network_condition)
                SampleProtozoaExact(250 + i, "/home/vagrant/SharedFolder/ProtozoaCaps/ProtozoaTraffic/", baseline, network_condition, chromium_builds[0])


