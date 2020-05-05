#include <cstdint>
#include <vector>

#ifndef PROTOZOA_PACKETDATA_H
#define PROTOZOA_PACKETDATA_H

//Manages data from packets gathered on libnetfilter_queue

const int IP_PACKET_ID_HEADER = 4;
const int IP_PACKET_LEN_HEADER = 2;
const int IP_FRAG_NUM_HEADER = 1;
const int IP_LAST_FRAG_HEADER = 1;
const int HEADER_LEN = 8;

class PacketData {

private:
    uint32_t _packet_id;
    std::vector<uint8_t>* _packet_data;
    uint16_t _packet_length;
    uint8_t  _packet_fragment;
    uint8_t _last_fragment;

    //Non-header fields
    uint16_t _total_length;
    uint16_t _already_sent_data;


public:
    PacketData(uint32_t packet_id, std::vector<uint8_t> packet_data, uint16_t packet_length, uint8_t packet_fragment, uint8_t last_fragment, uint16_t already_sent_data) : _packet_id(packet_id),
           _packet_length(packet_length), _total_length(packet_length), _packet_fragment(packet_fragment), _last_fragment(last_fragment), _already_sent_data(already_sent_data) {
        _packet_data = new std::vector<uint8_t>(packet_data);
    }


    uint32_t get_packet_id() const { return _packet_id; }

    std::vector<uint8_t>* get_packet_data() const { return _packet_data; }

    uint16_t get_packet_length() const { return _packet_length; }

    uint8_t get_packet_fragment() const { return _packet_fragment; }

    uint8_t get_packet_total_fragments() const { return _last_fragment; }

    uint16_t get_total_length() const { return _total_length; }

    uint16_t get_already_sent_data() const { return _already_sent_data; }


    void set_total_length(uint16_t total_length) {
        PacketData::_total_length = total_length;
    }

    void increase_already_sent_data(uint16_t already_sent_data) {
        PacketData::_already_sent_data += already_sent_data;
    }

    void increase_packet_fragment() {
        PacketData::_packet_fragment += 1;
    }

    void set_last_fragment(uint8_t last_fragment) {
        PacketData::_last_fragment = last_fragment;
    }

};

#endif //PROTOZOA_PACKETDATA_H
