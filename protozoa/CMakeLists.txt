cmake_minimum_required(VERSION 3.12)
project(Protozoa)

#Set Global Compiler Options
set(CMAKE_CXX_STANDARD 14)
#add_compile_options(-Wall)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin)

#Gather source files to include
file(GLOB_RECURSE include_src relative ${CMAKE_CURRENT_SOURCE_DIR} "src/include/*.cpp")

# Setup protozoa target
add_executable(protozoa
        src/Protozoa.cpp
        src/ProtozoaClientThread.cpp
        src/ProtozoaServerThread.cpp
        src/FragmentManager.cpp
        ${include_src}
        src/PacketHandlerThread.cpp src/PacketHandlerThread.h)

target_include_directories(protozoa
        PRIVATE $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
        PRIVATE $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src/include>
        )

target_link_libraries(protozoa
        pthread
        netfilter_queue
        nfnetlink
        )

target_compile_options(protozoa PRIVATE -fpermissive -c -O3)