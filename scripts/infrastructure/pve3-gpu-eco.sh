#!/bin/bash
set -e
echo auto > /sys/class/drm/card0/device/power_dpm_force_performance_level
echo "GPU PVE3: ECO (auto-scaling)"
