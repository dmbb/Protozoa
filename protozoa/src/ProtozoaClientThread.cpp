#include <string>
#include <cstring>
#include <utils.h>
#include "ProtozoaClientThread.h"
#include <chrono>
#include <thread>
#include <iostream>
#include <fstream>
#include <sys/un.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <chrono>
#include <vector>


void ProtozoaClientThread::writeToPipe(int protozoa_encoder_fd){
    std::vector<uint8_t> data_to_encode;

    if(_packets_queue.size() > 0) { //// If there is an IP packet to encode

        PacketData *packetData = _packets_queue.remove();

        // IP_PACKET_LEN_HEADER
        uint16_t packet_len_header = packetData->get_packet_length();
        uint8_t packet_len_header_bytes[2] = {(uint8_t) (packet_len_header >> 8), (uint8_t) (packet_len_header)};
        data_to_encode.push_back(packet_len_header_bytes[1]);
        data_to_encode.push_back(packet_len_header_bytes[0]);

        // IP_PACKET_ID_HEADER
        uint32_t packet_id_header = packetData->get_packet_id();
        uint8_t packet_id_header_bytes[4] = {(uint8_t) (packet_id_header >> 24), (uint8_t) (packet_id_header >> 16),
                                             (uint8_t) (packet_id_header >> 8), (uint8_t) (packet_id_header)};
        data_to_encode.push_back(packet_id_header_bytes[3]);
        data_to_encode.push_back(packet_id_header_bytes[2]);
        data_to_encode.push_back(packet_id_header_bytes[1]);
        data_to_encode.push_back(packet_id_header_bytes[0]);

        // IP_FRAG_NUM_HEADER
        uint8_t packet_fragment = packetData->get_packet_fragment();
        data_to_encode.push_back(packet_fragment);

        // IP_LAST_FRAG_HEADER
        data_to_encode.push_back(packet_fragment);

        // IP_PACKET_DATA
        data_to_encode.insert(data_to_encode.end(), packetData->get_packet_data()->data(),
                              packetData->get_packet_data()->data() + packetData->get_packet_length());

        int nwritten = write(protozoa_encoder_fd, data_to_encode.data(), data_to_encode.size());
        if(nwritten < 0){
            std::cout << "[ProtozoaClientThread::protozoa_encoder_pipe] Error writing data" << std::endl;
            checkPipeError(errno);
        }

        //// Packet fully sent, free memory
        delete packetData;
    }
}

void ProtozoaClientThread::packetDispatchCycle(){
    //// Open FIFO for reading size of frame that can be used for encoding data
    int MAX_PIPE_SIZE = 1048576;

    std::string protozoa_encoder_pipe = "/tmp/protozoa_encoder_pipe";
    int protozoa_encoder_fd = open(protozoa_encoder_pipe.c_str(), O_WRONLY);
    fcntl(protozoa_encoder_fd, F_SETPIPE_SZ, MAX_PIPE_SIZE);

    std::cout << "Opened pipe file descriptors" << std::endl;

    while(true){
            writeToPipe(protozoa_encoder_fd);
    }
}

void* ProtozoaClientThread::run() {
    int MAX_PIPE_SIZE = 1048576;

    std::string protozoa_encoder_pipe = "/tmp/protozoa_encoder_pipe";
    int protozoa_encoder_fd = open(protozoa_encoder_pipe.c_str(), O_WRONLY);
    fcntl(protozoa_encoder_fd, F_SETPIPE_SZ, MAX_PIPE_SIZE);

    printf("Opened pipe file descriptors\n");

    _packet_handler_thread = new PacketHandlerThread(_mode, protozoa_encoder_fd);
    _packet_handler_thread->start();
    _packet_handler_thread->join();

}


ProtozoaClientThread::ProtozoaClientThread(std::string mode) : _mode(mode) {};

