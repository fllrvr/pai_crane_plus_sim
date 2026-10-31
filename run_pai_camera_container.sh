#!/bin/bash
# Start a container from the image built with: docker build -t pai-ros2-camera docker/
# The repository folder (where this script is) is mounted as /workspace.
docker run -d --name pai_ros2_camera \
-p 6080:80 --shm-size=512m \
-p 9090:9090 -p 9876:9876 \
-v "$(cd "$(dirname "$0")" && pwd)":/workspace \
pai-ros2-camera
