# CRANE+ V2 simulation with a camera, for data collection / training / inference with LeRobot.
#
# Base: the "AI Robot Book" image (ROS 2 Humble, Gazebo, MoveIt, noVNC desktop, book samples in ~/airobot_ws).
# Added: upstream rt-net/crane_plus (which has the Gazebo camera) in ~/crane_plus_ws, with our camera position.
#
# Build (from the repository root):
#   docker build -t pai-ros2-camera docker/
#
# See docs/dockerfile_plan.md for the design.

# Pinned by digest so that everyone builds on the same base image
FROM airobotbook/ros2-desktop-ai-robot-book-humble@sha256:b58ec74c019aacd9ce4818fa25fc5a9e0a1f22f8c9cd1f5260994bf15cd9eb63

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG ROS_DISTRO=humble
# Upstream commit that added the camera to the Gazebo environment ("Gazebo環境にカメラを追加 (#83) (#84)")
ARG CRANE_PLUS_COMMIT=87486bb
ARG USER_NAME=ubuntu
ENV CRANE_PLUS_WS=/home/${USER_NAME}/crane_plus_ws

# 1. Upstream crane_plus at a fixed commit, with our camera position applied
USER ${USER_NAME}
COPY --chown=${USER_NAME}:${USER_NAME} camera_position.patch /tmp/camera_position.patch
RUN mkdir -p ${CRANE_PLUS_WS}/src \
    && git clone https://github.com/rt-net/crane_plus.git ${CRANE_PLUS_WS}/src/crane_plus \
    && cd ${CRANE_PLUS_WS}/src/crane_plus \
    && git checkout ${CRANE_PLUS_COMMIT} \
    && git apply /tmp/camera_position.patch \
    && rm /tmp/camera_position.patch

# 2. System dependencies of crane_plus (the ubuntu user has no passwordless sudo, so run as root)
#    The ROS apt key in the base image has expired (EXPKEYSIG F42ED6FBAB17C654), so fetch the renewed one
#    to the path the base image's /etc/apt/sources.list.d/ros2.list refers to.
USER root
RUN curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && apt-get update \
    && rosdep update --rosdistro ${ROS_DISTRO} \
    && rosdep install -r -y -i --rosdistro ${ROS_DISTRO} --from-paths ${CRANE_PLUS_WS}/src \
    && rm -rf /var/lib/apt/lists/*

# 3. Build on top of ~/airobot_ws (same underlay as at runtime)
USER ${USER_NAME}
RUN cd ${CRANE_PLUS_WS} \
    && source /opt/ros/${ROS_DISTRO}/setup.bash \
    && source /home/${USER_NAME}/airobot_ws/install/setup.bash \
    && colcon build --symlink-install --packages-up-to crane_plus_gazebo crane_plus_examples

# 4. Load the workspaces in every terminal, after ~/airobot_ws (already sourced in ~/.bashrc).
#    local_setup.bash is used so that ~/airobot_ws (with the book's fork of crane_plus) is not re-sourced on top.
#    /workspace/pai_ws is created after the container starts (see docker/README.md), hence the existence check.
RUN { \
        echo ''; \
        echo '# Upstream crane_plus with the camera (overrides the fork in ~/airobot_ws)'; \
        echo "source ${CRANE_PLUS_WS}/install/local_setup.bash"; \
        echo '# physicalai_teleop, cloned into /workspace/pai_ws after the container starts'; \
        echo '[ -f /workspace/pai_ws/install/local_setup.bash ] && source /workspace/pai_ws/install/local_setup.bash'; \
    } >> /home/${USER_NAME}/.bashrc

# The base image's entrypoint runs as root and starts the desktop as the ubuntu user
USER root
