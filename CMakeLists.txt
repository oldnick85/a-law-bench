cmake_minimum_required(VERSION 3.18)
project(ALawBench LANGUAGES CXX)

if(NOT DEFINED ALGORITHM_DIR)
    message(FATAL_ERROR "ALGORITHM_DIR must be set")
endif()

set(ALGORITHM_SOURCES
    src/algorithms/${ALGORITHM_DIR}/encoder.cpp
    src/algorithms/${ALGORITHM_DIR}/decoder.cpp
)

add_executable(
    bench 
    src/bench/main.cpp 
    ${ALGORITHM_SOURCES}
    )

target_include_directories(bench 
    PRIVATE src/algorithms/${ALGORITHM_DIR})

if(DEFINED ALGORITHM_NAME)
    target_compile_definitions(bench PRIVATE ALGORITHM_NAME="${ALGORITHM_NAME}")
endif()

set_target_properties(bench PROPERTIES
    CXX_STANDARD 23
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)