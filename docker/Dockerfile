# Hermes Pipeline Sandbox Container
FROM ubuntu:22.04

# Install essential tools
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Foundry
RUN curl -L https://foundry.paradigm.xyz | bash && \
    /root/.foundry/bin/foundryup

# Install solc-select
RUN pip3 install solc-select

# Add to PATH
ENV PATH="/root/.foundry/bin:/root/.local/bin:$PATH"

# Install default solc version
RUN solc-select install 0.8.20 && solc-select use 0.8.20

# Create workspace directories
RUN mkdir -p /workspace /invariants /datasets /artifacts

# Drop all capabilities by default
USER nobody

WORKDIR /workspace