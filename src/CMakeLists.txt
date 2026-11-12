cmake_minimum_required(VERSION 3.5)

if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
  set(CMAKE_TOOLCHAIN_FILE "$ENV{VITASDK}/share/vita.toolchain.cmake" CACHE PATH "toolchain")
endif()

project(bbpsx_hello C)
include("$ENV{VITASDK}/share/vita.cmake" REQUIRED)

set(VITA_APP_NAME "bloodbornePSX-V")
set(VITA_TITLEID  "BBPS00001")
set(VITA_VERSION  "01.09")

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -std=gnu17 -O2 -Wl,-q")

add_executable(bbpsx_hello main.c)

target_link_libraries(bbpsx_hello
 ScePower_stub
  SceAudio_stub
  vitaGL vitashark SceShaccCgExt mathneon taihen_stub stdc++
  SceShaccCg_stub SceKernelDmacMgr_stub
  SceGxm_stub SceDisplay_stub SceCtrl_stub SceTouch_stub
  SceAppMgr_stub SceCommonDialog_stub SceSysmodule_stub
  SceLibKernel_stub SceKernelThreadMgr_stub SceSysmem_stub
  m c
)

vita_create_self(bbpsx_hello.self bbpsx_hello UNSAFE)
vita_create_vpk(bbpsx_hello.vpk ${VITA_TITLEID} bbpsx_hello.self
  VERSION ${VITA_VERSION} NAME ${VITA_APP_NAME}
)
