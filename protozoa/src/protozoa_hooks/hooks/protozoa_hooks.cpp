#include "protozoa_hooks.h"
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <mutex>
#include <queue>
#include <chrono>
#include <unistd.h>
#include <fcntl.h>
#include <iostream>

std::string protozoa_decoder_pipe = "/tmp/protozoa_decoder_pipe";
int decoder_fd = open(protozoa_decoder_pipe.c_str(), O_WRONLY | O_NONBLOCK);

std::string protozoa_encoder_pipe = "/tmp/protozoa_encoder_pipe";
int encoder_fd = open(protozoa_encoder_pipe.c_str(), O_RDONLY | O_NONBLOCK);

//Queue for holding outbound IP packets
std::deque<std::vector<uint8_t>> staging_queue;

//Queue for holding outbound IP packet fragments
std::deque<std::vector<uint8_t>> staging_queue_fragments;


//Debug flag
int debug = 0;

//Limit of queue size following the Size = RTT * BW rule of thumb
unsigned long queue_limit = 24;

//Length of Protozoa message header
int HEADER_LEN = 8;

//// Set minimum amount of bytes that a frame must have for us to embed data
const int MIN_PAYLOAD_SIZE = 20;



void checkPipeError(int err) {
    if (err == EAGAIN || err == EWOULDBLOCK){
        std::cout << "EAGAIN" << std::endl;
    }
    else if (err == EBADF){
        std::cout << "EBADF" << std::endl;
    }
    else if (err == EFAULT){
        std::cout << "EFAULT" << std::endl;
    }
    else if (err == EFBIG){
        std::cout << "EFBIG" << std::endl;
    }
    else if (err == EINTR){
        std::cout << "EINTR" << std::endl;
    }
    else if (err == EINVAL){
        std::cout << "EINVAL" << std::endl;
    }
    else if (err == EIO){
        std::cout << "EIO" << std::endl;
    }
    else if (err == EPIPE){
        std::cout << "EPIPE" << std::endl;
    }
}


void probePrint(std::string msg) {
    std::cout << "Hello! I'm just a probe at " << msg << "!" << std::endl;
}


void printFrameData(uint8_t* frame_buffer, int frame_length){
    //// [DEBUG] Print 1st and last 30 bytes of data written to pipe
    for (int i = 0; i < 30; i++)
        printf("0x%02x ", frame_buffer[i]);

    printf(" ... ");

    for (int i = frame_length - 30; i < frame_length; i++)
        printf("0x%02x ", frame_buffer[i]);
    printf("\n");
}


void parseFrameHeader(uint8_t* frame_buffer){
    //// [DEBUG] Print 1st 30 bytes of data in a frame (hex and binary notation)
    for (int i = 0; i < 30; i++)
        printf("0x%02x ", frame_buffer[i]);
    printf("\n");

    for (int i = 0; i < 30; i++)
        std::cout << std::bitset<8>(frame_buffer[i]) << " ";
    std::cout << std::endl << std::endl;
}

void logChannelUtilization(int frame_length, int dct_partition_size, int payload_used, std::chrono::duration<double, std::milli> duration, std::chrono::duration<double, std::milli> assemble_time){
    std::cout << "[chromium_log_channel_performance]|" << frame_length << "|" << dct_partition_size << "|" << payload_used << "|" << duration.count() << "|" << assemble_time.count() << std::endl;
}

void logPacketsInQueue(int packets_in_queue){
    std::cout << "-------------------------" << std::endl;
    std::cout << "[packet_queue_size]|" << packets_in_queue << std::endl;
}

void logPacketsSentInFrame(int packets_sent_in_frame){
    std::cout << "[packets_sent_in_frame]|" << packets_sent_in_frame << std::endl;
}

void logFragmentsSentInFrame(int fragments_sent_in_frame){
    std::cout << "[fragments_sent_in_frame]|" << fragments_sent_in_frame << std::endl;
}

void fillQueue(std::vector<uint8_t> staging_buffer){
    int slice_pos = 0;
    int ptr_pos = 0;
    uint16_t packet_size = ((uint16_t) staging_buffer[ptr_pos + 1] << 8) | staging_buffer[ptr_pos];

    while (packet_size > 0) {
        slice_pos = ptr_pos;
        ptr_pos += packet_size + HEADER_LEN;
        
        if (ptr_pos > (int) staging_buffer.size()) {
            break;
        }
        
        std::vector<uint8_t> pkt(&staging_buffer[slice_pos], &staging_buffer[ptr_pos]);
        
        staging_queue.push_back(pkt);
        
        packet_size = ((uint16_t) staging_buffer[ptr_pos + 1] << 8) | staging_buffer[ptr_pos];
    }
}


void readFromPipe(){
    int read_n_bytes = 4096;
    uint8_t read_buffer[read_n_bytes];
    std::vector<uint8_t> staging_buffer;

    std::chrono::duration<double, std::milli> read_time;
    auto start_read = std::chrono::high_resolution_clock::now();
    while(true){
        int nread = read(encoder_fd, &read_buffer, read_n_bytes);
        if(nread > 1) {
            staging_buffer.insert(staging_buffer.end(), &read_buffer[0], &read_buffer[0] + nread);
        }
        else if (nread == -1) {
            break; //Pipe is empty
        }
        else if (nread == 0) {
            break; //Error in pipe
        }
    }
    auto end_read = std::chrono::high_resolution_clock::now();
    read_time = end_read - start_read;

    if(staging_buffer.size() > 1 && staging_queue.size() < queue_limit){
        fillQueue(staging_buffer);
    }
}


int assembleData(uint8_t* frame_buffer, int dct_partition_offset, int max_payload_size) {
    int data_to_encode = 0;
    int packets_encoded = 0; //for debugging purposes
    int fragments_encoded = 0; //for debugging purposes

    if((staging_queue.size() > 0 || staging_queue_fragments.size() > 0) && debug) {
        logPacketsInQueue(staging_queue.size());
    }

    while(data_to_encode < max_payload_size){
        if(staging_queue_fragments.size() > 0){ //// If there is a fragment of an IP packet to encode
            std::vector<uint8_t> frag(staging_queue_fragments.front());
            uint16_t packet_size = ((uint16_t) frag.data()[1] << 8) | frag.data()[0];
            
            //// The fragment fits whole
            if(data_to_encode + packet_size + HEADER_LEN <= max_payload_size){
                frag.data()[7] = 1;
                
                memcpy(&frame_buffer[dct_partition_offset + sizeof(int) + data_to_encode], &frag.data()[0], packet_size + HEADER_LEN);
                data_to_encode += packet_size + HEADER_LEN;
                staging_queue_fragments.pop_front();
                fragments_encoded += 1; //for debugging purposes
            }//// The fragment must be further fragmented but we can't even fit a header
            else if(data_to_encode + HEADER_LEN > max_payload_size){
                break;            
            }
            else{ //// The fragment will be further fragmented
                uint16_t packet_len_header = max_payload_size - data_to_encode - HEADER_LEN;
                //// Update fragment fields
                // IP_PACKET_LEN_HEADER
                uint8_t packet_len_header_bytes[2] = {(uint8_t) (packet_len_header >> 8), (uint8_t) (packet_len_header) };
                frag.data()[0] = packet_len_header_bytes[1];
                frag.data()[1] = packet_len_header_bytes[0];
                
                
                //// IP_LAST_FRAG_HEADER
                frag.data()[7] = 0;
                
                //// Write fragment to frame
                memcpy(&frame_buffer[dct_partition_offset + sizeof(int) + data_to_encode], &frag.data()[0], packet_len_header + HEADER_LEN);
                data_to_encode += packet_len_header + HEADER_LEN;
                
                //// Prepare resulting fragment
                std::vector<uint8_t> new_frag;
                
                // IP_PACKET_LEN_HEADER - update new size
                uint16_t new_frag_size = packet_size - packet_len_header;
                uint8_t new_frag_size_bytes[2] = {(uint8_t) (new_frag_size >> 8), (uint8_t) (new_frag_size) };
                new_frag.push_back(new_frag_size_bytes[1]);
                new_frag.push_back(new_frag_size_bytes[0]);
                
                // IP_PACKET_ID_HEADER - keep id
                new_frag.push_back(frag.data()[2]);
                new_frag.push_back(frag.data()[3]);
                new_frag.push_back(frag.data()[4]);
                new_frag.push_back(frag.data()[5]);
                
                // IP_FRAG_NUM_HEADER - increase frag number
                new_frag.push_back(frag.data()[6] + 1);
                
                // IP_LAST_FRAG_HEADER - keep last frag to 0
                new_frag.push_back(0);
                
                //Insert data
                new_frag.insert(new_frag.end(), &frag.data()[HEADER_LEN + packet_len_header], &frag.data()[HEADER_LEN + packet_size]);
                staging_queue_fragments.push_back(new_frag);
                staging_queue_fragments.pop_front();
                break;
            }
        }
        else if(staging_queue.size() > 0){ //// If there is an IP packet to encode

            std::vector<uint8_t> packet(staging_queue.front());
           
            uint16_t packet_size = ((uint16_t) packet.data()[1] << 8) | packet.data()[0];
            
            if(data_to_encode + packet_size + HEADER_LEN <= max_payload_size){ // The packet fits whole
                memcpy(&frame_buffer[dct_partition_offset + sizeof(int) + data_to_encode], &packet.data()[0], packet_size + HEADER_LEN);
                data_to_encode += packet_size + HEADER_LEN;
                staging_queue.pop_front();
                packets_encoded += 1; //for debugging purposes
            }
            else if(data_to_encode + HEADER_LEN > max_payload_size){ //// The packet must be further fragmented but we can't even fit a header
                staging_queue_fragments.push_back(packet);
                staging_queue.pop_front();
                break;            
            }
            else{ //// The packet will be fragmented
                uint16_t packet_len_header = max_payload_size - data_to_encode - HEADER_LEN;
                
                //// Update fragment fields
                // IP_PACKET_LEN_HEADER
                uint8_t packet_len_header_bytes[2] = {(uint8_t) (packet_len_header >> 8), (uint8_t) (packet_len_header) };
                packet.data()[0] = packet_len_header_bytes[1];
                packet.data()[1] = packet_len_header_bytes[0];
                
                //// IP_LAST_FRAG_HEADER
                packet.data()[7] = 0;

                //// Write fragment to frame
                memcpy(&frame_buffer[dct_partition_offset + sizeof(int) + data_to_encode], &packet.data()[0], packet_len_header + HEADER_LEN);
                data_to_encode += packet_len_header + HEADER_LEN;
                
                //// Prepare resulting fragment
                std::vector<uint8_t> new_frag;
                
                // IP_PACKET_LEN_HEADER - update new size
                uint16_t new_frag_size = packet_size - packet_len_header;
                uint8_t new_frag_size_bytes[2] = {(uint8_t) (new_frag_size >> 8), (uint8_t) (new_frag_size) };
                new_frag.push_back(new_frag_size_bytes[1]);
                new_frag.push_back(new_frag_size_bytes[0]);
                
                // IP_PACKET_ID_HEADER - keep id
                new_frag.push_back(packet.data()[2]);
                new_frag.push_back(packet.data()[3]);
                new_frag.push_back(packet.data()[4]);
                new_frag.push_back(packet.data()[5]);
                
                // IP_FRAG_NUM_HEADER - increase frag number
                new_frag.push_back(packet.data()[6] + 1);
                
                // IP_LAST_FRAG_HEADER - keep last frag to 0
                new_frag.push_back(0);
                
                //Insert data
                new_frag.insert(new_frag.end(), &packet.data()[HEADER_LEN + packet_len_header], &packet.data()[HEADER_LEN + packet_size]);
                staging_queue_fragments.push_back(new_frag);
                staging_queue.pop_front();
                break;
            }
        } else // There is still space to encode data, but no more packets
            break;
    }

    if(packets_encoded >= 1 && debug){
        logPacketsSentInFrame(packets_encoded);
    }
    if(fragments_encoded >= 1 && debug){
        logFragmentsSentInFrame(fragments_encoded);
    }
    return data_to_encode;
}


void encodeDataIntoFrame(uint8_t* frame_buffer, int frame_length, int dct_partition_offset) {
    
    ////Open FIFO for advertising protozoa of current payload length (P2_len - 4 bytes due to payload header -2 bytes due to terminator)
    int dct_partition_size = frame_length - dct_partition_offset;
    int useful_dct_partition_size = dct_partition_size - sizeof(int); //// 4 bytes are used for header
    int max_payload_size = useful_dct_partition_size - 2; //// 2 bytes for packet data terminator. Client must respect it
    int data_to_encode = 0;
    if(dct_partition_size >= MIN_PAYLOAD_SIZE) {

        ////Encode number of bytes in DCT partition (that the reader must read)
        memcpy(&frame_buffer[dct_partition_offset], &useful_dct_partition_size, sizeof(int));
        
        data_to_encode = assembleData(frame_buffer, dct_partition_offset, max_payload_size);
        
        ////Encode message terminator
        memset(&frame_buffer[dct_partition_offset + sizeof(int) + data_to_encode], 0, 2);

    }
}


void retrieveDataFromFrame(uint8_t* frame_buffer, int frame_length, int dct_partition_offset) {
    int dct_partition_size = frame_length - dct_partition_offset;
    int total_written_bytes = dct_partition_offset;


    if(dct_partition_size >= MIN_PAYLOAD_SIZE) {

        ////Write decoded data
        while(total_written_bytes < frame_length){
            int nwritten = write(decoder_fd, &frame_buffer[total_written_bytes], frame_length - total_written_bytes);
            if(nwritten > 0)
                total_written_bytes += nwritten;
        }
    }
}

void printEncodedImageInfo(uint32_t encodedWidth,
                           uint32_t encodedHeight,
                           size_t length,
                           size_t size,
                           bool completeFrame,
                           int qp,
                           int frameType,
                           uint8_t* buffer,
                           bool printBuffer) {

    std::cout << "[Encoded Image Structure]" << std::endl;
    std::cout << "Width: " << encodedWidth << std::endl;
    std::cout << "Height: " << encodedHeight << std::endl;
    std::cout << "Length: " << length << std::endl;
    std::cout << "Size: " << size << std::endl;
    std::cout << "Quantizer Value: " << qp << std::endl;
    std::cout << "Is complete Frame: " << completeFrame << std::endl;


    switch (frameType) {
        case 0:
            std::cout << "Frame Type: EmptyFrame" << std::endl;
            break;
        case 1:
            std::cout << "Frame Type: AudioFrameSpeech" << std::endl;
            break;
        case 2:
            std::cout << "Frame Type: AudioFrameCN" << std::endl;
            break;
        case 3:
            std::cout << "Frame Type: VideoFrameKey" << std::endl;
            break;
        case 4:
            std::cout << "Frame Type: VideoFrameDelta" << std::endl;
            break;
    }

    if(printBuffer){
        for (unsigned long i = 0; i < length; i++)
            printf("0x%02x ", buffer[i]);
        printf("\n");
    }
    std::cout << std::endl;
}



