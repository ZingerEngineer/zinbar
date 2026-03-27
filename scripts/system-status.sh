#!/usr/bin/env bash

bat=$(cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1 || echo '--')

v=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null)
vol=$(echo "$v" | awk '{printf "%d", $2 * 100}')
echo "$v" | grep -q MUTED && icon="󰝟" || icon="󰕾"

echo "${icon} ${vol}%  󰁹 ${bat}%  󰅀"
