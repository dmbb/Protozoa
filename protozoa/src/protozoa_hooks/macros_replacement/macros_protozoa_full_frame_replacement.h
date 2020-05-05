#ifndef PROTOZOA_MACROS_H_
#define PROTOZOA_MACROS_H_


/*******************
	Encoding Flow
********************/

// webrtc/call/rtp_video_sender.cc
// Intercept encoded image just before packetization
#define PROTOZOA_SEND_VIDEO_HOOK            1

//Attempt to encode 1st part + 2nd part
#define ENCODE_AT_PROTOZOA_SEND_VIDEO_FULL_FRAME_REPLACEMENT_HOOK  1

//Read data from pipe
#define READ_AT_PROTOZOA_SEND_VIDEO_HOOK    1

/*******************
	Decoding Flow
********************/

// webrtc/video/video_receive_stream.cc
// Replace frame at receiver before decoding
#define PROTOZOA_REPLACE_FRAME_HOOK			1

// webrtc/video/video_receive_stream.cc
// Intercept frames at receiver just after a full frame is received
#define PROTOZOA_ON_COMPLETE_FRAME_HOOK     1

//Attempt to decode 1st part + 2nd part
#define PROTOZOA_ON_FULL_FRAME_DECODING_HOOK    1


/*******************
	Debug Flags
********************/
// webrtc/call/rtp_video_sender.cc
//Record legitimate frames for setting replacements
#define PROTOZOA_RECORD_FRAME_HOOK_SENDER			0

// webrtc/call/video_receive_stream.cc
//Record legitimate frames for setting replacements
#define PROTOZOA_RECORD_FRAME_HOOK_RECEIVER			0

// webrtc/call/rtp_video_sender.cc
//Record time wasted in sending frames out
#define MEASURE_RTP_VIDEO_SENDER_TIME_HOOK	0

// webrtc/call/video_receive_stream.cc
//Record time wasted in receiving and replacing frame data
#define MEASURE_VIDEO_RECEIVE_STREAM_TIME_HOOK	0

#define PROTOZOA_TRAFFIC_DEBUG_HOOK     	0

#define DEBUG_PRINT 						0

#endif //PROTOZOA_MACROS_H_
