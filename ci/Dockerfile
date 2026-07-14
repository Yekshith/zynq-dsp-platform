FROM ghdl/ghdl:ubuntu22-llvm-11

RUN apt-get update && \
	apt-get install -y --no-install-recommends \
		python3 \
		python3-dev \
		python3.10-dev \
		libpython3.10-dev \
		python3-pip \
		make \
		git && \
	rm -rf /var/lib/apt/lists/*

RUN test -f /usr/lib/x86_64-linux-gnu/libpython3.10.so.1.0

ENV LIBPYTHON_LOC=/usr/lib/x86_64-linux-gnu/libpython3.10.so.1.0

RUN pip3 install --no-cache-dir \
	cocotb==1.9.2 \
	vunit_hdl \
	pytest \
	numpy \
	scipy

WORKDIR /work