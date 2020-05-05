#include "utils.h"
#include <errno.h>
#include <iostream>

void checkPipeError(int err) {
    if (err == EAGAIN || err == EWOULDBLOCK){
        std::cout << "EAGAIN" << std::endl;
    }
    else if (err == EBADF){
        std::cout << "EBADF" << std::endl;
    }
    else if (err == EFAULT){
        std::cout << "EFAULT" << std::endl;
    }
    else if (err == EFBIG){
        std::cout << "EFBIG" << std::endl;
    }
    else if (err == EINTR){
        std::cout << "EINTR" << std::endl;
    }
    else if (err == EINVAL){
        std::cout << "EINVAL" << std::endl;
    }
    else if (err == EIO){
        std::cout << "EIO" << std::endl;
    }
    else if (err == EPIPE){
        std::cout << "EPIPE" << std::endl;
    }
}