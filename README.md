# Windy Image Tool

A minimal desktop app for common image tasks on Windows.

## Features

- Convert formats (JPEG, PNG, WEBP, AVIF, BMP, GIF, TIFF)
- Crop with draggable bounds or numeric inputs
- Resize by pixels with optional aspect ratio lock, or by percentage across the entire batch
- Compress with auto or target file size
- Rotate (90° / 180° / 270°, left or right)
- Flip horizontally or vertically
- Adjust hue with live preview
- Remove near-white backgrounds to transparent PNG
- Batch selection for convert, crop, resize, compress, rotate, flip, hue, and transparency tools
- Add multiple image layers to a meme in one selection
- Customizable font size, background color, and text color

For tools with a preview, the first selected image drives the preview and initial settings. The chosen settings are then applied to every image in the batch; files that fail are reported without stopping the remaining images.

In Resize, choose Percentage and enter a value such as 50 to halve every image's width and height, or 200 to double them. Each image is scaled from its own original dimensions, with a minimum of one pixel per dimension.

## Run from source

```bat
setup.bat
run.bat
```

Or just double-click `run.bat`; it creates a local `.venv` and installs missing dependencies automatically through `uv`.

## Build the portable `.exe`

```bat
build.bat
```

The executable is written to `dist/Windy Image Tool.exe`.

## Downloads

Get the latest portable Windows build from [Releases](https://github.com/fwqefwqef/windy-image-tool/releases).

## Publish source changes

Run `publish-github.bat` to stage, commit, and push the current branch to the configured `origin` remote. You can optionally supply a commit message:

```bat
publish-github.bat "Describe the changes"
```
