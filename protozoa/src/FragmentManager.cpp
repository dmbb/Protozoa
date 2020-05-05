#include "FragmentManager.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>
#include <algorithm>
#include <sys/socket.h>
#include <arpa/inet.h>

bool compareBySeqNum(const PacketData* a, const PacketData* b){
    return a->get_packet_fragment() < b->get_packet_fragment();
}


void FragmentManager::setTotalFragmentNumber(int total_fragments_to_completion){
    _total_fragments_to_completion = total_fragments_to_completion;
}


bool FragmentManager::isPacketComplete() {
    //Packet is complete when total fragment number has been set and all fragments have been received
    return _total_fragments_to_completion > 0 && _data_fragments.size() == _total_fragments_to_completion;
}


void FragmentManager::initDataStage(PacketData* fragment){
    _data_fragments.push_back(fragment);
    _total_fragments_to_completion = 0;
}


bool FragmentManager::isFragmentPresent(int packet_fragment_number){
    bool found = false;
    for(auto it = _data_fragments.begin(); it != _data_fragments.end(); ++it){
        PacketData* p = *it;
        if(p->get_packet_fragment() == packet_fragment_number)
            found = true;
    }
    return found;
}


void FragmentManager::addFragment(PacketData* data_fragment){
    _data_fragments.push_back(data_fragment);
}


void FragmentManager::printFragment(){
    std::cout << "printing pieces numbers" << std::endl;
    for(auto it = _data_fragments.begin(); it!=_data_fragments.end(); ++it){
        PacketData* p = *it;
        std::cout << p->get_packet_fragment() << std::endl;
    }
}


void FragmentManager::deliverPacket(std::vector<uint8_t>& packet_data){
    //Raw socket creation for inserting returning IP packet on the network
    std::string address;
    if(_mode == "client")
        address = "10.10.10.10";
    else
        address = "20.20.20.20";

    struct sockaddr_in sin;
    sin.sin_family = AF_INET;
    sin.sin_addr.s_addr = inet_addr(address.c_str());

    if (sendto (_sockfd, packet_data.data(), packet_data.size() ,  0, (struct sockaddr *) &sin, sizeof (sin)) <0){
        perror("[FragmentManager::deliverPacket] sendto failed");
    }
}

void FragmentManager::deleteFragments(){
    for(auto it = _data_fragments.begin(); it!=_data_fragments.end(); ++it){
        PacketData* p = *it;
        delete p;
    }
}

void FragmentManager::assemblePacket(){
    //Sort packet fragments
    sort(_data_fragments.begin(), _data_fragments.end(), compareBySeqNum);

    std::vector<uint8_t> packet_data;

    //Build packet_data by concatenating all individual fragment data
    for(auto it = _data_fragments.begin(); it!=_data_fragments.end(); ++it){
        PacketData* p = *it;
        packet_data.insert(packet_data.end(), p->get_packet_data()->data(), p->get_packet_data()->data() + p->get_packet_length());
    }

    deliverPacket(packet_data);
    deleteFragments();
}


FragmentManager::FragmentManager(std::string mode, int sockfd) : _mode(mode), _sockfd(sockfd) {};
