# wbor-archiver

24/7 audio logger that makes recordings of a broadcast on `n`-minute intervals. Gapless playback is possible such that many recordings can be seamlessly concatenated, allowing for the creation of arbitrary-length recordings.

## System Architecture

Dedicated containers for each service. Compatible with both Docker and Podman (what we use).

* **Recording service (Python, FFmpeg):** Audio acquisition and segmenting. Files are named dynamically indicating timestamp covered (e.g., `WBOR-2025-02-14T00:35:01Z.mp3` - all in ISO 8601 UTC format). Segments are written to a specified archive directory.
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

## Developing

Install the pre-commit hooks to ensure that code is formatted correctly before committing. This will help maintain a clean codebase.

```bash
pip install pre-commit
pre-commit install
```

You can run the pre-commit hooks manually to check for any issues:

```bash
pre-commit run --all-files
```

## TO-DO

### Development Tasks

* [ ] Endpoints:
  * [ ] Listing recordings with metadata
  * [ ] Downloading recordings
  * [ ] Admin-only endpoints to "delete" (hide) specific recordings
* [ ] Cleanup process that runs periodically to rename any `.temp` files that are older than a certain threshold (e.g. 1 hour) to `.mp3` files.
* [ ] Logging for download statistics and API activity
* [x] Secure admin API endpoints
* [ ] Build basic navigation UI:
  * [ ] Date-based filtering (calendar picker)
* [ ] Add admin panel to manage recordings (delete/hide feature)
* [ ] Test for mobile responsiveness

### Deployment

* [x] Configure proxy for `https://archive.wbor.bowdoin.edu`.
* [ ] Deploy

### Monitoring & Alarms

* [ ] Implement monitoring dashboard or simple status page
* [ ] Set up real-time alerts for:
  * [ ] API downtime
  * [ ] Recording agent is not making recordings
