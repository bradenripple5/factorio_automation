# CMake generated Testfile for 
# Source directory: C:/Users/brade.DESKTOP-E538E75/gitrepos/factorio_software_automation/blueprint_builder_in_c_plus_plus
# Build directory: C:/Users/brade.DESKTOP-E538E75/gitrepos/factorio_software_automation/blueprint_builder_in_c_plus_plus/build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test([=[solar_20x10]=] "C:/Users/brade.DESKTOP-E538E75/gitrepos/factorio_software_automation/blueprint_builder_in_c_plus_plus/build/blueprint_builder.exe" "solar" "20" "10" "--no-clipboard")
set_tests_properties([=[solar_20x10]=] PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/brade.DESKTOP-E538E75/gitrepos/factorio_software_automation/blueprint_builder_in_c_plus_plus/CMakeLists.txt;31;add_test;C:/Users/brade.DESKTOP-E538E75/gitrepos/factorio_software_automation/blueprint_builder_in_c_plus_plus/CMakeLists.txt;0;")
add_test([=[station_defaults]=] "C:/Users/brade.DESKTOP-E538E75/gitrepos/factorio_software_automation/blueprint_builder_in_c_plus_plus/build/blueprint_builder.exe" "station-plan" "advanced-circuit" "copper-cable")
set_tests_properties([=[station_defaults]=] PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/brade.DESKTOP-E538E75/gitrepos/factorio_software_automation/blueprint_builder_in_c_plus_plus/CMakeLists.txt;32;add_test;C:/Users/brade.DESKTOP-E538E75/gitrepos/factorio_software_automation/blueprint_builder_in_c_plus_plus/CMakeLists.txt;0;")
