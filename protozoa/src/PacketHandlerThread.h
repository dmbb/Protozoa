#include <thread.h>
#include <wqueue.h>
#include <string>
#include <PacketData.h>

#ifndef PROTOZOA_PACKETHANDLERTHREAD_H
#define PROTOZOA_PACKETHANDLERTHREAD_H


class PacketHandlerThread : public Thread {

private:
    std::string _mode;
    int _protozoa_handler_fd;


public:
    int get_protozoa_handler_fd() const;


public:
    PacketHandlerThread(std::string mode, int protozoa_handler_fd);
    void* run();
};

#endif //PROTOZOA_PACKETHANDLERTHREAD_H
