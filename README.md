# wbor-archiver

24/7 logger that makes recordings of a broadcast on n-minute intervals. Each recording is named according to the time it began capturing (e.g., `2025-02-11_13-05-00.mp3`). Gapless playback is possible such that two recordings can be concatenated and there be no discernable "change-over", allowing for the creation of arbitrarily long recordings.

## System Architecture

Dedicated containers for each service done via Docker/Podman.

* Recording service (`ffmpeg` for capture)
* Web interface
  * Date-based filtering and basic search
* API (FastAPI) to serve recordings/downloads, with admin endpoints to "delete" specific recordings
  * Logging for statistics

## TO-DO

### Phase 1: Daemon (24/7 Logger)

* [ ] **Set Up Recording Service Container**
  * [x] Create Dockerfile for the recording service.
  * [x] Implement continuous recording logic using `ffmpeg`.
  * [x] Implement error handling for recording failures.
  * [x] Develop a watchdog script to monitor the recording service.
  * [ ] Trigger an alarm (email, Slack webhook, etc.) if recordings are not being generated.

* [ ] **Storage Structure Implementation**
  * [ ] Create logic to organize recordings into the specified directory hierarchy.
  * [ ] Generate basic `.meta.json` files with timestamp info (placeholders for now).

* [ ] **Deployment**
  * [ ] Build and run the container using Podman.
  * [ ] Configure automatic restart on failure (`--restart=always`).
  * [ ] Set up logging for recording service errors and status.

### Phase 2

#### API Development (FastAPI)

* [ ] Set up FastAPI container for serving recordings.

* [ ] Implement endpoints for:
  * [ ] Listing recordings with metadata.
  * [ ] Downloading recordings.
  * [ ] Admin-only endpoints to "delete" (hide) specific recordings.
* [ ] Add logging for download statistics and API activity.

#### Web Interface (React)

* [ ] Initialize React project optimized for mobile.

* [ ] Build basic navigation UI:
  * [ ] Date-based filtering (calendar picker).
  * [ ] Basic search functionality (by date, show name if metadata exists).
* [ ] Integrate with FastAPI for dynamic content.
* [ ] Add admin panel to manage recordings (delete/hide feature).
* [ ] Test for mobile responsiveness.

#### Metadata Enrichment

* [ ] Design metadata format for `.meta.json` (shows, DJs, songs).

* [ ] Implement optional Spinitron API integration to enrich metadata.
* [ ] Automate metadata generation post-recording (if feasible).

### Networking & Security

* [ ] Configure reverse proxy (NGINX or Caddy) for `https://archive.wbor.org`.

* [ ] Restrict access to on-campus IP ranges.
* [ ] Secure admin API endpoints (simple key-based auth or IP whitelisting).

### Monitoring & Alarms

* [ ] Implement monitoring dashboard or simple status page.

* [ ] Set up real-time alerts for:
  * [ ] Failed recordings.
  * [ ] API downtime.

## Bugs

## Development

Build: `podman build -t wbor-archiver .`
Run image: `podman run -d --name wbor-archiver -v /archive:/archive --restart=always wbor-archiver`
