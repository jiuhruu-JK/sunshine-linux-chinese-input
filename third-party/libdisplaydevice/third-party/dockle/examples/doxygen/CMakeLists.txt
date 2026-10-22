cmake_minimum_required(VERSION 3.24)
project(dockle_doxygen_example LANGUAGES CXX)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../../cmake")
include(Dockle)

dockle_add_docs(docs CONFIG "${CMAKE_CURRENT_LIST_DIR}/../../dockle.toml"
                TARGETS doxygen)
