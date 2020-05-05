#ifndef PROTOZOA_HOOKS_H_
#define PROTOZOA_HOOKS_H_

#include <string.h>
#include <string>
#include <mutex>
#include "macros.h"

void printFrameData(uint8_t* frame_buffer, int frame_length);

void printEncodedImageInfo(uint32_t encodedWidth, uint32_t encodedHeight, size_t length, size_t size, bool completeFrame, int qp, int frameType, uint8_t* buffer, bool printBuffer);

void encodeDataIntoFrame(uint8_t* frame_buffer, int frame_length, int dct_partition_offset);

void retrieveDataFromFrame(uint8_t* frame_buffer, int frame_length, int dct_partition_offset);

void probePrint(std::string msg);

void readFromPipe();

static inline uint32_t GetBitsAt(uint32_t data, size_t shift, size_t num_bits) {
  return ((data >> shift) & ((1 << num_bits) - 1));
}

#endif //PROTOZOA_HOOKS_H_
