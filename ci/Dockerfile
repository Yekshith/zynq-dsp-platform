FROM ghdl/ghdl:ubuntu22-llvm-11
RUN apt-get update && \
	apt-get install -y --no-install-recommends \
	python3 \
	python3-pip \
	make \
	git && \
	rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir \
	cocotb==1.9.2 \
	vunit_hdl \
	pytest \
	numpy \
	scipy
WORKDIR /work
