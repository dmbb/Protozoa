"""
This file deals with GUI automation to test several WebRTC apps

Screen resolution should be set to 1280x768

Chromium browser window should be set to maximize
"""
import os
os.environ['DISPLAY'] = ':0'

import pyautogui
import sys
import time


pyautogui.PAUSE = 0.25
pyautogui.FAILSAFE = True


def CoderpadAutomation(mode):
    #Coderpad requires different actions from the caller / callee
    #Caller must fill nickname, ask to start a call and confirm the request
    #Callee must fill nickname, accept ongoing call request, and join the call

    if(mode == "caller"):
        time.sleep(0.25)
        name_field = (515, 497)
        pyautogui.click(name_field[0], name_field[1]); pyautogui.typewrite('Protozoa1'); pyautogui.typewrite(['enter'])

        #Accept call even when caller, in the case the previous session is still active
        time.sleep(5)
        accept_call_button = (683, 519)
        pyautogui.click(accept_call_button[0], accept_call_button[1], button='left')

        time.sleep(5)
        confirm_call_button = (680, 718)
        pyautogui.click(confirm_call_button[0], confirm_call_button[1], button='left')
        #----------------

        #Accept
        time.sleep(5)
        start_call_button = (56, 741)
        pyautogui.click(start_call_button[0], start_call_button[1], button='left')

        time.sleep(5)
        confirm_call_button = (680, 718)
        pyautogui.click(confirm_call_button[0], confirm_call_button[1], button='left')
        
    
    elif(mode == "callee"):
        time.sleep(0.25)
        name_field = (515, 497)
        pyautogui.click(name_field[0], name_field[1]); pyautogui.typewrite('Protozoa2'); pyautogui.typewrite(['enter'])

        time.sleep(5)
        accept_call_button = (683, 519)
        pyautogui.click(accept_call_button[0], accept_call_button[1], button='left')

        time.sleep(5)
        join_call_button = (680, 716)
        pyautogui.click(join_call_button[0], join_call_button[1], button='left')


def ApprtcAutomation():
    #Appr.tc requires a single "Join Button" to be pressed to join a call

    time.sleep(0.25)
    join_button = (637, 712)
    pyautogui.click(join_button[0], join_button[1], button='left')


def automateChromium(webrtc_application, mode):
    #Print debug info
    #print "Window size: " + str(width) + "x" + str(height)
    print "Mouse position: " + str(pyautogui.position())

    if("coderpad" in webrtc_application):
        print "Coderpad Automation: Started"
        CoderpadAutomation(mode)
    elif("whereby" in webrtc_application):
        print "WhereBy Automation: Nothing to do."
    elif("appr.tc" in webrtc_application):
        print "Appr.tc Automation: Started"
        ApprtcAutomation()

def gracefullyCloseChromium():
    pyautogui.click(1265, 20, button='left')
    pyautogui.click(1265, 20, button='left')
    


if __name__ == "__main__":
    if(len(sys.argv) < 2):
        print "Input intended application"
        sys.exit(0)

    webrtc_application = sys.argv[1]
    automateChromium(webrtc_application, "callee")