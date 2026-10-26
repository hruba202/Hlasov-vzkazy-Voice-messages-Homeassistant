#pragma once
#include <cstddef>
#include <cstdint>
namespace esphome::mic_48_to_16 {
// 63-tap Hamming-windowed sinc, cutoff 6500 Hz at 48000 Hz; Q15 unity DC.
static constexpr size_t FIR_TAPS = 63;
static constexpr int16_t FIR_COEFFICIENTS[FIR_TAPS] = {
  25, 11, -14, -36, -38, -7, 45, 83, 67, -16, -122, -170, -92, 94, 273, 292, 76, -276, -525, -430, 46, 648, 934, 559, -426, -1473, -1762, -650, 1890, 5121, 7822, 8870, 7822, 5121, 1890, -650, -1762, -1473, -426, 559, 934, 648, 46, -430, -525, -276, 76, 292, 273, 94, -92, -170, -122, -16, 67, 83, 45, -7, -38, -36, -14, 11, 25
};
}
