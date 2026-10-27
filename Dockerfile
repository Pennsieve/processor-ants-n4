# ANTs 2.6.5 (Apache-2.0), amd64. The image ships no Python, so a small
# Debian python3 is added for the wrapper and the bias-field check.
FROM antsx/ants:2.6.5

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install --no-cache-dir --break-system-packages nibabel==5.3.2 numpy==2.2.6 \
 && useradd --uid 1000 --create-home processor

WORKDIR /processor
COPY processor/ /processor/processor/
COPY VERSION /processor/VERSION
ENV PYTHONPATH="/processor" \
    PYTHONUNBUFFERED=1

# The platform runs the container as uid 1000; do the same locally.
USER 1000

ENTRYPOINT ["python3", "-m", "processor.entry"]
