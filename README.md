# wbor-archiver

24/7 logger that makes recordings of a broadcast on `n`-minute intervals. Each recording is named according to the time it began capturing (e.g., `WBOR-2025-02-14T00:35:01Z.mp3` - all in ISO 8601 UTC format). Gapless playback is possible such that two recordings can be concatenated and there be no discernable "change-over", allowing for the creation of arbitrarily long recordings.

## System Architecture

Dedicated containers for each service. Written in Docker but compatible with Podman.

* Recording service (Python, FFmpeg). Handles audio segment acquisition, dropping files into a specified archive directory.
* Archive watchdog (Python). After the recording service finishes writing to a segment, the watchdog organizes the file into the appropriate subdirectory. The watchdog then informs the backend that a new segment is ready.
* Backend & API (Python, FastAPI, FFmpeg) to serve final recordings. Admin endpoints are available to un-publish segments as needed. Depending on the request, concatenate segments to produce a single, gapless recording.
* Web interface (JavaScript, React). Primary means of downloading from the archive. A time-based availability heatmap will be available to show, at a glance, where gaps in the archive exist.

## TO-DO

### Development Tasks

* [ ] Makefile
* [x] Implement continuous recording logic using `ffmpeg`
* [ ] Set up FastAPI container for serving recordings
* [ ] Implement endpoints for:
  * [ ] Listing recordings with metadata
  * [ ] Downloading recordings
  * [ ] Admin-only endpoints to "delete" (hide) specific recordings
* [ ] Add logging for download statistics and API activity
* [ ] Secure admin API endpoints (simple key-based auth or IP whitelisting)
* [ ] Initialize React project optimized for mobile
* [ ] Build basic navigation UI:
  * [ ] Date-based filtering (calendar picker)
* [ ] Integrate with FastAPI for dynamic content
* [ ] Add admin panel to manage recordings (delete/hide feature)
* [ ] Test for mobile responsiveness

### Deployment

* [ ] Configure reverse proxy (NGINX or Caddy) for `https://archive.wbor.org`.

### Monitoring & Alarms

* [ ] Implement monitoring dashboard or simple status page
* [ ] Set up real-time alerts for:
  * [ ] API downtime
  * [ ] Recording agent is not making recordings

## Bugs

## Development

Build: `podman build -t wbor-archiver .`
Run image: `podman run -d --name wbor-archiver -v /archive:/archive --restart=always wbor-archiver`
