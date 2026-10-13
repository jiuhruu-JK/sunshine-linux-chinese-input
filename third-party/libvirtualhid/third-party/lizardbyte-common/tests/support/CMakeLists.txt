add_library(lizardbyte_common_test_support STATIC)
add_library(lizardbyte::test_support ALIAS lizardbyte_common_test_support)

target_sources(lizardbyte_common_test_support
               PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/testing.cpp")

target_include_directories(
  lizardbyte_common_test_support
  PUBLIC $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/tests/support/include>)

target_link_libraries(lizardbyte_common_test_support PUBLIC gtest
                                                            lizardbyte::common)

target_compile_features(lizardbyte_common_test_support PUBLIC cxx_std_17)
set_target_properties(lizardbyte_common_test_support
                      PROPERTIES OUTPUT_NAME lizardbyte-common-test-support)

if(MSVC)
    target_compile_options(lizardbyte_common_test_support PRIVATE /W4)
    if(LIZARDBYTE_COMMON_WARNINGS_AS_ERRORS)
        target_compile_options(lizardbyte_common_test_support PRIVATE /WX)
    endif()
else()
    target_compile_options(lizardbyte_common_test_support PRIVATE -Wall -Wextra
                                                                  -Wpedantic)
    if(LIZARDBYTE_COMMON_WARNINGS_AS_ERRORS)
        target_compile_options(lizardbyte_common_test_support PRIVATE -Werror)
    endif()
endif()
