include_guard(GLOBAL)

include(CMakeParseArguments)

# Resolve the Dockle command for the calling scope.
function(_dockle_resolve_command package_directory python_path)
    if(DOCKLE_EXECUTABLE)
        set(dockle_command "${DOCKLE_EXECUTABLE}")
    elseif(EXISTS "${package_directory}/__init__.py")
        # Run the implementation adjacent to this module so a source-submodule
        # integration cannot silently use a different globally installed Dockle
        # revision.
        find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)
        set(dockle_command
            "${CMAKE_COMMAND}" -E env "PYTHONPATH=${python_path}"
            "${Python3_EXECUTABLE}" -m dockle)
    else()
        find_program(dockle_program NAMES dockle dockle.exe)
        if(dockle_program)
            set(dockle_command "${dockle_program}")
        else()
            find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)
            set(dockle_command "${Python3_EXECUTABLE}" -m dockle)
        endif()
    endif()
    set(dockle_command
        "${dockle_command}"
        PARENT_SCOPE)
endfunction()

# Create a target that builds documentation through Dockle.
#
# dockle_add_docs(<target> [ALL] [CONFIG <dockle.toml>] [WORKING_DIRECTORY
# <directory>] [TARGETS <dockle-target>...])
#
# The module first looks for the dockle console command. If it is not installed,
# it falls back to Python3 -m dockle. Set DOCKLE_EXECUTABLE before including
# this module to select a standalone Dockle executable.
function(dockle_add_docs target)
    # Add a build target that invokes Dockle's canonical command-line interface.
    set(options ALL)
    set(one_value_args CONFIG WORKING_DIRECTORY)
    set(multi_value_args TARGETS)
    cmake_parse_arguments(DOCKLE "${options}" "${one_value_args}"
                          "${multi_value_args}" ${ARGN})

    if(DOCKLE_UNPARSED_ARGUMENTS)
        message(
            FATAL_ERROR
                "Unknown dockle_add_docs arguments: ${DOCKLE_UNPARSED_ARGUMENTS}"
        )
    endif()

    set(dockle_config "${DOCKLE_CONFIG}")
    if(NOT dockle_config)
        set(dockle_config "${CMAKE_SOURCE_DIR}/dockle.toml")
    elseif(NOT IS_ABSOLUTE "${dockle_config}")
        get_filename_component(dockle_config "${dockle_config}" ABSOLUTE
                               BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
    endif()

    if(NOT EXISTS "${dockle_config}")
        message(FATAL_ERROR "Dockle configuration not found: ${dockle_config}")
    endif()

    if(NOT DOCKLE_WORKING_DIRECTORY)
        get_filename_component(dockle_working_directory "${dockle_config}"
                               DIRECTORY)
    else()
        set(dockle_working_directory "${DOCKLE_WORKING_DIRECTORY}")
    endif()

    get_filename_component(dockle_package_directory "${CMAKE_CURRENT_LIST_DIR}"
                           DIRECTORY)
    get_filename_component(dockle_python_path "${dockle_package_directory}"
                           DIRECTORY)
    _dockle_resolve_command("${dockle_package_directory}"
                            "${dockle_python_path}")

    set(dockle_arguments --config "${dockle_config}" build)
    list(APPEND dockle_arguments ${DOCKLE_TARGETS})

    if(DOCKLE_ALL)
        add_custom_target(
            "${target}" ALL
            COMMAND ${dockle_command} ${dockle_arguments}
            WORKING_DIRECTORY "${dockle_working_directory}"
            COMMENT "Building documentation with Dockle"
            USES_TERMINAL VERBATIM)
    else()
        add_custom_target(
            "${target}"
            COMMAND ${dockle_command} ${dockle_arguments}
            WORKING_DIRECTORY "${dockle_working_directory}"
            COMMENT "Building documentation with Dockle"
            USES_TERMINAL VERBATIM)
    endif()
endfunction()
