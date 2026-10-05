#!/bin/bash
set -e
echo high > /sys/class/drm/card0/device/power_dpm_force_performance_level
echo "GPU PVE3: TURBO (2900MHz / high)"
