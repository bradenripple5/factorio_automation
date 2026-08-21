#include "codec.hpp"
#include "solar.hpp"
#include "station.hpp"

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void usage() {
    std::cout
        << "Factorio blueprint builder (C++)\n\n"
        << "Usage:\n"
        << "  blueprint_builder solar COLUMNS ROWS [--json] [--no-clipboard]\n"
        << "  blueprint_builder station-plan PRODUCT... [--trains N]\n";
}
}  // namespace

int main(const int argc, char** argv) {
    try {
        if (argc < 2) { usage(); return 1; }
        const std::string mode = argv[1];
        if (mode == "solar") {
            if (argc < 4) { usage(); return 1; }
            const int columns = std::stoi(argv[2]);
            const int rows = std::stoi(argv[3]);
            bool json_only = false;
            bool clipboard = true;
            for (int index = 4; index < argc; ++index) {
                const std::string option = argv[index];
                if (option == "--json") json_only = true;
                else if (option == "--no-clipboard") clipboard = false;
                else throw std::invalid_argument("unknown option: " + option);
            }
            const auto blueprint = factorio::make_solar_array(columns, rows);
            const auto stats = factorio::solar_stats(columns, rows);
            const auto json = blueprint.to_json();
            if (json_only) {
                std::cout << json << '\n';
                return 0;
            }
            const auto encoded = factorio::encode_blueprint(json);
            if (clipboard) factorio::copy_to_clipboard(encoded);
            std::cout << stats.solar_panels << " solar panels, " << stats.substations
                      << " substations, " << std::fixed << std::setprecision(2)
                      << stats.peak_output_mw << " MW peak output\n"
                      << encoded << '\n';
            return 0;
        }
        if (mode == "station-plan") {
            std::vector<std::string> products;
            unsigned trains = 1;
            for (int index = 2; index < argc; ++index) {
                const std::string value = argv[index];
                if (value == "--trains") {
                    if (++index >= argc) throw std::invalid_argument("--trains needs a value");
                    trains = static_cast<unsigned>(std::stoul(argv[index]));
                } else {
                    products.push_back(value);
                }
            }
            const auto stations = factorio::build_station_tree(products, {}, trains);
            for (const auto& station : stations) {
                std::cout << station.id << " product=" << station.product
                          << " trains=" << station.trains_per_station << '\n';
            }
            return 0;
        }
        usage();
        return 1;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 2;
    }
}
