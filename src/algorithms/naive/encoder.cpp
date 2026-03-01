#include "encoder.h"
#include <cstdint>

static uint8_t linear_to_alaw(uint16_t linear)
{
    int16_t pcm = static_cast<int16_t>(linear);

    uint8_t sign = 0;
    uint16_t mag;
    if (pcm < 0)
    {
        sign = 0x80;
        mag  = static_cast<uint16_t>(-pcm);
    }
    else
    {
        sign = 0;
        mag  = static_cast<uint16_t>(pcm);
    }

    if (mag > 0x1FFF)
        mag = 0x1FFF;

    uint8_t exponent;
    uint8_t mantissa;

    if (mag >= 0x1000)
    {
        exponent = 7;
        mantissa = (mag >> 8) & 0x0F;
    }
    else if (mag >= 0x0800)
    {
        exponent = 6;
        mantissa = (mag >> 7) & 0x0F;
    }
    else if (mag >= 0x0400)
    {
        exponent = 5;
        mantissa = (mag >> 6) & 0x0F;
    }
    else if (mag >= 0x0200)
    {
        exponent = 4;
        mantissa = (mag >> 5) & 0x0F;
    }
    else if (mag >= 0x0100)
    {
        exponent = 3;
        mantissa = (mag >> 4) & 0x0F;
    }
    else if (mag >= 0x0080)
    {
        exponent = 2;
        mantissa = (mag >> 3) & 0x0F;
    }
    else if (mag >= 0x0040)
    {
        exponent = 1;
        mantissa = (mag >> 2) & 0x0F;
    }
    else
    {
        exponent = 0;
        mantissa = mag >> 1;
    }

    uint8_t alaw = sign | (exponent << 4) | mantissa;

    alaw ^= 0x55;

    return alaw;
}

void ALawEncoder::Encode(const uint16_t* in, uint8_t* out, size_t size)
{
    for (size_t i = 0; i < size; ++i)
    {
        out[i] = linear_to_alaw(in[i]);
    }
}