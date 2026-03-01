#pragma once

#include <cstddef>
#include <cstdint>

class ALawDecoder
{
  public:
    void Decode(const uint8_t* in, uint16_t* out, size_t size);
};