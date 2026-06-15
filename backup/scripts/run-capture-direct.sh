#!/bin/bash
cd /home/iots/.openclaw/workspace/iot-camera
export NODE_PATH=/home/iots/.openclaw/workspace/node_modules
node capture-cameras.js --cron
