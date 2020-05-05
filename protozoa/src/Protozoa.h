#include "PacketHandlerThread.h"
#include "ProtozoaServerThread.h"
#include <string>

#ifndef __protozoa_h__
#define __protozoa_h__

class Protozoa {
  private:
    PacketHandlerThread* _packet_handler_thread;
    ProtozoaServerThread* _protozoa_server_thread;

  public:
    Protozoa();
    int start(std::string mode);

};


#endif
