#include "ProtozoaServerThread.h"
#include <utils.h>
#include <FragmentManager.h>
#include <string>
#include <libnetfilter_queue/libnetfilter_queue.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <cstring>
#include <linux/ip.h>
#include <chrono>
#include <thread>
#include <iostream>
#include <fstream>
#include <fcntl.h>
#include <unistd.h>
#include <PacketData.h>
#include <bitset>


int ProtozoaServerThread::readNextFramePayloadSize(int fd){

    int payload_length;

    //Attempt to perform read from the pipe
    int nread = read(fd, &payload_length, sizeof(int));

    if(nread == -1) {
        std::cout << "[ProtozoaServerThread::readNextFramePayloadSize] Error in pipe read" << std::endl;
        checkPipeError(errno);
        return nread;
    }
    else if (nread == 0) {
        //std::cout << "[ProtozoaServerThread::readNextFramePayloadSize] Pipe EOF" << std::endl;
        return nread;
    }
    // if we read bytes (in this case 4), return the read dct_coeff partition len
    else if(nread > 0) {
        //close(fd);
        return payload_length;
    }
}

int ProtozoaServerThread::readFromPipe(uint8_t* msg, int read_buffer_len, int fd){

    int total_read_bytes = 0;

    while(total_read_bytes < read_buffer_len) {

        //Attempt to perform read from the pipe
        int nread = read(fd, &msg[total_read_bytes], read_buffer_len - total_read_bytes);

        // nread == -1 means pipe is empty
        if(nread == -1) {
            std::cout << "[ProtozoaServerThread::readFromPipe] Error in pipe read" << std::endl;
            checkPipeError(errno);
        }
        // nread == 0 means all is written / Pipe EOF
        else if(nread == 0) {
            //std::cout << "[ProtozoaServerThread::readFromPipe] Pipe EOF" << std::endl;
        }
        // nread > 0 yields number of bytes read
        else if(nread > 0) {
            //std::cout << "[protozoa_decoder_pipe] Read " << nread << " bytes" << std::endl;
            total_read_bytes += nread;
        }
    }
    return total_read_bytes;
}


void ProtozoaServerThread::updatePacketFragmentsMap(PacketData* data_fragment){

    //If packet has not been seen before, create a map entry for it
    if(!_dataStore->count(data_fragment->get_packet_id())){
        FragmentManager fragment_manager = FragmentManager(_mode, _sock);
        fragment_manager.initDataStage(data_fragment);
        _dataStore->emplace(data_fragment->get_packet_id(), fragment_manager);

        //Check whether the packet arrived in a single fragment
        if(data_fragment->get_packet_total_fragments() == 1 && data_fragment->get_packet_fragment() == 1) {
            _dataStore->at(data_fragment->get_packet_id()).assemblePacket();
            _dataStore->erase(data_fragment->get_packet_id());
        }
    }
        // If packet is already acknowledged, account for new fragment & check whether it is now complete
    else {
        if(!_dataStore->at(data_fragment->get_packet_id()).isFragmentPresent(data_fragment->get_packet_fragment())){
            _dataStore->at(data_fragment->get_packet_id()).addFragment(data_fragment);

            //Check if we got the last fragment. If so, set the total fragments number
            if(data_fragment->get_packet_total_fragments())
                _dataStore->at(data_fragment->get_packet_id()).setTotalFragmentNumber(data_fragment->get_packet_fragment());

            //Check whether the packet is now complete
            if(_dataStore->at(data_fragment->get_packet_id()).isPacketComplete()) {
                _dataStore->at(data_fragment->get_packet_id()).assemblePacket();
                _dataStore->erase(data_fragment->get_packet_id());
            }
        }
    }
}


void ProtozoaServerThread::gatherPayload(uint8_t *frame_content) {
    // Read data from frame and gather the embedded IP packets

    // Start reading from the first frame payload position
    int ptr_pos = 0;

    // Packet length header represented in 2 bytes
    // Build the first packet len by concatenation to unsigned short
    uint16_t packet_size = ((uint16_t)frame_content[ptr_pos + 1] << 8) | frame_content[ptr_pos];

    int packets_on_frame = 0;
    if(packet_size > 0)
        packets_on_frame = 1;


    //Packet splitting loop
    while(packet_size > 0) {
        uint32_t packet_id = ((uint32_t)frame_content[ptr_pos + 5] << 24) | frame_content[ptr_pos + 4] << 16 | frame_content[ptr_pos + 3] << 8 | frame_content[ptr_pos + 2];
        uint8_t  packet_fragment = frame_content[ptr_pos + 6];
        uint8_t last_fragment = frame_content[ptr_pos + 7];

        //// Retrieve packet content
        std::vector<uint8_t> packet_data (&frame_content[ptr_pos + HEADER_LEN], &frame_content[ptr_pos + HEADER_LEN + packet_size]);

        //// Buffer fragments and deliver full packets to the network
        PacketData* data = new PacketData(packet_id, packet_data, packet_size, packet_fragment, last_fragment, 0);
        updatePacketFragmentsMap(data);

        //// Update pointer for next possible packet
        //Move pointer by packet size header + IP packet size
        ptr_pos += packet_size + HEADER_LEN;
        //Check packet size for next packet
        packet_size = ((uint16_t) frame_content[ptr_pos + 1] << 8) | frame_content[ptr_pos];

        if(packet_size > 0)
            packets_on_frame++;
    }
}



void *ProtozoaServerThread::run() {
    _dataStore = new std::map<int, FragmentManager>;

    // Open FIFO for Read only
    int MAX_PIPE_SIZE = 1048576;
    std::string protozoa_decoder_pipe = "/tmp/protozoa_decoder_pipe";
    int fd = open(protozoa_decoder_pipe.c_str(), O_RDONLY);
    fcntl(fd, F_SETPIPE_SZ, MAX_PIPE_SIZE);

    while(true){

        //Get to know how many payload bytes we are going to read
        int read_buffer_len = readNextFramePayloadSize(fd);

        //Read incoming dct_coeffs buffer and extract meaningful data
        if(read_buffer_len > 0) {
            auto time_frame_received = std::chrono::high_resolution_clock::now();

            // Set up read buffer
            uint8_t msg[read_buffer_len];
            memset(msg, 0, static_cast<size_t>(read_buffer_len));

            // Wait for incoming data to be written to pipe
            int read_frame_bytes = readFromPipe(msg, read_buffer_len, fd);
            if(read_frame_bytes < read_buffer_len)
                printf("[ProtozoaServerThread::run] Failed. Read %d of total %d bytes\n", read_frame_bytes, read_buffer_len);

            //Split packets received through the pipe
            gatherPayload(msg);

        }
    }
}

ProtozoaServerThread::ProtozoaServerThread(std::string mode) : _mode(mode) {
    _sock = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    if(_sock == -1){
        perror("[ProtozoaServerThread.cpp::ProtozoaServerThread] Failed to create raw socket.");
        exit(1);
    }
};

