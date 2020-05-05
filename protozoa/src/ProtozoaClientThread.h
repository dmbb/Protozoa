#include <thread.h>
#include <wqueue.h>
#include <PacketHandlerThread.h>
#include <string>
#include <PacketData.h>
#include <unistd.h>
#include <fcntl.h>

#ifndef PROTOZOA_PROTOZOACLIENTTHREAD_H
#define PROTOZOA_PROTOZOACLIENTTHREAD_H


class ProtozoaClientThread : public Thread {

private:
    std::string _mode;
    wqueue<PacketData*> _packets_fragments_queue;
    wqueue<PacketData*> _packets_queue;
    PacketHandlerThread* _packet_handler_thread;

    void packetDispatchCycle();
    void writeToPipe(int protozoa_encoder_fd);

public:
    ProtozoaClientThread(std::string mode);
    void* run();
};



#endif //PROTOZOA_PROTOZOACLIENTTHREAD_H
