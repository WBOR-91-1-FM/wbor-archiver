# wbor-archiver

24/7 audio logger that makes recordings of a broadcast on `n`-minute intervals. Each recording is named according to the time it began capturing (e.g., `WBOR-2025-02-14T00:35:01Z.mp3` - all in ISO 8601 UTC format). Gapless playback is possible such that two recordings can be concatenated with no discernable "change-over", allowing for the creation of arbitrarily-length recordings.

## System Architecture

Dedicated containers for each service. Compatible with both Docker and Podman (what we use).

* **Recording service (Python, FFmpeg):** Audio acquisition and segmenting. Files are named dynamically indicating timestamp covered. After a segment is done writing, it drops the file into a specified archive directory.
* **Archive watchdog (Python):** Organizes files into the appropriate subdirectory. Informs the backend that a new segment is ready for indexing.
* **Backend & API (Python, FastAPI, FFmpeg):** Serves recordings. Admin endpoints available to un-publish segments as needed. Depending on the request, will concatenate segments to produce a single, gapless recording.
* **Database (Postgres)**: Store segment index and metadata info.
* **Web interface (JavaScript, React):** User interface. A time-based availability heatmap is available to show, at a glance, where gaps in the archive exist.

![Archiver Workflow](diagrams/png/Archiver%20Workflow.png)

## Usage

First, set up your `.env`. Copy the `.env.example` file to `.env` and fill in the necessary values.

```bash
cp .env.example .env
```

Spin up services by running `make` (note: you may need to install `make`, `docker`, and/or `podman`).

```bash
make
```

**Starting & Building:** `make`
**Restarting:** `make restart`
**Stopping:** `make down`
**Logs:** `make logs`
**Cleanup:** `make clean`

**Note:** by default, the archive directory is `./archive`. As of now, to change this, edit the `docker-compose.yml` file (under the `volumes` section for `recording` and `archive-watchdog`).

## TO-DO

### Development Tasks

* [ ] Endpoints:
  * [ ] Listing recordings with metadata
  * [ ] Downloading recordings
  * [ ] Admin-only endpoints to "delete" (hide) specific recordings
* [ ] Logging for download statistics and API activity
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
