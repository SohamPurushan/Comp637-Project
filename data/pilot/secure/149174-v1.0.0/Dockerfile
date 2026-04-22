FROM gcc:11.2.0
LABEL maintainer="SAMATE, NIST"
WORKDIR /sard
RUN apt-get update && apt-get install -y --no-install-recommends make
RUN git clone --depth 1 https://github.com/boutell/cgic.git /tmp/cgic
RUN make -C /tmp/cgic all install
RUN rm -r /tmp/cgic
COPY . .
