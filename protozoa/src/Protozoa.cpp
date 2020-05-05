#include "Protozoa.h"
#include <cmdline.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <fcntl.h>

Protozoa::Protozoa() {};


int Protozoa::start(std::string mode) {

    std::string protozoa_encoder_pipe = "/tmp/protozoa_encoder_pipe";
    mkfifo(protozoa_encoder_pipe.c_str(), 0666);
    int protozoa_encoder_fd = open(protozoa_encoder_pipe.c_str(), O_WRONLY);
    int MAX_PIPE_SIZE = 1048576;
    fcntl(protozoa_encoder_fd, F_SETPIPE_SZ, MAX_PIPE_SIZE);
    std::cout << "Started Encoder Pipe" << std::endl;

    std::string protozoa_decoder_pipe = "/tmp/protozoa_decoder_pipe";
    mkfifo(protozoa_decoder_pipe.c_str(), 0666);
    std::cout << "Started Decoder Pipe" << std::endl;

    _packet_handler_thread = new PacketHandlerThread(mode, protozoa_encoder_fd);
    _packet_handler_thread->start();

    _protozoa_server_thread = new ProtozoaServerThread(mode);
    _protozoa_server_thread->start();

    _packet_handler_thread->join();
    _protozoa_server_thread->join();

    return 0;
}


int main(int argc, char *argv[]){
    
    cmdline::parser parser;

    parser.add<string>("mode", 'm', "client / server", true, "");
    parser.parse_check(argc, argv);

    std::string mode = parser.get<string>("mode");
    if(mode != "client" && mode != "server"){
        std::cout << "Choose client or server mode. Exiting..." << std::endl;
        return 0;
    }

    std::cout << "Starting Protozoa in " << mode << " mode..." << std::endl;
    
    Protozoa* protozoa = new Protozoa();

    protozoa->start(mode);

    std::cout << "Exiting..." << std::endl;
    return 0;
}
