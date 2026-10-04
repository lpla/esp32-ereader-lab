FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 dosfstools mtools libpixman-1-0 libsdl2-2.0-0 libslirp0 gdb-multiarch binutils-riscv64-linux-gnu \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
