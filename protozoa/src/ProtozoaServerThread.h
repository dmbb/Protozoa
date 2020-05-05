#include <wqueue.h>
#include <thread.h>
#include <mutex>
#include <map>
#include <string>
#include "FragmentManager.h"

#ifndef PROTOZOA_PROTOZOASERVERTHREAD_H
#define PROTOZOA_PROTOZOASERVERTHREAD_H

class ProtozoaServerThread : public Thread {

private:
    std::string _mode;
    std::map<int, FragmentManager>* _dataStore;
    int _sock;

    int readFromPipe(uint8_t* msg, int read_buffer_len, int fd);
    int readNextFramePayloadSize(int fd);
    void updatePacketFragmentsMap(PacketData* data_fragment);
    void gatherPayload(uint8_t* frame_content);

public:
    ProtozoaServerThread(std::string mode);
    void* run();
};


#endif //PROTOZOA_PROTOZOASERVERTHREAD_H
