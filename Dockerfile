FROM fedora:latest

RUN sudo dnf install -y ffmpeg-free

WORKDIR /archiver

COPY archive-driver.sh .

CMD ["bash", "archive-driver.sh"]
