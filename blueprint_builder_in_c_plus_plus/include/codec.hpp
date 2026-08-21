#pragma once

#include <string>

namespace factorio {

[[nodiscard]] std::string encode_blueprint(const std::string& json);
void copy_to_clipboard(const std::string& text);

}  // namespace factorio
