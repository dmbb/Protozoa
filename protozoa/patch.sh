#!/bin/bash

##############################################################################
# Patch files within Chromium's WebRTC stack
# This script will be executed from Protozoa/machine_setup/compile_chromium.py
##############################################################################

CHROMIUM_WEBRTC_DIR=$1
MACRO_DIR=$2
MACRO_FILE=$3
HOOK_DIR=$4
HOOK_FILE=$5

#Copy protozoa hooks and code to Chromium's WebRTC directory
rm -r $CHROMIUM_WEBRTC_DIR/protozoa_hooks
mkdir $CHROMIUM_WEBRTC_DIR/protozoa_hooks

cp src/protozoa_hooks/BUILD.gn $CHROMIUM_WEBRTC_DIR/protozoa_hooks/BUILD.gn
cp src/protozoa_hooks/$HOOK_DIR/protozoa_hooks.h $CHROMIUM_WEBRTC_DIR/protozoa_hooks/protozoa_hooks.h
cp src/protozoa_hooks/protozoa_recorded_frames.h $CHROMIUM_WEBRTC_DIR/protozoa_hooks/protozoa_recorded_frames.h

cp src/protozoa_hooks/$HOOK_DIR/$HOOK_FILE $CHROMIUM_WEBRTC_DIR/protozoa_hooks/protozoa_hooks.cpp
cp src/protozoa_hooks/$MACRO_DIR/$MACRO_FILE $CHROMIUM_WEBRTC_DIR/protozoa_hooks/macros.h

#Include Protozoa in Chromium's linking step
cp webrtc_patches/media/BUILD.gn 											$CHROMIUM_WEBRTC_DIR/media/BUILD.gn

#Overwrite Webrtc code to apply our hooks
cp webrtc_patches/call/rtp_video_sender.cc 							        $CHROMIUM_WEBRTC_DIR/call/rtp_video_sender.cc
cp webrtc_patches/video/video_receive_stream.cc 						    $CHROMIUM_WEBRTC_DIR/video/video_receive_stream.cc
cp webrtc_patches/modules/video_coding/encoded_frame.h 						$CHROMIUM_WEBRTC_DIR/modules/video_coding/encoded_frame.h
