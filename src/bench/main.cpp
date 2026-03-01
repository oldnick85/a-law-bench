#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

#ifndef ALGORITHM_NAME
#define ALGORITHM_NAME "unknown"
#endif

#include "decoder.h"
#include "encoder.h"

class ALawEncoder;
class ALawDecoder;

constexpr std::size_t SamplesToTest   = 100'000'000;
constexpr std::size_t SamplesInMemory = 10'000'000;
constexpr std::size_t Rounds          = SamplesToTest / SamplesInMemory;

using Clock = std::chrono::high_resolution_clock;
using namespace std::chrono;

struct Statistics {
    std::size_t total_samples{};
    double total_seconds{};
    double seconds_per_sample{};
    double samples_per_second{};
};

Statistics TestEncode()
{
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<int> dist_uint16(0, 0xFFFF);

    std::vector<uint16_t> encode_in;
    std::vector<uint8_t> encode_out;

    encode_in.reserve(SamplesInMemory);
    encode_out.reserve(SamplesInMemory);

    for (std::size_t i = 0; i < SamplesInMemory; ++i)
    {
        encode_in.push_back(static_cast<std::uint16_t>(dist_uint16(gen)));
    }

    ALawEncoder encoder;

    auto start = Clock::now();
    for (std::size_t round = 0; round < Rounds; ++round)
    {
        encoder.Encode(encode_in.data(), encode_out.data(), SamplesInMemory);
    }
    auto end = Clock::now();

    Statistics stat;
    stat.total_samples      = SamplesToTest;
    stat.total_seconds      = double(duration_cast<nanoseconds>(end - start).count()) / 1'000'000'000.0;
    stat.seconds_per_sample = stat.total_seconds / SamplesToTest;
    stat.samples_per_second = SamplesToTest / stat.total_seconds;

    return stat;
}

Statistics TestDecode()
{
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<int> dist_uint8(0, 0xFF);

    std::vector<uint8_t> decode_in;
    std::vector<uint16_t> decode_out;

    decode_in.reserve(SamplesInMemory);
    decode_out.reserve(SamplesInMemory);

    for (std::size_t i = 0; i < SamplesInMemory; ++i)
    {
        decode_in.push_back(static_cast<std::uint8_t>(dist_uint8(gen)));
    }

    ALawDecoder decoder;

    auto start = Clock::now();
    for (std::size_t round = 0; round < Rounds; ++round)
    {
        decoder.Decode(decode_in.data(), decode_out.data(), SamplesInMemory);
    }
    auto end = Clock::now();

    Statistics stat;
    stat.total_seconds      = double(duration_cast<nanoseconds>(end - start).count()) / 1'000'000'000.0;
    stat.seconds_per_sample = stat.total_seconds / SamplesToTest;
    stat.samples_per_second = SamplesToTest / stat.total_seconds;

    return stat;
}

int main(int argc, char* argv[])
{
    const auto encode_stat = TestEncode();
    const auto decode_stat = TestDecode();

    std::cout << "{"
              << "\"benchmark\": \"speed\","
              << "\"algorithm\": \"" << ALGORITHM_NAME << "\","
              << "\"encode\": {"
              << "\"samples\": " << encode_stat.total_samples << ","
              << "\"total_seconds\": " << std::fixed << std::setprecision(6) << encode_stat.total_seconds << ","
              << "\"seconds_per_sample\": " << std::scientific << encode_stat.seconds_per_sample << ","
              << "\"samples_per_second\": " << std::fixed << encode_stat.samples_per_second << "},"
              << "\"decode\": {"
              << "\"samples\": " << decode_stat.total_samples << ","
              << "\"total_seconds\": " << std::fixed << std::setprecision(6) << decode_stat.total_seconds << ","
              << "\"seconds_per_sample\": " << std::scientific << decode_stat.seconds_per_sample << ","
              << "\"samples_per_second\": " << std::fixed << decode_stat.samples_per_second << "}"
              << "}" << std::endl;

    return 0;
}