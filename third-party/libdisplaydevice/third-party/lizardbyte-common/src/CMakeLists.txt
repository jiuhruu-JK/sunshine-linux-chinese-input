add_library(lizardbyte_common STATIC)
add_library(lizardbyte::common ALIAS lizardbyte_common)

target_sources(lizardbyte_common
               PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/common/env.cpp")

target_include_directories(
  lizardbyte_common PUBLIC $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/src/include>
                           $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

target_compile_features(lizardbyte_common PUBLIC cxx_std_17)
set_target_properties(
  lizardbyte_common PROPERTIES EXPORT_NAME common OUTPUT_NAME lizardbyte-common)

if(MSVC)
    target_compile_options(lizardbyte_common PRIVATE /W4)
    if(LIZARDBYTE_COMMON_WARNINGS_AS_ERRORS)
        target_compile_options(lizardbyte_common PRIVATE /WX)
    endif()
else()
    target_compile_options(lizardbyte_common PRIVATE -Wall -Wextra -Wpedantic)
    if(LIZARDBYTE_COMMON_WARNINGS_AS_ERRORS)
        target_compile_options(lizardbyte_common PRIVATE -Werror)
    endif()
endif()

if(LIZARDBYTE_COMMON_INSTALL)
    install(
      TARGETS lizardbyte_common
      EXPORT lizardbyte-common-targets
      ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
      LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
      RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")

    install(DIRECTORY "${PROJECT_SOURCE_DIR}/src/include/"
            DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}")

    install(
      EXPORT lizardbyte-common-targets
      NAMESPACE lizardbyte::
      DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/lizardbyte-common")
endif()
