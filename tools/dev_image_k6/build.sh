#!/bin/sh
set -e
docker build -f Dockerfile -t ghcr.io/inti-cmnb/kicad6_auto:dev .
TG1=`docker run --rm ghcr.io/inti-cmnb/kicad6_auto:dev kibot --version | sed 's/.* \([0-9]\+\.[0-9]\+\.[0-9]\+\) .*/\1/' | tr -d '\n'`
HASH=`git log --pretty=format:%h -1 | tr -d '\n'`
TG2=k`docker run --rm ghcr.io/inti-cmnb/kicad6_auto:dev kicad_version.py`
TG3=d`docker run --rm ghcr.io/inti-cmnb/kicad6_auto:dev cat /etc/debian_version | tr -d '\n'`
docker tag ghcr.io/inti-cmnb/kicad6_auto:dev ghcr.io/inti-cmnb/kicad6_auto:dev_${TG1}-${HASH}_${TG2}_${TG3}
docker tag ghcr.io/inti-cmnb/kicad6_auto:dev ghcr.io/inti-cmnb/kicad_auto:dev_k6_${TG1}-${HASH}_${TG2}_${TG3}
docker tag ghcr.io/inti-cmnb/kicad6_auto:dev ghcr.io/inti-cmnb/kicad_auto:dev_k6
docker push ghcr.io/inti-cmnb/kicad6_auto:dev_${TG1}-${HASH}_${TG2}_${TG3}
docker push ghcr.io/inti-cmnb/kicad_auto:dev_k6_${TG1}-${HASH}_${TG2}_${TG3}
docker push ghcr.io/inti-cmnb/kicad_auto:dev_k6
docker push ghcr.io/inti-cmnb/kicad6_auto:dev
