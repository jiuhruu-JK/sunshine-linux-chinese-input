cmake_minimum_required(VERSION 3.16)
project(sunshine-input-mvp CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release)
include(GNUInstallDirs)

find_package(Fcitx5Core REQUIRED)

# ---------- 注入扩展（fcitx5 addon，so） ----------
# 安装到 $libdir/fcitx5/（与本机 fcitx5 5.1.19 的 addon 目录布局一致）
add_library(sunshineinput MODULE src/sunshineinput.cpp)
set_target_properties(sunshineinput PROPERTIES PREFIX "lib")
target_link_libraries(sunshineinput Fcitx5::Core)
target_compile_options(sunshineinput PRIVATE -Wall -Wextra)

# ---------- 测试客户端（CLI） ----------
add_executable(sunshine-input-test src/client.cpp)

install(TARGETS sunshineinput sunshine-input-test
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}/fcitx5
        RUNTIME DESTINATION bin)
install(FILES sunshineinput.conf DESTINATION ${CMAKE_INSTALL_DATADIR}/fcitx5/addon)
