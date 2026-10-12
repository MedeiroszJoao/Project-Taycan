# Local review of the 509 Taycan images

**Goal:** inspect the images visually without uploading ~2.02 GB of originals to public GitHub.

## Run on Windows

Open PowerShell. The images must be in the folder Downloads/Taycan_Images, with the original gallery subfolders intact.

1. Change to the already cloned Project-Taycan folder:

    cd "$HOME\Downloads\Project-Taycan"

2. Receive the generator committed to GitHub:

    git pull --ff-only origin main

3. Run it using Windows PowerShell (no Python or additional modules needed):

    powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\build_taycan_contact_sheets.ps1"

If the source folder is somewhere else, specify the directory with the optional -Source argument:

    powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\build_taycan_contact_sheets.ps1" -Source "C:\path\to\Taycan_Images"

## Expected outputs

The default output folder is Downloads/Taycan_ContactSheets **outside the Git repository**.

- Around 21 numbered JPG contact sheets containing 25 thumbnail images each, in consistent file order.
- taycan_sheets_index.csv maps the visible image number to the original exact path, dimensions and file size.
- taycan_contact_sheets.zip bundles these review artifacts, not the full-resolution originals.
- Source images are never modified.

Upload the resulting taycan_contact_sheets.zip to the existing ChatGPT conversation. If its size exceeds the attachment limit, send the JPG sheets in a few batches alongside the index CSV.

Use a fresh -Output directory when rerunning: to avoid unintentional overwrites, the generator refuses to overwrite existing sheets.

## Provenance and safety

The originals remain on the user's machine. The repository already has data/manifests/taycan_images_inventory.csv containing their SHA-256 hashes. Generated contact sheets are derivatives of their original images and should NOT be pushed to a public repo without the necessary distribution rights. A private repository by itself does not create such rights.

Contact sheet review supports visual identification, not direct validation of numerical simulation parameters, and does not modify any frozen project stage.
