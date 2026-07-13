// Render timestamped YM2151 register writes with Aaron Giles' YMFM core.
//
// The Python front end writes a compact binary stream:
//   "GYM1", uint32 native_sample_count, uint32 event_count
//   event_count * { uint32 sample_index, uint8 register, uint8 value }
// Output is interleaved little-endian signed 16-bit stereo PCM at the
// YM2151 native sample rate.

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <vector>

#include "ymfm_opm.h"

namespace
{

struct event
{
    uint32_t sample;
    uint8_t reg;
    uint8_t value;
};

class interface : public ymfm::ymfm_interface
{
};

bool read_u32(FILE *file, uint32_t &value)
{
    uint8_t bytes[4];
    if (std::fread(bytes, 1, 4, file) != 4)
        return false;
    value = uint32_t(bytes[0]) | (uint32_t(bytes[1]) << 8) |
            (uint32_t(bytes[2]) << 16) | (uint32_t(bytes[3]) << 24);
    return true;
}

bool write_i16(FILE *file, int32_t value)
{
    value = std::max(-32768, std::min(32767, value));
    uint16_t sample = uint16_t(int16_t(value));
    uint8_t bytes[2] = { uint8_t(sample), uint8_t(sample >> 8) };
    return std::fwrite(bytes, 1, 2, file) == 2;
}

} // anonymous namespace

int main(int argc, char **argv)
{
    if (argc != 3)
    {
        std::fprintf(stderr, "usage: %s events.bin output.pcm\n", argv[0]);
        return 2;
    }

    FILE *input = std::fopen(argv[1], "rb");
    if (input == nullptr)
    {
        std::perror(argv[1]);
        return 2;
    }

    uint8_t magic[4];
    uint32_t sample_count = 0;
    uint32_t event_count = 0;
    if (std::fread(magic, 1, 4, input) != 4 ||
        magic[0] != 'G' || magic[1] != 'Y' ||
        magic[2] != 'M' || magic[3] != '1' ||
        !read_u32(input, sample_count) || !read_u32(input, event_count))
    {
        std::fprintf(stderr, "invalid YMFM event file\n");
        std::fclose(input);
        return 2;
    }

    std::vector<event> events;
    events.reserve(event_count);
    for (uint32_t index = 0; index < event_count; ++index)
    {
        event item{};
        if (!read_u32(input, item.sample) ||
            std::fread(&item.reg, 1, 1, input) != 1 ||
            std::fread(&item.value, 1, 1, input) != 1)
        {
            std::fprintf(stderr, "truncated YMFM event file\n");
            std::fclose(input);
            return 2;
        }
        events.push_back(item);
    }
    std::fclose(input);

    FILE *output = std::fopen(argv[2], "wb");
    if (output == nullptr)
    {
        std::perror(argv[2]);
        return 2;
    }

    interface intf;
    ymfm::ym2151 chip(intf);
    chip.reset();
    ymfm::ym2151::output_data sample{};
    size_t event_index = 0;

    for (uint32_t position = 0; position < sample_count; ++position)
    {
        while (event_index < events.size() && events[event_index].sample <= position)
        {
            chip.write(0, events[event_index].reg);
            chip.write(1, events[event_index].value);
            ++event_index;
        }
        chip.generate(&sample);
        if (!write_i16(output, sample.data[0]) ||
            !write_i16(output, sample.data[1]))
        {
            std::fprintf(stderr, "failed writing PCM output\n");
            std::fclose(output);
            return 2;
        }
    }

    std::fclose(output);
    return 0;
}
