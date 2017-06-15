FROM cassandra:2.2

# Add Containerpilot and set its configuration
ENV CONTAINERPILOT_VERSION 2.7.3
ENV CONTAINERPILOT file:///etc/containerpilot.json

RUN apt-get -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --force-yes wget curl dnsutils && \
    wget -O /etc/cassandra/jmx_prometheus_javaagent-0.5.jar https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.5/jmx_prometheus_javaagent-0.5.jar && \
    wget -O /etc/cassandra/jmx_exporter.yml https://raw.githubusercontent.com/prometheus/jmx_exporter/master/example_configs/cassandra.yml && \
    echo 'JVM_OPTS="$JVM_OPTS -javaagent:'/etc/cassandra/jmx_prometheus_javaagent-0.5.jar=7070:/etc/cassandra/jmx_exporter.yml'"' >> /etc/cassandra/cassandra-env.sh

RUN export CONTAINERPILOT_CHECKSUM=2511fdfed9c6826481a9048e8d34158e1d7728bf \
    && export archive=containerpilot-${CONTAINERPILOT_VERSION}.tar.gz \
    && curl -Lso /tmp/${archive} \
         "https://github.com/joyent/containerpilot/releases/download/${CONTAINERPILOT_VERSION}/${archive}" \
    && echo "${CONTAINERPILOT_CHECKSUM}  /tmp/${archive}" | sha1sum -c \
    && tar zxf /tmp/${archive} -C /usr/local/bin \
    && rm /tmp/${archive}

RUN curl -Lvo get-pip.py https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py && \
    pip install \
    python-Consul==0.4.7 \
    pyyaml==3.12 \
    mock==2.0.0

COPY etc/containerpilot.json etc/
# COPY bin/* /usr/local/bin/
COPY bin/manager /usr/local/bin/manager
COPY bin/manage.py /usr/local/bin/manage.py


HEALTHCHECK --interval=30s --timeout=20s --retries=10 CMD python /usr/local/bin/manage.py basic_health

ENTRYPOINT ["/usr/local/bin/containerpilot" ]
CMD ["cassandra", "-f"]
