# Windy Image Tool

A minimal desktop app for common image tasks on Windows.

## Features

- Convert formats (JPEG, PNG, WEBP, AVIF, BMP, GIF, TIFF)
- Crop with draggable bounds or numeric inputs
- Resize with optional aspect ratio lock
- Compress with auto or target file size
- Rotate (90° / 180° / 270°, left or right)
- Flip horizontally or vertically
- Adjust hue with live preview
- Customizable font size, background color, and text color

## Run from source

```bat
pip install -r requirements.txt
python main.py
```

Or double-click `run.bat`.

## Build the portable `.exe`

```bat
build.bat
```

The executable is written to `dist/Windy Image Tool.exe`.

## Downloads

Get the latest portable Windows build from [Releases](https://github.com/fwqefwqef/windy-image-tool/releases).
