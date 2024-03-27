FROM fedora:latest

RUN sudo dnf install ffmpeg-free

WORKDIR /archiver

COPY driver.sh .

CMD ["bash", "driver.sh"]
