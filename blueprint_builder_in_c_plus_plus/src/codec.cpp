#include "codec.hpp"

#include <cstring>
#include <stdexcept>
#include <vector>
#include <zlib.h>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace factorio {
namespace {
std::string base64_encode(const std::vector<unsigned char>& input) {
    static constexpr char alphabet[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string output;
    output.reserve(((input.size() + 2) / 3) * 4);
    for (std::size_t index = 0; index < input.size(); index += 3) {
        const unsigned value = (static_cast<unsigned>(input[index]) << 16U)
            | (index + 1 < input.size() ? static_cast<unsigned>(input[index + 1]) << 8U : 0U)
            | (index + 2 < input.size() ? static_cast<unsigned>(input[index + 2]) : 0U);
        output.push_back(alphabet[(value >> 18U) & 63U]);
        output.push_back(alphabet[(value >> 12U) & 63U]);
        output.push_back(index + 1 < input.size() ? alphabet[(value >> 6U) & 63U] : '=');
        output.push_back(index + 2 < input.size() ? alphabet[value & 63U] : '=');
    }
    return output;
}
}  // namespace

std::string encode_blueprint(const std::string& json) {
    uLongf compressed_size = compressBound(static_cast<uLong>(json.size()));
    std::vector<unsigned char> compressed(compressed_size);
    const int status = compress2(
        compressed.data(), &compressed_size,
        reinterpret_cast<const Bytef*>(json.data()), static_cast<uLong>(json.size()),
        Z_DEFAULT_COMPRESSION
    );
    if (status != Z_OK) throw std::runtime_error("zlib compression failed");
    compressed.resize(compressed_size);
    return "0" + base64_encode(compressed);
}

void copy_to_clipboard(const std::string& text) {
#ifdef _WIN32
    if (!OpenClipboard(nullptr)) throw std::runtime_error("could not open clipboard");
    struct ClipboardCloser { ~ClipboardCloser() { CloseClipboard(); } } closer;
    if (!EmptyClipboard()) throw std::runtime_error("could not clear clipboard");
    HGLOBAL memory = GlobalAlloc(GMEM_MOVEABLE, text.size() + 1);
    if (memory == nullptr) throw std::runtime_error("clipboard allocation failed");
    void* destination = GlobalLock(memory);
    std::memcpy(destination, text.c_str(), text.size() + 1);
    GlobalUnlock(memory);
    if (SetClipboardData(CF_TEXT, memory) == nullptr) {
        GlobalFree(memory);
        throw std::runtime_error("could not set clipboard data");
    }
#else
    (void)text;
    throw std::runtime_error("clipboard copying is currently implemented for Windows only");
#endif
}

}  // namespace factorio
