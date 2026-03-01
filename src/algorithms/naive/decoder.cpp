#include "decoder.h"
#include <cstdint>

static uint16_t alaw_to_linear(uint8_t alaw)
{
    alaw ^= 0x55;

    uint8_t sign     = alaw & 0x80;
    uint8_t exponent = (alaw >> 4) & 0x07;
    uint8_t mantissa = alaw & 0x0F;

    int16_t sample;
    if (exponent == 0)
    {
        sample = static_cast<int16_t>(mantissa) << 1;
    }
    else
    {
        sample = static_cast<int16_t>((mantissa | 0x10) << (exponent + 3));
    }

    if (sign)
    {
        sample = -sample;
    }

    return static_cast<uint16_t>(sample);
}

void ALawDecoder::Decode(const uint8_t* in, uint16_t* out, size_t size)
{
    for (size_t i = 0; i < size; ++i)
    {
        out[i] = alaw_to_linear(in[i]);
    }
}