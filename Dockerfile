FROM fedora:latest

RUN sudo dnf install ffmpeg

WORKDIR /archiver

COPY driver.sh .

CMD ["bash", "driver.sh"]
