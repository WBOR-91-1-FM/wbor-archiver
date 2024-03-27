# TO-DO:
* There is an opportunity to write metadata from the stream to the .mp3, though it would likely need to be a separate process
* Micro gaps between recordings, so no seamless playback... not sure how to fix
* Auto prune recordings older than six months

# Development
Build: `podman build -t archiver .`
Run image: `podman run -d --name archiver -v /archive:/archive --restart=always archiver`
