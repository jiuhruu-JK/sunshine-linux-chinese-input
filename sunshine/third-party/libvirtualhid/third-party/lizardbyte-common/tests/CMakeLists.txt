include(GoogleTest)

set(TEST_BINARY test_lizardbyte_common)

add_executable(
  ${TEST_BINARY} "${CMAKE_CURRENT_SOURCE_DIR}/cpp/test_env.cpp"
                 "${CMAKE_CURRENT_SOURCE_DIR}/cpp/test_testing.cpp")

target_link_libraries(${TEST_BINARY} PRIVATE gmock_main lizardbyte::common
                                             lizardbyte::test_support)

gtest_discover_tests(${TEST_BINARY})
