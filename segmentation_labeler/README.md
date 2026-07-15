# Segmentation Labeler

Segmentation Labeler is a local, desktop-first web application for manually creating
class-indexed semantic segmentation masks for two-dimensional images. It combines a FastAPI
and SQLite backend with a React/TypeScript and Konva canvas. Images never need to leave the
machine running the application, and no GPU or model checkpoint is used.

## Operating assumptions

- The backend and browser run for one trusted user on the same computer or HPC login node.
- Only de-identified images should be used.
- The server binds to `127.0.0.1` by default. For a remote HPC host, use SSH port forwarding;
  do not expose the application directly to an untrusted network.
- The application is intended for current desktop Chrome, Firefox, or Edge. Mobile annotation
  is not supported, and the UI warns when the window is too small.

## Architecture and project storage

The backend owns all filesystem access and validation. A small registry under
`~/.segmentation_labeler/registry.sqlite` remembers recently opened projects. Every annotation
project is otherwise self-contained:

```text
chosen-project-directory/
├── project.sqlite       # project, class, image, status, and resume metadata
├── project.json         # readable project pointer
├── images/              # private normalized PNG display copies
├── masks/               # atomic uint16 NumPy working masks
└── exports/             # default export parent
```

SQLite stores structured metadata, while images and masks remain files. Mask saves and export
files use a temporary file followed by an atomic rename. Uploaded names are treated only as
metadata; generated UUIDs address images internally. An explicitly entered local import or
export path is the only way the backend accesses a location outside a project.

The frontend keeps up to 30 undo states for the current image and sends the complete validated
mask to the backend after every logical edit. Undo history is intentionally temporary and does
not survive reopening, but the latest mask always does.

## Prerequisites and installation

The recommended installation uses `uv`, which installs dependencies in the project directory
without administrator rights. Requirements are Python 3.11 or newer, `uv`, Node.js 20 or newer,
and npm.

From this `segmentation_labeler/` directory:

```bash
uv sync --dev
npm --prefix frontend install
```

No system packages, CUDA libraries, GPU, external service, or secret are required.

## Starting the application

For normal local use, build the frontend and start one server:

```bash
make run
```

Then open <http://127.0.0.1:8000>. The command rebuilds the production frontend before starting
FastAPI. An equivalent command with a different port is:

```bash
npm --prefix frontend run build
uv run segmentation-labeler --port 8010
```

For development with automatic backend and frontend reloads, use:

```bash
make dev
```

Open <http://127.0.0.1:5173>; Vite proxies API calls to port 8000. `make backend` and
`make frontend` are also available when separate terminals are preferable.

On a remote HPC login node, keep the default loopback binding and forward the port from a local
machine, for example `ssh -L 8000:127.0.0.1:8000 user@host`.

## Creating, opening, and importing

On the opening screen, enter a project name, optionally enter the exact empty directory in which
to store it, and define at least one foreground class. If the directory is blank, a named project
directory is created under `~/.segmentation_labeler/projects/`. Class ID `0` is permanently
reserved for background. Automatic foreground IDs start at `1` and never change when a class is
renamed or recolored.

To resume, choose a recent project or enter the directory containing its `project.sqlite`. The
image list, classes, masks, statuses, last image, overlay opacity, and mask visibility are restored.

The **Import images** panel supports:

- one or multiple files selected in the browser;
- a browser folder selection, preserving relative subdirectories;
- a ZIP archive, preserving safe member paths; or
- an explicitly entered server-side local directory, imported recursively.

Valid files continue importing when another file is invalid; each rejected filename and reason is
shown. Imported raster images are decoded by content and written as normalized PNG display copies.
Original filenames and relative paths remain in metadata. Two-dimensional NumPy and DICOM intensity
images are scaled to 8-bit only for display; annotation dimensions are unchanged.

## Classes and annotation tools

The selected class has a highlighted row and check mark. **Manage** adds, renames, recolors, or
deletes classes. IDs remain stable. Deleting a used class requires a second explicit confirmation
that its pixels will become background.

- **Brush (`B`)** paints the active class with a circular, continuous stroke. Adjust its 1–200 px
  diameter with the toolbar or `[` and `]`.
- **Eraser (`E`)** changes pixels to background ID `0` and uses the same size control.
- **Polygon (`P`)** adds a vertex per click. Close by clicking the highlighted first vertex,
  double-clicking, or pressing `Enter`. At least three non-degenerate vertices are required.
  `Escape` cancels an unfinished polygon.
- **Pan (`H`)** drags the view without editing.

Brush, polygon, and eraser all modify one shared class-indexed mask, so they can refine each other.
The pointer wheel zooms around the cursor. Toolbar controls zoom in/out, fit the image, return to
100%, toggle the overlay, and change opacity. Every pointer is converted through the canvas
transform into original image coordinates, independent of zoom and browser pixel ratio.

Use **Undo** (`Ctrl+Z` or `Command+Z`) and **Redo** (`Ctrl+Y`, `Ctrl+Shift+Z`, or
`Command+Shift+Z`). A complete brush/eraser stroke or polygon is one history operation. Clear class
removes only the active foreground class; Reset removes all classes. Both request confirmation and
are undoable.

## Navigation, status, and autosave

Use the scrollable/searchable list or Previous/Next buttons. Gray, amber, and green dots mean Not
started, In progress, and Completed. The footer can mark or unmark the current image as completed,
and the header reports completed/total progress.

The save indicator changes through **Saving**, **Saved**, and **Save failed**. Autosave runs after
every stroke, erase, polygon, undo, redo, clear, reset, or imported mask. Saves are serialized so a
slower older request cannot replace a newer mask; while one upload is active, intermediate queued
states are replaced by the newest state. Mask uploads are gzip-compressed when beneficial.
Navigation waits for the active/latest save; confirmation is shown only when a failed save leaves
genuine unsaved work.

## Input formats

Supported inputs are PNG, JPEG/JPG, single-page TIFF/TIF, BMP, WebP, two-dimensional numeric `.npy`,
and DICOM `.dcm`. ZIP may contain any of these. Multi-page TIFF is rejected with an explanation
rather than ambiguously selecting a page. DICOM support covers pixel data that the installed
`pydicom` can decode; uncommon compressed transfer syntaxes may need to be converted first. Files
with unsupported extensions, corrupt content, non-2D arrays, or unsafe archive paths are rejected.

An existing PNG, TIFF, or NPY indexed mask can be imported for the current image. Its dimensions
must match exactly, values must be integers, and every nonzero value must be a configured class ID.
The application never resizes or silently remaps an imported mask.

## Mask encoding and export

Working masks are two-dimensional `uint16` arrays with the exact source width and height. Pixel `0`
means background; values `1...65535` are stable configured class IDs. Colors are display metadata,
not pixel encodings.

The **Export masks** panel exports the current image, checked images, or all images. Each export
creates a new timestamped directory, so it cannot overwrite unrelated files. Formats are:

- class-indexed 8-bit PNG when every configured ID is at most 255 (default);
- 16-bit TIFF; and
- NumPy `.npy` containing `uint16` values.

**Download current mask** downloads the current image immediately in the selected format. **Export
batch** writes the selected batch on the server and displays a **Download export ZIP** button, so
remote users do not need filesystem access to the HPC path shown in the status message.

The usual name is `<original-stem>_mask.png`, with source subdirectories preserved. Same-directory
files such as `sample.jpg` and `sample.tif` become `sample_jpg_mask.png` and
`sample_tif_mask.png`; a stable image-ID suffix resolves any remaining duplicate. TIFF and NPY use
the same stem rule with their own extension.

Every batch includes `classes.json` with the background definition, class IDs/names/colors, export
format, schema/application version, source-to-mask mapping, dimensions, per-image class pixel
counts, and aggregate class statistics. It also includes `class_summary.txt`, a readable report of
class IDs, labels, colors, total pixels, number of images containing each class, and per-image pixel
counts. Both metadata files and all masks are included in the downloadable ZIP.

## Tests and quality checks

Run all unit and component tests:

```bash
make test
```

Run lint, TypeScript checking, and the production build:

```bash
make lint
make typecheck
make build
```

Backend coverage alone can be run with `uv run pytest`, and frontend component tests with
`npm --prefix frontend test -- --run`. The API workflow test generates its own images, creates a
two-class project, combines operations, saves/reopens it, and reads exported masks back. Browser
automation, when a Playwright Chromium binary is installed for the current user, runs with:

```bash
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend run e2e
```

## Troubleshooting

- **Port already in use:** run `uv run segmentation-labeler --port 8010` after the frontend build.
- **Remote page does not open:** use SSH port forwarding and confirm `/api/health` returns `ok`.
- **Project cannot be created:** choose a writable empty directory; the backend will not mix a new
  project into a nonempty path.
- **An image is rejected:** expand the error toast. Extensions and decoded content must both be
  supported; multi-page TIFF and arrays with more than two dimensions are intentionally rejected.
- **PNG export is refused:** a configured class ID exceeds 255; select TIFF or NPY so IDs remain exact.
- **Save failed:** keep the page open, check filesystem quota/permissions, and make another edit or
  retry with undo/redo. The UI warns before leaving while unsaved work remains.
- **Canvas is cramped:** enlarge the desktop window; labeling is intentionally not offered as a
  mobile workflow.

## Known limitations

- Undo/redo history is per open image and is not persisted across image switches or application
  restarts; saved masks are persisted.
- Multi-page TIFF is rejected instead of expanded into separate images.
- NPY and DICOM display conversion does not currently expose window/level controls.
- There is no authentication or multi-user conflict resolution; this is a loopback-only, single-user
  local tool.
- Very large masks consume additional browser memory for the overlay and undo snapshots. History is
  capped to limit growth.
