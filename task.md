# Task: Build a Local 2D Image Segmentation Labeling Application

## Scope and repository boundaries

For this task:

1. Read the repository instruction file `AGENT.md` and this `task.md` before doing any work.

   * If the repository uses `AGENTS.md` instead of `AGENT.md`, read that file.
2. Do not inspect the entire repository, unrelated source files, Git history, or unrelated documentation.
3. Only inspect additional files when they are directly required to:

   * Follow instructions from `AGENT.md`.
   * Detect a naming or dependency conflict.
   * Create, run, test, or document the new application.
4. Do not modify unrelated code or configuration.
5. Create the application inside a new top-level directory named:

```text
segmentation_labeler/
```

You may choose a more appropriate name only if `segmentation_labeler` conflicts with an existing path. Document any naming change.

This task does not require GPU access. Do not request or use a GPU.

---

## Objective

Design and implement a complete, reliable, user-friendly application for manually labeling semantic segmentation masks for two-dimensional images.

The application must allow users to:

* Create or reopen an annotation project.
* Import one image, multiple images, or a directory of images.
* Define multiple segmentation classes.
* Annotate each image using brush, eraser, and polygon tools.
* Combine different annotation tools on the same image.
* Save progress automatically.
* Close the application and later resume from the same project.
* Export masks with predictable filenames and class metadata.

Do not produce only a prototype, UI mock-up, or incomplete scaffold. Implement a working application and verify its core workflows with automated tests.

---

## Technology selection

Do not force the implementation into Streamlit if Streamlit cannot provide a responsive and reliable annotation experience.

Use the simplest maintainable architecture that fully supports the required canvas interactions.

The preferred default architecture is:

* Python backend, preferably FastAPI.
* SQLite for project metadata and progress tracking.
* React with TypeScript for the frontend.
* A mature canvas library such as Konva or Fabric.js for annotation interactions.
* Pillow, NumPy, and other focused Python imaging libraries for image and mask processing.

A different architecture is acceptable only when it provides all required functionality more simply and reliably.

Keep the code professional, modular, understandable, and easy to extend. Avoid unnecessary services, abstractions, distributed components, or infrastructure.

The application should run locally and must not depend on an external cloud service.

---

## Core project workflow

### 1. Project creation

The user must be able to create a named annotation project.

A project must store at least:

* Project name and identifier.
* Creation and modification times.
* Source-image locations or imported copies.
* Image dimensions and relevant metadata.
* Class definitions.
* Current masks.
* Per-image annotation status.
* Last opened image.
* Application state required to resume work.

Allow the user to choose where the project data will be stored, or use a clearly documented default workspace directory.

### 2. Reopening and resuming

The user must be able to reopen an existing project and continue labeling without losing previous work.

When reopening a project, restore at least:

* Imported images.
* Class IDs, names, and colors.
* Existing masks.
* Current or last opened image.
* Per-image completion status.
* Relevant display settings when practical.

Use SQLite for structured metadata. Store large images and masks as files rather than unnecessarily storing large binary objects in SQLite.

Use safe, atomic writes where practical so an interrupted save does not corrupt an existing annotation.

### 3. Image input

Support all of the following:

* Uploading a single image.
* Uploading multiple images.
* Selecting or uploading a folder of images.
* Importing a ZIP archive containing images.
* Supplying a local server-side directory path when the application is running locally.

At minimum, support these common two-dimensional raster formats:

* PNG
* JPEG and JPG
* TIFF and TIF
* BMP
* WebP

Where reasonably practical, support:

* Two-dimensional NumPy arrays stored as `.npy`.
* DICOM images stored as `.dcm`.

Do not advertise unsupported formats as supported. Use file-content validation where practical rather than relying only on filename extensions.

For unsupported or invalid files:

* Do not crash.
* Skip or reject the file safely.
* Show a clear error identifying the affected file and reason.
* Continue processing other valid files when possible.

For multi-page TIFF files, either import each page as a separate two-dimensional image or reject them with a clear explanation. Document the selected behavior.

Preserve relative directory structures when importing folders so images with identical filenames from different subdirectories do not conflict.

### 4. Image navigation

Provide:

* Previous-image and next-image controls.
* A searchable or scrollable image list.
* Visible annotation status for every image, such as:

  * Not started
  * In progress
  * Completed
* A way to mark or unmark an image as completed.
* A progress indicator such as `completed images / total images`.
* Confirmation before leaving an image only when unsaved changes genuinely remain.

Autosaving should normally prevent users from losing work during navigation.

---

## Segmentation classes

At project creation, allow users to define one or more segmentation classes.

For each class, allow the user to configure:

* A stable numeric class ID.
* A unique, non-empty class name.
* A display color.

Use class ID `0` exclusively for the background.

Foreground class IDs should begin at `1`.

Support adding, renaming, and recoloring classes after project creation when this can be done safely. Existing class IDs must remain stable. Removing a class that is already used in masks must require explicit confirmation and clearly explain how its pixels will be handled.

Support at least 255 foreground classes. When an export format cannot safely represent the configured number of classes, show a clear explanation and require a compatible export format.

The interface must make the currently selected class obvious. Users must be able to switch classes without losing existing annotations.

---

## Annotation interface

The annotation canvas must display the original image with the segmentation mask as a configurable overlay.

Provide controls for:

* Mask visibility.
* Overlay opacity.
* Zooming in and out.
* Panning.
* Fitting the image to the available view.
* Returning to 100% zoom.
* Selecting the active class.
* Selecting the active annotation tool.

Annotations must always be aligned with the original image coordinates, regardless of zoom level, canvas scaling, browser size, or device pixel ratio.

The exported mask must have exactly the same width and height as the source image.

Do not resize or interpolate class IDs when exporting masks.

---

## Required annotation tools

### 1. Brush tool

Implement a circular brush that paints the selected class ID.

Provide:

* Adjustable brush size.
* A visible brush cursor.
* Continuous painting while dragging.
* Correct coordinate handling at every zoom level.
* Smooth strokes without major gaps during normal mouse movement.
* A reasonable minimum and maximum brush size.

Useful keyboard shortcuts such as `[` and `]` for brush size are encouraged when they do not conflict with browser behavior.

### 2. Eraser tool

Implement an eraser that changes affected pixels back to background class ID `0`.

The eraser must:

* Have an adjustable size.
* Work correctly at every zoom level.
* Be usable on annotations created by either brush or polygon tools.
* Be undoable.

### 3. Polygon tool

Implement polygon-based area labeling.

Expected interaction:

1. The user selects a class and activates the polygon tool.
2. The first click creates the first polygon vertex.
3. Each subsequent click adds another vertex.
4. The polygon closes when the user clicks the first vertex again.

Also support practical completion methods such as double-clicking or pressing `Enter`, provided clicking the first point remains supported.

Provide:

* A visible preview of polygon edges and vertices.
* A visibly distinct first vertex.
* `Escape` to cancel an unfinished polygon.
* Validation requiring at least three valid vertices.
* Correct rasterization into the selected class ID.
* Correct behavior at all zoom levels.
* Undo support for the completed polygon.

A polygon must not be committed when it is invalid or unfinished.

### 4. Combining tools

Users must be able to use brush, polygon, and eraser operations on the same image and the same mask.

For example, a user must be able to:

1. Label a large region with a polygon.
2. Refine its boundary with a brush.
3. Remove mistakes with the eraser.
4. Switch to another class and continue annotating.

The tools must operate on one consistent class-indexed mask rather than creating incompatible annotation layers.

---

## History and editing controls

Implement:

* Undo using `Ctrl+Z` on Windows/Linux and `Command+Z` on macOS.
* Redo using `Ctrl+Y`, `Ctrl+Shift+Z`, or `Command+Shift+Z`.
* Visible undo and redo buttons.
* Reset current image.
* Clear only the currently selected class from the current image.
* Confirmation before destructive reset or clear operations.

Undo and redo history must work for at least:

* Brush strokes.
* Eraser strokes.
* Completed polygons.
* Clear-class operations.
* Full-image reset operations.

History may be maintained per image. Document whether history persists after closing and reopening a project. Saved mask state must always persist even if the temporary undo history does not.

Do not create one undo entry for every individual pixel or pointer event. Treat one continuous brush or eraser stroke as one logical operation.

---

## Autosave and data integrity

Automatically save progress:

* After a completed brush stroke.
* After a completed eraser stroke.
* After a polygon is committed.
* After an undo or redo operation.
* After a clear or reset operation.
* Before switching images when necessary.
* At a reasonable debounced interval during active work if beneficial.

Display save status clearly, such as:

* Saving
* Saved
* Save failed

A failed save must not be silently ignored.

Prevent path traversal, unsafe filenames, and accidental writes outside the configured project or export directory.

---

## Mask representation

Use a single class-indexed semantic segmentation mask for each image:

* `0` represents background.
* `1...N` represent configured foreground classes.

Internally, use a suitable integer representation such as:

* `uint8` when all class IDs fit within 8 bits.
* `uint16` when more class IDs are required.

Do not store only a colorized mask because colors are presentation metadata and must not replace stable numeric class IDs.

Class colors must be stored separately in project metadata.

---

## Export requirements

Provide an export workflow for:

* The current image.
* Selected images.
* All project images.

The default export must produce class-indexed PNG masks when the configured class IDs can be represented safely.

Use this filename convention:

```text
<original_image_stem>_mask.png
```

Examples:

```text
wound_001.jpg       -> wound_001_mask.png
patient_04.tif      -> patient_04_mask.png
```

Preserve source subdirectories in the export directory when needed to avoid filename collisions.

When two source files in the same directory have the same stem but different extensions, prevent overwriting by including a deterministic disambiguator, such as the source extension:

```text
sample_jpg_mask.png
sample_tif_mask.png
```

Never silently overwrite unrelated existing files.

Also support at least one format suitable for masks requiring more than 8-bit class IDs, such as:

* 16-bit TIFF
* NumPy `.npy`

Optional useful exports include:

* One binary mask per class.
* A colorized preview mask.
* A project ZIP bundle.

Generate a machine-readable metadata file, such as `classes.json`, containing at least:

* Background definition.
* Class IDs.
* Class names.
* Class colors.
* Export format.
* Source-to-mask filename mapping.
* Mask dimensions.
* Application or schema version.

For indexed masks, pixel values must be class IDs, not arbitrary palette indices that cannot be interpreted without undocumented behavior.

Verify exported masks by reading them back during automated tests.

---

## Importing existing masks

When reasonably achievable without compromising the core implementation, allow users to import existing masks for an image.

At minimum:

* Validate that mask dimensions match the source image.
* Validate that mask values correspond to known class IDs.
* Reject invalid masks with a clear explanation.
* Never silently resize an incompatible mask.
* Never silently remap unknown class IDs.

This feature is secondary to reliable project persistence and export, but the architecture should not prevent it from being added later.

---

## User experience requirements

The interface must be understandable to a user who is experienced with Python and machine learning but not necessarily with frontend development.

Provide:

* A clean project-opening screen.
* Clear labels and concise help text.
* Tooltips for non-obvious controls.
* Visible keyboard shortcuts.
* Clear error messages.
* Confirmation for destructive actions.
* Responsive layout for standard desktop screens.
* A warning when the browser window is too small for reliable labeling.
* No hidden dependency on browser developer tools.

Use a desktop-first design. Mobile annotation support is not required.

Avoid clutter and avoid adding unrelated image-processing or machine-learning features.

This is a manual annotation tool. Do not add model-assisted segmentation unless it is isolated, optional, and does not delay or destabilize the required functionality.

---

## Backend/API requirements

When using a separate backend:

* Define clear request and response schemas.
* Validate all incoming data.
* Return useful HTTP errors.
* Keep file-system operations on the backend.
* Avoid exposing arbitrary server files.
* Restrict local-directory imports to explicitly selected paths.
* Use stable project and image identifiers rather than trusting filenames as identifiers.
* Add API tests for important project, image, mask, save, resume, and export operations.

The frontend must not be the only location where critical mask validation or export rules are implemented.

---

## Code quality requirements

The implementation must:

* Use clear directory and module names.
* Separate UI, state management, persistence, mask operations, and export logic.
* Include type hints in Python code.
* Use TypeScript rather than untyped JavaScript when using a JavaScript frontend.
* Avoid duplicated mask-operation logic.
* Avoid hard-coded absolute paths.
* Avoid dependencies on files outside `segmentation_labeler/`, except for repository-wide tooling explicitly required by `AGENT.md`.
* Include helpful comments only where the reasoning is not obvious.
* Handle errors explicitly.
* Log useful backend errors without exposing sensitive local paths unnecessarily in the UI.

Do not claim that the software is completely bug-free. Instead, thoroughly test the required workflows and document any known limitations honestly.

---

## Testing requirements

Create automated tests that cover the important behavior. Tests must use generated fixture images and masks where possible, so they do not depend on downloading external data.

### Backend and unit tests

Test at least:

* Project creation.
* Project reopening.
* Class creation and validation.
* Stable class IDs.
* Brush rasterization.
* Eraser behavior.
* Polygon rasterization.
* Overlapping annotations from different classes.
* Undo and redo state behavior.
* Reset and clear-class behavior.
* Autosave or save operations.
* Correct mask dimensions.
* Correct mask pixel values.
* Export naming.
* Filename-collision handling.
* PNG export and read-back.
* A format supporting more than 8-bit class IDs.
* Invalid image handling.
* Invalid or mismatched mask handling.
* Persistence after application restart or backend reinitialization.

### Frontend tests

Test at least:

* Project creation or opening.
* Image selection.
* Class selection.
* Tool selection.
* Brush-size changes.
* Undo and redo controls.
* Destructive-action confirmation.
* Save-status display.
* Image navigation.

### End-to-end test

When practical, add at least one Playwright or equivalent browser test that:

1. Creates a project.
2. Imports a small generated image.
3. Defines at least two classes.
4. Adds an annotation.
5. Saves the project.
6. Reloads or reopens it.
7. Confirms that the annotation still exists.
8. Exports the mask.
9. Confirms that the exported mask has the correct dimensions and class IDs.

If browser automation is not practical in the current environment, provide strong backend and frontend component tests and clearly document the missing end-to-end coverage.

Run all relevant:

* Unit tests.
* Integration tests.
* Frontend tests.
* Type checks.
* Linters.
* Production builds.

Fix failures caused by this implementation rather than disabling meaningful checks.

No GPU must be required for any test.

---

## Documentation

Create:

```text
segmentation_labeler/README.md
```

The README must include:

* What the application does.
* Supported operating assumptions.
* Architecture summary.
* Prerequisites.
* Exact installation commands.
* Exact development-mode commands.
* Exact production or local-user startup command.
* How to create and reopen a project.
* How to import images.
* How to configure classes.
* How to use each annotation tool.
* Keyboard shortcuts.
* Autosave and project-storage behavior.
* Supported input formats.
* Supported output formats.
* Mask encoding and background/class-ID conventions.
* Export naming rules.
* How to run tests.
* Known limitations.
* Troubleshooting guidance.

Prefer a simple startup command from inside `segmentation_labeler/`, such as:

```bash
make run
```

or:

```bash
python -m segmentation_labeler
```

A small script may start both backend and frontend when necessary. Do not require users to manually coordinate several undocumented terminal commands.

Provide an `.env.example` only if configuration variables are genuinely required. Do not commit secrets.

---

## Expected directory structure

Use a clean structure appropriate to the selected stack. For example:

```text
segmentation_labeler/
├── README.md
├── backend/
│   ├── ...
│   └── tests/
├── frontend/
│   ├── ...
│   └── tests/
├── scripts/
├── sample_data/
├── .gitignore
└── ...
```

This is an example, not a strict requirement. Prefer the simplest structure that remains maintainable.

Do not add generated dependency directories, build outputs, virtual environments, databases, temporary project files, or large sample images to version control.

---

## Acceptance criteria

The task is complete only when all of the following are true:

1. The application starts using the documented command.
2. No GPU is required.
3. A user can create a project.
4. A user can import one image, multiple images, or a folder/archive of images.
5. A user can define multiple classes with names and colors.
6. Background uses class ID `0`.
7. A user can annotate with a brush.
8. A user can erase annotations.
9. A user can create and close polygon annotations.
10. Brush, eraser, and polygon operations can be combined on one image.
11. A user can switch between classes.
12. Undo, redo, clear-class, and reset work correctly.
13. Zooming and panning do not misalign annotations.
14. Masks retain the exact source-image dimensions.
15. Progress is automatically saved.
16. Closing and reopening a project restores saved annotations.
17. The user can navigate among images and see annotation status.
18. Masks export using deterministic names based on source-image names.
19. Exported mask pixels contain stable numeric class IDs.
20. Class names and colors are exported as metadata.
21. Filename collisions do not silently overwrite masks.
22. Invalid files produce understandable errors rather than crashes.
23. Automated tests cover the core persistence, annotation, and export logic.
24. All documented tests, type checks, and builds pass.
25. The README contains enough information for another developer to install, run, test, and use the application.

---

## Final verification and report

Before finishing:

1. Review the changes for accidental modifications outside the task scope.
2. Run the complete relevant test suite.
3. Run the frontend production build when applicable.
4. Start the application and perform a manual smoke test.
5. Test at least two images and two segmentation classes.
6. Verify brush, eraser, polygon, undo, redo, reset, navigation, resume, and export.
7. Open at least one exported mask programmatically and verify:

   * Its dimensions match the source image.
   * Its values are valid class IDs.
   * Its filename follows the documented convention.
8. Confirm that restarting the application preserves saved work.

In the final response, provide:

* A concise summary of the implemented architecture.
* The main files and directories created.
* Exact installation and startup commands.
* Tests and checks executed, including their results.
* A brief manual-verification summary.
* Any known limitations or incomplete optional features.

Do not state that something was tested unless the corresponding command or manual verification was actually completed.

When a requirement remains ambiguous, select the simplest reasonable implementation that satisfies the objective, document the decision in the README, and continue rather than leaving the application incomplete.


feel free to install all of the dependency you need , but consider one point, you are use kelvin2 HPC and you are an ordinary user and dont have access to admin rights 