FROM debian:stretch as builder

RUN apt-get update && \
    apt-get upgrade -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gcc \
        make \
        pkg-config \
        ca-certificates \
        curl \
        libcurl4-openssl-dev \
        libc-ares-dev \
        libssl-dev \
        libtre-dev \
        libpcre2-dev \
    && \
    rm -rf /var/lib/apt/lists/*
RUN curl -L https://github.com/unrealircd/unrealircd/archive/377fa252448f8b0e4271b0013ad4ff866e628677.tar.gz | tar -xz
WORKDIR /unrealircd-377fa252448f8b0e4271b0013ad4ff866e628677
# Add fix for PROXY module
RUN curl -L https://www.unrealircd.org/downloads/webirc.c -o src/modules/webirc.c
RUN sed -i -e 's|$(INSTALL) -m 0700|$(INSTALL) -m 0755|g' -e 's|$(INSTALL) -m 0600|$(INSTALL) -m 0644|g' Makefile.in
RUN ./configure \
    --with-pidfile=/run/unrealircd/ircd.pid \
    --with-showlistmodes \
    --enable-ssl=/usr \
    --with-bindir=/usr/bin \
    --with-datadir=/var/lib/unrealircd \
    --with-confdir=/etc/unrealircd \
    --with-modulesdir=/usr/lib/x86_64-linux-gnu/unrealircd \
    --with-logdir=/var/log/unrealircd \
    --with-cachedir=/var/cache/unrealircd \
    --with-docdir=/usr/share/doc/unrealircd \
    --with-tmpdir=/tmp \
    --with-scriptdir=/usr \
    --with-nick-history=2000 \
    --with-sendq=3000000 \
    --with-permissions=0644 \
    --with-fd-setsize=1024 \
    --enable-dynamic-linking \
    && make

FROM debian:stretch
COPY --from=builder /unrealircd-377fa252448f8b0e4271b0013ad4ff866e628677 /unrealircd
RUN apt-get update && \
    apt-get upgrade -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        libcurl3 \
        libc-ares2 \
        libssl1.1 \
        libtre5 \
        libpcre2-8-0 \
        make \
    && \
    make -C /unrealircd install && \
    install /unrealircd/extras/argon2/lib/libargon2.so.1 /usr/lib/x86_64-linux-gnu && \
    rm -rf /unrealircd && \
    mv /usr/unrealircd /etc/unrealircd/unrealircd && \
    chmod 1777 /tmp && \
    mkdir /run/unrealircd && \
    chown irc: /run/unrealircd /etc/unrealircd /var/cache/unrealircd /var/log/unrealircd /var/lib/unrealircd && \
    apt-get remove -y make && \
    rm -rf /var/lib/apt/lists/*
USER irc

EXPOSE 6697 7000 6800

CMD ["/usr/bin/unrealircd", "-F"]
