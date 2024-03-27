FROM fedora:latest

RUN sudo dnf install -y ffmpeg-free

WORKDIR /archiver

COPY driver.sh .

CMD ["bash", "driver.sh"]
