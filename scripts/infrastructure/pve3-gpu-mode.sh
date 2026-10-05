#!/bin/bash
set -e
printf "GPU Mode: "
cat /sys/class/drm/card0/device/power_dpm_force_performance_level
printf "Clock: "
grep "*" /sys/class/drm/card0/device/pp_dpm_sclk || true
