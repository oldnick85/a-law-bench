#pragma once

#include <cstddef>
#include <cstdint>

class ALawEncoder
{
  public:
    void Encode(const uint16_t* in, uint8_t* out, size_t size);
};