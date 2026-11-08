# fic2epub — personal AO3 to EPUB converter

A local-first web interface for the existing Tcl AO3 scraper and EPUB creator. The browser UI sends a work URL to a Python standard-library server, which validates the URL and runs the Tcl conversion adapter. The server binds to `127.0.0.1` only.

> Personal-use starter project. The conversion pipeline has not yet been end-to-end tested against a live AO3 work. Respect AO3's Terms of Service, robots/access controls, and rate limits. This tool does not attempt to bypass login or access restrictions.

## Project layout

```text
ao3-epub-converter/
├── backend/
│   ├── scraper/ao3.tsh          # Reconstructed from the supplied Tcl Wiki-formatted source
│   ├── epub/epubCreator.tsh     # Supplied epubCreator v0.5 script
│   ├── converter/into_epub.tcl  # Adapter that connects the two scripts
│   └── server.py                # Local HTTP server and download handling
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/test_url_validation.py
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Run locally with Docker

1. Install Docker Desktop.
2. Open a terminal in this project folder.
3. Build and start the app:

   ```bash
   docker compose up --build
   ```

4. Open <http://127.0.0.1:8000> in your browser.
5. Paste an AO3 work URL and select **Convert to EPUB**.
6. Stop the app with `Ctrl+C` in the terminal.

Docker installs Tcl, Tcllib, tDOM, Tcl TLS, `zip`, and ImageMagick for the existing scripts.

## Run without Docker

Requirements:

- Python 3.10 or newer
- Tcl 8.6
- Tcllib (`fileutil`, `base64`, and `textutil`)
- tDOM
- Tcl TLS
- `zip`
- ImageMagick if you want the original generator's automatic cover-image path

Then run:

```bash
python3 backend/server.py
```

Open <http://127.0.0.1:8000>.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The current tests cover AO3 URL validation only. They do not establish that the Tcl dependencies, AO3 scraper, or EPUB packaging work end-to-end on your computer.

## Notes on the supplied scripts

- `ao3.tsh` was supplied as Markdown-rendered Tcl Wiki text. The Markdown links/formatting were removed to reconstruct Tcl source. The obvious `valu22e` typo in its JSON helper was corrected, and the old forced TLS 1.0 setting was replaced with Tcl TLS's automatic server-name handling. The JSON helper is not used by this MVP.
- `epubCreator.tsh` is copied from the supplied `epubCreator v0.5` script. It retains its command-line interface and its own packaging logic.
- `into_epub.tcl` adapts the third supplied script to accept a work ID and an explicit output path, instead of writing to `~/FBooks`. It preserves the chapter extraction and HTML cleanup approach.
- Conversion downloads and temporary chapter files are kept in temporary directories. A generated EPUB is deleted after its one-time download or when the server stops.

## Privacy and scope

This server is intentionally restricted to localhost. Do not expose port 8000 to the public internet as-is. It has no authentication, persistent job queue, or public deployment hardening. The code is intended for personal use on your own computer.
