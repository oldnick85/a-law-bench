#include "decoder.h"
#include <array>
#include <cstdint>

namespace
{

std::array<uint16_t, 256> create_decode_table()
{
    std::array<uint16_t, 256> table{};

    auto alaw_to_linear = [](uint8_t alaw) -> uint16_t {
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
    };

    for (size_t i = 0; i < 256; ++i)
    {
        table[i] = alaw_to_linear(static_cast<uint8_t>(i));
    }
    return table;
}

const std::array<uint16_t, 256> decode_table = create_decode_table();

}  // namespace

void ALawDecoder::Decode(const uint8_t* in, uint16_t* out, size_t size)
{
    for (size_t i = 0; i < size; ++i)
    {
        out[i] = decode_table[in[i]];
    }
}