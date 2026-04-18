FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y \
    curl git git-lfs wget ca-certificates build-essential \
    cmake ninja-build python3-dev \
    libgl1-mesa-glx libosmesa6-dev libglu1-mesa-dev libglib2.0-0 libgomp1 \
    libxi-dev libxrandr-dev libxinerama-dev libxcursor-dev \
    libfontconfig1 libxrender1 libice6 libsm6 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /workspace
COPY . .

# Install all deps (including local editable packages: verifier-core, mech-verifier, etc.)
RUN uv sync --no-dev

# Open3D — built headless (OSMesa) after uv so install-pip-package uses same Python
RUN git clone https://github.com/isl-org/Open3D.git /tmp/Open3D \
    && cd /tmp/Open3D \
    && git checkout 8e434558a9b1ecacba7854da7601a07e8bdceb26 \
    && mkdir build && cd build \
    && cmake -DENABLE_HEADLESS_RENDERING=ON -DBUILD_GUI=OFF \
             -DUSE_SYSTEM_GLEW=OFF -DUSE_SYSTEM_GLFW=OFF \
             -DPYTHON_EXECUTABLE=$(python3 -c "import sys; print(sys.executable)") .. \
    && make -j$(nproc) && make install-pip-package \
    && rm -rf /tmp/Open3D

# Node.js 20 + Claude Code
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

ENV NPM_CONFIG_PREFIX=/npm-global
ENV PATH="/npm-global/bin:$PATH"

RUN npm install -g @anthropic-ai/claude-code

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["claude", "--dangerously-skip-permissions"]