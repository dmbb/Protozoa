#include "PacketHandlerThread.h"
#include <libnetfilter_queue/libnetfilter_queue.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <linux/netfilter.h>
#include <linux/ip.h>
#include <chrono>
#include <cstring>
#include <sys/un.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>


int packetHandler(struct nfq_q_handle *queue, struct nfgenmsg *msg, struct nfq_data *pkt, void *cbData) {
    auto time_packet_received = std::chrono::high_resolution_clock::now();

    PacketHandlerThread *_packet_handler_thread = (PacketHandlerThread *) cbData;

    uint32_t pktID = 0;
    struct nfqnl_msg_packet_hdr *header;
    struct iphdr *ip_header;
    uint8_t *packet_data;


    if(header = nfq_get_msg_packet_hdr(pkt))
        pktID = ntohl(header->packet_id);

    nfq_get_payload ( ( struct nfq_data * ) pkt, (unsigned char**)&ip_header);

    int packet_length = nfq_get_payload(pkt, &packet_data);

    //// Place data into vector
    std::vector<uint8_t> packet_data_copy (&packet_data[0], &packet_data[0] + packet_length);

    //inet_ntoa is non-reentrant :'(
    char *source = inet_ntoa(*(in_addr *) &ip_header->saddr);
    char *dest = inet_ntoa(*(in_addr *) &ip_header->daddr);


    //Gather extra packet payload
    PacketData* packetData = new PacketData(pktID, packet_data_copy, static_cast<uint16_t>(packet_length), 1, 1, 0);

    //Write Application packet to pipe
    std::vector<uint8_t> data_to_encode;
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

    int nwritten = write(_packet_handler_thread->get_protozoa_handler_fd(), data_to_encode.data(), data_to_encode.size());
    if(nwritten < 0){
        printf("[ProtozoaClientThread::protozoa_encoder_pipe] Error writing data\n");
    }

    return nfq_set_verdict(queue, pktID, NF_STOLEN, packet_length, packet_data);
}


void* PacketHandlerThread::run() {

    //set up network container
    std::string cmd = "./../src/scripts/network_container.sh " + _mode;
    int container_result = system(cmd.c_str());

    //set up netfilter data structures
    struct nfq_handle *nfqHandle;
    struct nfq_q_handle *queue;
    struct nfnl_handle *netlinkHandle;

    int fd, res;
    char buf[2048];

    // _queue connection
    if (!(nfqHandle = nfq_open())) {
        perror("Error in nfq_open()");
    }

    // bind this handler
    if (nfq_bind_pf(nfqHandle, AF_INET) < 0) {
        perror("Error in nfq_bind_pf()");
    }

    // define a handler
    //LibNetfilterQueue number
    u_int16_t queue_no;
    if(_mode == "client") {
        queue_no = 0;
        printf("Client mode: Queue %d\n", queue_no);
    } else {
        queue_no = 1;
        printf("Server mode: Queue %d\n", queue_no);
    }

    if (!(queue = nfq_create_queue(nfqHandle, queue_no, &packetHandler, this))) {
        perror("Error in nfq_create_queue()");
    }

    // turn on packet copy mode
    if (nfq_set_mode(queue, NFQNL_COPY_PACKET, 0xffff) < 0) {
        perror("Could not set packet copy mode");
    }

    if (nfq_set_queue_maxlen(queue, 1048576) < 0) {
        perror("Could not set queue max length");
    }

    netlinkHandle = nfq_nfnlh(nfqHandle);

    //Increase nfnl_recv buffer size
    nfnl_rcvbufsiz(netlinkHandle, 1048576);
    nfnl_set_rcv_buffer_size(netlinkHandle, 1048576);
    fd = nfnl_fd(netlinkHandle);

    //main cycle
    while(true){
        if((res = recv(fd, buf, sizeof(buf), 0)) && res >= 0) {
            nfq_handle_packet(nfqHandle, buf, res);
            continue;
        }
        else if(errno == ENOBUFS)
            printf("[ProtozoaClientThread::packetHandler] ENOBUFS\n");
        else if(errno == NETLINK_NO_ENOBUFS)
            printf("[ProtozoaClientThread::packetHandler] NETLINK_NO_ENOBUFS\n");
        else
            printf("[ProtozoaClientThread::packetHandler] Error on netlink recv()\n");
    }

    nfq_destroy_queue(queue);
    nfq_close(nfqHandle);

}


PacketHandlerThread::PacketHandlerThread(std::string mode, int protozoa_handler_fd) : _mode(mode), _protozoa_handler_fd(protozoa_handler_fd) {}

int PacketHandlerThread::get_protozoa_handler_fd() const {
    return _protozoa_handler_fd;
};

