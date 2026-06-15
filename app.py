from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk

from operations import (
    FORMAT_EXTENSIONS,
    adjust_hue_image,
    compress_image,
    convert_image,
    crop_image,
    ensure_output_dir,
    flip_image,
    load_image,
    resize_image,
    rotate_image,
    shift_hue,
)
from settings import DEFAULT_SETTINGS, dim_color, is_valid_color, load_settings, save_settings

IMAGE_TYPES = [
    ("Image files", "*.jpg *.jpeg *.png *.webp *.avif *.bmp *.gif *.tiff *.tif"),
    ("All files", "*.*"),
]


OVERLAY_SHADE = "#646464"


class ImagePreviewLabel(tk.Label):
    """Lightweight image preview using Label instead of Canvas."""

    def __init__(self, master: tk.Misc, placeholder: str = "Load an image to preview", canvas_bg: str = "#f2f2f2", text_color: str = "#1a1a1a", **kwargs):
        super().__init__(
            master,
            bg=canvas_bg,
            fg=dim_color(text_color),
            text=placeholder,
            anchor="center",
            **kwargs,
        )
        self.placeholder = placeholder
        self.canvas_bg = canvas_bg
        self.placeholder_color = dim_color(text_color)
        self.source_image: Image.Image | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self._preview_cache_key: tuple[int, int, int] | None = None
        self._render_size: tuple[int, int] = (0, 0)

    def apply_theme(self, canvas_bg: str, text_color: str) -> None:
        self.canvas_bg = canvas_bg
        self.placeholder_color = dim_color(text_color)
        self.configure(bg=canvas_bg, fg=self.placeholder_color)
        self.redraw(force_image=True)

    def set_image(self, image: Image.Image | None) -> None:
        self.source_image = image
        self._preview_cache_key = None
        self._render_size = (0, 0)
        self.redraw(force_image=True)

    def _preview_photo(self, draw_w: int, draw_h: int) -> ImageTk.PhotoImage:
        cache_key = (id(self.source_image), draw_w, draw_h)
        if cache_key == self._preview_cache_key and self._photo is not None:
            return self._photo
        preview = self.source_image.copy()
        preview.thumbnail((draw_w, draw_h), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(preview)
        self._preview_cache_key = cache_key
        return self._photo

    def redraw(self, force_image: bool = False) -> None:
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        render_size = (width, height)

        if not self.source_image:
            if render_size == self._render_size and not force_image:
                return
            self._render_size = render_size
            self.configure(image="", text=self.placeholder, fg=self.placeholder_color)
            return

        if not force_image and render_size == self._render_size:
            return

        self._render_size = render_size
        photo = self._preview_photo(width, height)
        self.configure(image=photo, text="")


class CropCanvas(tk.Canvas):
    HANDLE = 8

    def __init__(self, master: tk.Misc, on_change, canvas_bg: str = "#f2f2f2", text_color: str = "#1a1a1a", **kwargs):
        super().__init__(master, bg=canvas_bg, highlightthickness=0, **kwargs)
        self.on_change = on_change
        self.canvas_bg = canvas_bg
        self.placeholder_color = dim_color(text_color)
        self.source_image: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self._preview_cache_key: tuple[int, int, int] | None = None
        self._render_size: tuple[int, int] = (0, 0)
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = 1
        self.crop_h = 1
        self.drag_mode: str | None = None
        self.drag_start: tuple[int, int] | None = None
        self.initial_crop: tuple[int, int, int, int] | None = None

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def apply_theme(self, canvas_bg: str, text_color: str) -> None:
        self.canvas_bg = canvas_bg
        self.placeholder_color = dim_color(text_color)
        self.configure(bg=canvas_bg)
        self.redraw(force_image=True)

    def set_image(self, image: Image.Image) -> None:
        self.source_image = image
        self._preview_cache_key = None
        self._render_size = (0, 0)
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = image.width
        self.crop_h = image.height
        self.redraw(force_image=True)
        self.on_change(self.crop_x, self.crop_y, self.crop_w, self.crop_h)

    def set_crop(self, x: int, y: int, width: int, height: int) -> None:
        if not self.source_image:
            return
        self.crop_x = max(0, min(x, self.source_image.width - 1))
        self.crop_y = max(0, min(y, self.source_image.height - 1))
        max_w = self.source_image.width - self.crop_x
        max_h = self.source_image.height - self.crop_y
        self.crop_w = max(1, min(width, max_w))
        self.crop_h = max(1, min(height, max_h))
        self._update_overlay()

    def _preview_photo(self, draw_w: int, draw_h: int) -> ImageTk.PhotoImage:
        cache_key = (id(self.source_image), draw_w, draw_h)
        if cache_key == self._preview_cache_key and self.photo is not None:
            return self.photo
        preview = self.source_image.copy()
        preview.thumbnail((draw_w, draw_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(preview)
        self._preview_cache_key = cache_key
        return self.photo

    def _layout(self) -> tuple[int, int, int, int] | None:
        if not self.source_image:
            return None
        canvas_w = max(self.winfo_width(), 1)
        canvas_h = max(self.winfo_height(), 1)
        scale_x = canvas_w / self.source_image.width
        scale_y = canvas_h / self.source_image.height
        self.scale = min(scale_x, scale_y, 1.0)
        draw_w = int(self.source_image.width * self.scale)
        draw_h = int(self.source_image.height * self.scale)
        self.offset_x = (canvas_w - draw_w) // 2
        self.offset_y = (canvas_h - draw_h) // 2
        return canvas_w, canvas_h, draw_w, draw_h

    def _update_overlay(self) -> None:
        layout = self._layout()
        if layout is None:
            return
        canvas_w, canvas_h, _, _ = layout
        self.delete("overlay")
        x1, y1, x2, y2 = self._crop_to_canvas()
        for coords in (
            (0, 0, canvas_w, y1),
            (0, y2, canvas_w, canvas_h),
            (0, y1, x1, y2),
            (x2, y1, canvas_w, y2),
        ):
            self.create_rectangle(*coords, fill=OVERLAY_SHADE, outline="", tags="overlay")
        self.create_rectangle(x1, y1, x2, y2, outline="#4da3ff", width=2, tags="overlay")
        for hx, hy in self._handles():
            self.create_rectangle(
                hx - self.HANDLE // 2,
                hy - self.HANDLE // 2,
                hx + self.HANDLE // 2,
                hy + self.HANDLE // 2,
                fill="#ffffff",
                outline="#4da3ff",
                tags="overlay",
            )

    def redraw(self, force_image: bool = False) -> None:
        layout = self._layout()
        if layout is None:
            canvas_w = max(self.winfo_width(), 1)
            canvas_h = max(self.winfo_height(), 1)
            render_size = (canvas_w, canvas_h)
            if render_size == self._render_size and not force_image:
                return
            self._render_size = render_size
            self.delete("all")
            self.create_text(
                canvas_w // 2,
                canvas_h // 2,
                text="Load an image to crop",
                fill=self.placeholder_color,
            )
            return

        canvas_w, canvas_h, draw_w, draw_h = layout
        render_size = (canvas_w, canvas_h)
        image_changed = force_image or render_size != self._render_size

        if image_changed:
            self._render_size = render_size
            self.delete("all")
            photo = self._preview_photo(draw_w, draw_h)
            self.create_image(self.offset_x, self.offset_y, anchor="nw", image=photo, tags="image")

        self._update_overlay()

    def _crop_to_canvas(self) -> tuple[int, int, int, int]:
        x1 = self.offset_x + int(self.crop_x * self.scale)
        y1 = self.offset_y + int(self.crop_y * self.scale)
        x2 = self.offset_x + int((self.crop_x + self.crop_w) * self.scale)
        y2 = self.offset_y + int((self.crop_y + self.crop_h) * self.scale)
        return x1, y1, x2, y2

    def _canvas_to_image(self, x: int, y: int) -> tuple[int, int]:
        ix = int((x - self.offset_x) / self.scale)
        iy = int((y - self.offset_y) / self.scale)
        ix = max(0, min(ix, self.source_image.width))
        iy = max(0, min(iy, self.source_image.height))
        return ix, iy

    def _handles(self) -> list[tuple[int, int]]:
        x1, y1, x2, y2 = self._crop_to_canvas()
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2
        return [
            (x1, y1),
            (mx, y1),
            (x2, y1),
            (x1, my),
            (x2, my),
            (x1, y2),
            (mx, y2),
            (x2, y2),
        ]

    def _hit_test(self, x: int, y: int) -> str:
        x1, y1, x2, y2 = self._crop_to_canvas()
        margin = self.HANDLE + 2
        inside = x1 <= x <= x2 and y1 <= y <= y2
        near_left = abs(x - x1) <= margin
        near_right = abs(x - x2) <= margin
        near_top = abs(y - y1) <= margin
        near_bottom = abs(y - y2) <= margin

        if near_left and near_top:
            return "nw"
        if near_right and near_top:
            return "ne"
        if near_left and near_bottom:
            return "sw"
        if near_right and near_bottom:
            return "se"
        if near_top and inside:
            return "n"
        if near_bottom and inside:
            return "s"
        if near_left and inside:
            return "w"
        if near_right and inside:
            return "e"
        if inside:
            return "move"
        return "none"

    def _on_press(self, event: tk.Event) -> None:
        if not self.source_image:
            return
        mode = self._hit_test(event.x, event.y)
        if mode == "none":
            return
        self.drag_mode = mode
        self.drag_start = (event.x, event.y)
        self.initial_crop = (self.crop_x, self.crop_y, self.crop_w, self.crop_h)

    def _on_drag(self, event: tk.Event) -> None:
        if not self.source_image or not self.drag_mode or not self.drag_start or not self.initial_crop:
            return
        ix, iy = self._canvas_to_image(event.x, event.y)
        sx, sy = self._canvas_to_image(*self.drag_start)
        ox, oy, ow, oh = self.initial_crop
        dx = ix - sx
        dy = iy - sy
        img_w = self.source_image.width
        img_h = self.source_image.height

        if self.drag_mode == "move":
            nx = max(0, min(ox + dx, img_w - ow))
            ny = max(0, min(oy + dy, img_h - oh))
            self.crop_x, self.crop_y = nx, ny
        else:
            left, top, right, bottom = ox, oy, ox + ow, oy + oh
            if "w" in self.drag_mode:
                left = max(0, min(left + dx, right - 1))
            if "e" in self.drag_mode:
                right = min(img_w, max(right + dx, left + 1))
            if "n" in self.drag_mode:
                top = max(0, min(top + dy, bottom - 1))
            if "s" in self.drag_mode:
                bottom = min(img_h, max(bottom + dy, top + 1))
            self.crop_x, self.crop_y = left, top
            self.crop_w, self.crop_h = right - left, bottom - top

        self._update_overlay()
        self.on_change(self.crop_x, self.crop_y, self.crop_w, self.crop_h)

    def _on_release(self, _event: tk.Event) -> None:
        self.drag_mode = None
        self.drag_start = None
        self.initial_crop = None


class WindyImageTool(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Windy Image Tool")
        self.geometry("860x640")
        self.minsize(760, 560)

        self.output_dir = tk.StringVar(value=str(Path.cwd() / "output"))
        self.status = tk.StringVar(value="Ready")

        self.convert_path = tk.StringVar()
        self.convert_format = tk.StringVar(value="PNG")

        self.crop_path = tk.StringVar()
        self.crop_x = tk.IntVar(value=0)
        self.crop_y = tk.IntVar(value=0)
        self.crop_w = tk.IntVar(value=1)
        self.crop_h = tk.IntVar(value=1)
        self._crop_syncing = False

        self.resize_path = tk.StringVar()
        self.resize_w = tk.IntVar(value=800)
        self.resize_h = tk.IntVar(value=600)
        self.preserve_aspect = tk.BooleanVar(value=True)
        self._aspect_ratio = 1.0
        self._resize_syncing = False

        self.compress_path = tk.StringVar()
        self.use_target_size = tk.BooleanVar(value=False)
        self.target_kb = tk.IntVar(value=500)

        self.rotate_path = tk.StringVar()
        self.rotate_degrees = tk.IntVar(value=90)
        self.rotate_direction = tk.StringVar(value="right")

        self.flip_path = tk.StringVar()
        self.flip_axis = tk.StringVar(value="horizontal")

        self.hue_path = tk.StringVar()
        self.hue_shift = tk.IntVar(value=0)
        self._hue_source: Image.Image | None = None
        self._hue_preview_job: str | None = None

        self.settings = load_settings()
        self.settings_font_size = tk.IntVar(value=self.settings["font_size"])
        self.settings_bg_color = tk.StringVar(value=self.settings["background_color"])
        self.settings_text_color = tk.StringVar(value=self.settings["text_color"])
        self._settings_window: tk.Toplevel | None = None
        self.bg_swatch: tk.Label | None = None
        self.text_swatch: tk.Label | None = None
        self._window_size: tuple[int, int] = (0, 0)
        self._heavy_panels: list[dict] = []
        self._panels_hidden = False
        self._last_root_geom: tuple[int, int, int, int] | None = None
        self._motion_end_job: str | None = None
        self.notebook: ttk.Notebook | None = None

        self._build_styles()
        self._build_layout()
        self._apply_appearance()
        self.bind("<Configure>", self._on_root_configure)
        self.after(200, self._start_geometry_watch)

    def _register_heavy_panel(self, tab: str, widget: tk.Widget, placeholder: tk.Widget, pack_opts: dict) -> None:
        self._heavy_panels.append(
            {
                "tab": tab,
                "widget": widget,
                "placeholder": placeholder,
                "pack": pack_opts,
            }
        )

    def _start_geometry_watch(self) -> None:
        if not self.winfo_exists():
            return
        try:
            geom = (self.winfo_rootx(), self.winfo_rooty(), self.winfo_width(), self.winfo_height())
        except tk.TclError:
            self.after(50, self._start_geometry_watch)
            return

        if self._last_root_geom is not None and geom != self._last_root_geom:
            self._begin_window_motion()
            if self._motion_end_job is not None:
                self.after_cancel(self._motion_end_job)
            self._motion_end_job = self.after(120, self._end_window_motion)

        self._last_root_geom = geom
        self.after(30, self._start_geometry_watch)

    def _begin_window_motion(self) -> None:
        if self._panels_hidden:
            return
        self._panels_hidden = True
        for panel in self._heavy_panels:
            if panel["widget"].winfo_ismapped():
                panel["widget"].pack_forget()
            if not panel["placeholder"].winfo_ismapped():
                panel["placeholder"].pack(**panel["pack"])

    def _end_window_motion(self) -> None:
        self._motion_end_job = None
        self._panels_hidden = False
        for panel in self._heavy_panels:
            panel["placeholder"].pack_forget()
        self._sync_visible_heavy_panels(force_redraw=True)

    def _sync_visible_heavy_panels(self, force_redraw: bool = False) -> None:
        if self.notebook is None or self._panels_hidden:
            return
        current = self.notebook.tab(self.notebook.select(), "text")
        for panel in self._heavy_panels:
            widget = panel["widget"]
            if panel["tab"] == current:
                if not widget.winfo_ismapped():
                    widget.pack(**panel["pack"])
                if force_redraw and hasattr(widget, "redraw"):
                    widget.redraw(force_image=True)
            elif widget.winfo_ismapped():
                widget.pack_forget()

    def _on_tab_changed(self, _event: tk.Event | None = None) -> None:
        self._sync_visible_heavy_panels(force_redraw=True)

    def _on_root_configure(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        self._window_size = (event.width, event.height)

    def _refresh_canvases(self) -> None:
        self._sync_visible_heavy_panels(force_redraw=True)

    def _build_styles(self) -> None:
        self.style = ttk.Style(self)
        if "vista" in self.style.theme_names():
            self.style.theme_use("vista")

    def _apply_appearance(self) -> None:
        bg = self.settings["background_color"]
        text = self.settings["text_color"]
        size = self.settings["font_size"]
        font = ("Segoe UI", size)
        header_font = ("Segoe UI", size + 1, "bold")
        muted = dim_color(text)

        self.configure(bg=bg)
        for widget in (
            ".",
            "TFrame",
            "TLabel",
            "TButton",
            "TRadiobutton",
            "TCheckbutton",
            "TNotebook",
            "TLabelframe",
        ):
            self.style.configure(widget, background=bg, font=font, foreground=text)
        self.style.configure("Header.TLabel", background=bg, font=header_font, foreground=text)
        self.style.configure("Status.TLabel", background=bg, font=font, foreground=text)
        self.style.configure("Muted.TLabel", background=bg, font=font, foreground=muted)
        self.style.configure("TNotebook.Tab", padding=(12, max(4, size // 2)), font=font, background=bg, foreground=text)
        self.style.configure("TEntry", fieldbackground="white", font=font, foreground=text)
        self.style.configure("TCombobox", fieldbackground="white", font=font, foreground=text)
        self.style.configure("TSpinbox", fieldbackground="white", font=font, foreground=text)
        self.style.configure("Horizontal.TScale", background=bg)

        if hasattr(self, "bg_swatch") and self.bg_swatch is not None and self.bg_swatch.winfo_exists():
            self.bg_swatch.configure(bg=bg)
        if hasattr(self, "text_swatch") and self.text_swatch is not None and self.text_swatch.winfo_exists():
            self.text_swatch.configure(bg=text)

        for panel in self._heavy_panels:
            panel["placeholder"].configure(bg=bg)
        for widget in (getattr(self, "crop_canvas", None), getattr(self, "hue_preview", None)):
            if widget is not None and hasattr(widget, "apply_theme"):
                widget.apply_theme(bg, text)
        if not self._panels_hidden:
            self._sync_visible_heavy_panels()

    def _build_layout(self) -> None:
        header = ttk.Frame(self, padding=(12, 10))
        header.pack(fill="x")
        ttk.Label(header, text="Windy Image Tool", style="Header.TLabel").pack(side="left")
        ttk.Button(header, text="Settings", command=self._open_settings).pack(side="right")

        output_row = ttk.Frame(self, padding=(12, 0, 12, 8))
        output_row.pack(fill="x")
        ttk.Label(output_row, text="Output folder:").pack(side="left")
        ttk.Entry(output_row, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(output_row, text="Browse", command=self._choose_output_dir).pack(side="left")

        notebook = ttk.Notebook(self, padding=(12, 0))
        notebook.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.notebook = notebook
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_convert_tab(notebook)
        self._build_crop_tab(notebook)
        self._build_resize_tab(notebook)
        self._build_compress_tab(notebook)
        self._build_rotate_tab(notebook)
        self._build_flip_tab(notebook)
        self._build_hue_tab(notebook)

        status_bar = ttk.Label(self, textvariable=self.status, style="Status.TLabel", padding=(12, 6))
        status_bar.pack(fill="x")
        self.after_idle(self._sync_visible_heavy_panels)

    def _build_convert_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Convert")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Image:").pack(side="left")
        ttk.Entry(row, textvariable=self.convert_path).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=lambda: self._pick_file(self.convert_path)).pack(side="left")

        format_row = ttk.Frame(frame)
        format_row.pack(fill="x", pady=(0, 16))
        ttk.Label(format_row, text="Output type:").pack(side="left")
        ttk.Combobox(
            format_row,
            textvariable=self.convert_format,
            values=list(FORMAT_EXTENSIONS.keys()),
            state="readonly",
            width=12,
        ).pack(side="left", padx=8)

        ttk.Button(frame, text="Convert", command=self._run_convert).pack(anchor="w")

    def _build_crop_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Crop")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Image:").pack(side="left")
        ttk.Entry(row, textvariable=self.crop_path).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=self._load_crop_image).pack(side="left")

        self.crop_canvas = CropCanvas(
            frame,
            on_change=self._on_crop_canvas_change,
            canvas_bg=self.settings["background_color"],
            text_color=self.settings["text_color"],
            height=360,
        )
        crop_pack = {"fill": "both", "expand": True, "pady": (0, 10)}
        self.crop_preview_placeholder = tk.Frame(frame, bg=self.settings["background_color"], height=360)
        self._register_heavy_panel("Crop", self.crop_canvas, self.crop_preview_placeholder, crop_pack)

        bounds = ttk.Frame(frame)
        bounds.pack(fill="x", pady=(0, 10))
        for label, var in [("X", self.crop_x), ("Y", self.crop_y), ("Width", self.crop_w), ("Height", self.crop_h)]:
            cell = ttk.Frame(bounds)
            cell.pack(side="left", padx=(0, 12))
            ttk.Label(cell, text=label).pack(side="left")
            spin = ttk.Spinbox(cell, from_=0, to=10000, textvariable=var, width=8, command=self._on_crop_fields_change)
            spin.pack(side="left", padx=(4, 0))
            spin.bind("<KeyRelease>", lambda _e: self._on_crop_fields_change())

        ttk.Button(frame, text="Crop", command=self._run_crop).pack(anchor="w")

    def _build_resize_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Resize")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Image:").pack(side="left")
        ttk.Entry(row, textvariable=self.resize_path).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=self._load_resize_image).pack(side="left")

        size_row = ttk.Frame(frame)
        size_row.pack(fill="x", pady=(0, 10))
        ttk.Label(size_row, text="Width:").pack(side="left")
        width_spin = ttk.Spinbox(size_row, from_=1, to=20000, textvariable=self.resize_w, width=10)
        width_spin.pack(side="left", padx=(6, 16))
        width_spin.bind("<KeyRelease>", lambda _e: self._on_width_change())
        width_spin.configure(command=self._on_width_change)

        ttk.Label(size_row, text="Height:").pack(side="left")
        height_spin = ttk.Spinbox(size_row, from_=1, to=20000, textvariable=self.resize_h, width=10)
        height_spin.pack(side="left", padx=6)
        height_spin.bind("<KeyRelease>", lambda _e: self._on_height_change())
        height_spin.configure(command=self._on_height_change)

        ttk.Checkbutton(
            frame,
            text="Preserve aspect ratio",
            variable=self.preserve_aspect,
        ).pack(anchor="w", pady=(0, 16))

        ttk.Button(frame, text="Resize", command=self._run_resize).pack(anchor="w")

    def _build_compress_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Compress")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Image:").pack(side="left")
        ttk.Entry(row, textvariable=self.compress_path).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=lambda: self._pick_file(self.compress_path)).pack(side="left")

        target_row = ttk.Frame(frame)
        target_row.pack(fill="x", pady=(0, 16))
        ttk.Checkbutton(
            target_row,
            text="Use target size (KB)",
            variable=self.use_target_size,
            command=self._toggle_target_size,
        ).pack(side="left")
        self.target_spin = ttk.Spinbox(
            target_row,
            from_=16,
            to=50000,
            textvariable=self.target_kb,
            width=10,
            state="disabled",
        )
        self.target_spin.pack(side="left", padx=8)

        ttk.Label(
            frame,
            text="Auto mode aims for roughly 70% of the original file size.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 16))

        ttk.Button(frame, text="Compress", command=self._run_compress).pack(anchor="w")

    def _build_rotate_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Rotate")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Image:").pack(side="left")
        ttk.Entry(row, textvariable=self.rotate_path).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=lambda: self._pick_file(self.rotate_path)).pack(side="left")

        angle_row = ttk.Frame(frame)
        angle_row.pack(fill="x", pady=(0, 10))
        ttk.Label(angle_row, text="Angle:").pack(side="left")
        for degrees in (90, 180, 270):
            ttk.Radiobutton(
                angle_row,
                text=f"{degrees}°",
                variable=self.rotate_degrees,
                value=degrees,
            ).pack(side="left", padx=(8 if degrees == 90 else 4, 4))

        direction_row = ttk.Frame(frame)
        direction_row.pack(fill="x", pady=(0, 16))
        ttk.Label(direction_row, text="Direction:").pack(side="left")
        ttk.Radiobutton(
            direction_row,
            text="Right (clockwise)",
            variable=self.rotate_direction,
            value="right",
        ).pack(side="left", padx=(8, 4))
        ttk.Radiobutton(
            direction_row,
            text="Left (counter-clockwise)",
            variable=self.rotate_direction,
            value="left",
        ).pack(side="left", padx=4)
        ttk.Label(
            frame,
            text="180° rotation is the same in either direction.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 16))

        ttk.Button(frame, text="Rotate", command=self._run_rotate).pack(anchor="w")

    def _build_flip_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Flip")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Image:").pack(side="left")
        ttk.Entry(row, textvariable=self.flip_path).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=lambda: self._pick_file(self.flip_path)).pack(side="left")

        axis_row = ttk.Frame(frame)
        axis_row.pack(fill="x", pady=(0, 16))
        ttk.Label(axis_row, text="Axis:").pack(side="left")
        ttk.Radiobutton(
            axis_row,
            text="Horizontal (mirror left-right)",
            variable=self.flip_axis,
            value="horizontal",
        ).pack(side="left", padx=(8, 4))
        ttk.Radiobutton(
            axis_row,
            text="Vertical (mirror top-bottom)",
            variable=self.flip_axis,
            value="vertical",
        ).pack(side="left", padx=4)

        ttk.Button(frame, text="Flip", command=self._run_flip).pack(anchor="w")

    def _build_hue_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Hue")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Image:").pack(side="left")
        ttk.Entry(row, textvariable=self.hue_path).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=self._load_hue_image).pack(side="left")

        self.hue_preview = ImagePreviewLabel(
            frame,
            placeholder="Load an image to adjust hue",
            canvas_bg=self.settings["background_color"],
            text_color=self.settings["text_color"],
            height=320,
        )
        hue_pack = {"fill": "both", "expand": True, "pady": (0, 10)}
        self.hue_preview_placeholder = tk.Frame(frame, bg=self.settings["background_color"], height=320)
        self._register_heavy_panel("Hue", self.hue_preview, self.hue_preview_placeholder, hue_pack)

        slider_row = ttk.Frame(frame)
        slider_row.pack(fill="x", pady=(0, 10))
        ttk.Label(slider_row, text="Hue shift:").pack(side="left")
        self.hue_slider = ttk.Scale(
            slider_row,
            from_=-180,
            to=180,
            orient="horizontal",
            command=self._on_hue_slider,
        )
        self.hue_slider.pack(side="left", fill="x", expand=True, padx=8)
        self.hue_value_label = ttk.Label(slider_row, text="0°", width=6)
        self.hue_value_label.pack(side="left")

        ttk.Button(frame, text="Export", command=self._run_hue).pack(anchor="w")

    def _open_settings(self) -> None:
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            return

        window = tk.Toplevel(self)
        window.title("Settings")
        window.transient(self)
        window.resizable(False, False)
        window.grab_set()
        self._settings_window = window

        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)

        font_row = ttk.Frame(frame)
        font_row.pack(fill="x", pady=(0, 12))
        ttk.Label(font_row, text="Font size:").pack(side="left")
        ttk.Spinbox(font_row, from_=8, to=24, textvariable=self.settings_font_size, width=8).pack(side="left", padx=(8, 0))

        color_row = ttk.Frame(frame)
        color_row.pack(fill="x", pady=(0, 12))
        ttk.Label(color_row, text="Background color:").pack(side="left")
        ttk.Entry(color_row, textvariable=self.settings_bg_color, width=12).pack(side="left", padx=(8, 8))
        self.bg_swatch = tk.Label(color_row, width=3, relief="solid", bg=self.settings_bg_color.get())
        self.bg_swatch.pack(side="left", padx=(0, 8))
        ttk.Button(color_row, text="Choose color", command=self._choose_background_color).pack(side="left")

        text_row = ttk.Frame(frame)
        text_row.pack(fill="x", pady=(0, 12))
        ttk.Label(text_row, text="Text color:").pack(side="left")
        ttk.Entry(text_row, textvariable=self.settings_text_color, width=12).pack(side="left", padx=(8, 8))
        self.text_swatch = tk.Label(text_row, width=3, relief="solid", bg=self.settings_text_color.get())
        self.text_swatch.pack(side="left", padx=(0, 8))
        ttk.Button(text_row, text="Choose color", command=self._choose_text_color).pack(side="left")

        ttk.Label(
            frame,
            text="Settings are saved on your computer and apply when you click Apply.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 16))

        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Button(actions, text="Apply", command=self._apply_settings).pack(side="left")
        ttk.Button(actions, text="Reset defaults", command=self._reset_settings).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Close", command=lambda: self._close_settings(window)).pack(side="right")

        window.protocol("WM_DELETE_WINDOW", lambda: self._close_settings(window))

    def _close_settings(self, window: tk.Toplevel) -> None:
        window.grab_release()
        window.destroy()
        self._settings_window = None
        self.bg_swatch = None
        self.text_swatch = None

    def _choose_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_dir.set(folder)

    def _pick_file(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(title="Select image", filetypes=IMAGE_TYPES)
        if path:
            var.set(path)

    def _load_crop_image(self) -> None:
        path = filedialog.askopenfilename(title="Select image", filetypes=IMAGE_TYPES)
        if not path:
            return
        self.crop_path.set(path)
        image = load_image(path)
        self.crop_canvas.set_image(image)
        self._sync_visible_heavy_panels(force_redraw=True)

    def _load_resize_image(self) -> None:
        path = filedialog.askopenfilename(title="Select image", filetypes=IMAGE_TYPES)
        if not path:
            return
        self.resize_path.set(path)
        image = load_image(path)
        self._aspect_ratio = image.width / image.height if image.height else 1.0
        self._resize_syncing = True
        self.resize_w.set(image.width)
        self.resize_h.set(image.height)
        self._resize_syncing = False

    def _on_crop_canvas_change(self, x: int, y: int, width: int, height: int) -> None:
        if self._crop_syncing:
            return
        self._crop_syncing = True
        self.crop_x.set(x)
        self.crop_y.set(y)
        self.crop_w.set(width)
        self.crop_h.set(height)
        self._crop_syncing = False

    def _on_crop_fields_change(self) -> None:
        if self._crop_syncing:
            return
        self._crop_syncing = True
        self.crop_canvas.set_crop(self.crop_x.get(), self.crop_y.get(), self.crop_w.get(), self.crop_h.get())
        self._crop_syncing = False

    def _on_width_change(self) -> None:
        if self._resize_syncing or not self.preserve_aspect.get():
            return
        self._resize_syncing = True
        width = max(1, self.resize_w.get())
        height = max(1, round(width / self._aspect_ratio))
        self.resize_h.set(height)
        self._resize_syncing = False

    def _on_height_change(self) -> None:
        if self._resize_syncing or not self.preserve_aspect.get():
            return
        self._resize_syncing = True
        height = max(1, self.resize_h.get())
        width = max(1, round(height * self._aspect_ratio))
        self.resize_w.set(width)
        self._resize_syncing = False

    def _toggle_target_size(self) -> None:
        state = "normal" if self.use_target_size.get() else "disabled"
        self.target_spin.configure(state=state)

    def _load_hue_image(self) -> None:
        path = filedialog.askopenfilename(title="Select image", filetypes=IMAGE_TYPES)
        if not path:
            return
        self.hue_path.set(path)
        self._hue_source = load_image(path)
        self.hue_shift.set(0)
        self.hue_slider.set(0)
        self.hue_value_label.configure(text="0°")
        self.hue_preview.set_image(self._hue_source)
        self._sync_visible_heavy_panels(force_redraw=True)

    def _on_hue_slider(self, value: str) -> None:
        if not self._hue_source:
            return
        degrees = int(round(float(value)))
        self.hue_shift.set(degrees)
        self.hue_value_label.configure(text=f"{degrees}°")
        if self._hue_preview_job is not None:
            self.after_cancel(self._hue_preview_job)
        self._hue_preview_job = self.after(60, lambda: self._refresh_hue_preview(degrees))

    def _refresh_hue_preview(self, degrees: int) -> None:
        self._hue_preview_job = None
        if not self._hue_source:
            return
        preview = shift_hue(self._hue_source, degrees)
        self.hue_preview.set_image(preview)

    def _choose_background_color(self) -> None:
        chosen = colorchooser.askcolor(
            color=self.settings_bg_color.get(),
            title="Choose background color",
        )
        if chosen[1]:
            self.settings_bg_color.set(chosen[1])
            if self.bg_swatch is not None and self.bg_swatch.winfo_exists():
                self.bg_swatch.configure(bg=chosen[1])

    def _choose_text_color(self) -> None:
        chosen = colorchooser.askcolor(
            color=self.settings_text_color.get(),
            title="Choose text color",
        )
        if chosen[1]:
            self.settings_text_color.set(chosen[1])
            if self.text_swatch is not None and self.text_swatch.winfo_exists():
                self.text_swatch.configure(bg=chosen[1])

    def _apply_settings(self) -> None:
        try:
            font_size = int(self.settings_font_size.get())
        except tk.TclError:
            messagebox.showerror("Invalid setting", "Font size must be a number.")
            return
        if font_size < 8 or font_size > 24:
            messagebox.showerror("Invalid setting", "Font size must be between 8 and 24.")
            return

        background = self.settings_bg_color.get().strip()
        if not is_valid_color(background):
            messagebox.showerror("Invalid setting", "Background color must be a hex value like #f2f2f2.")
            return

        text_color = self.settings_text_color.get().strip()
        if not is_valid_color(text_color):
            messagebox.showerror("Invalid setting", "Text color must be a hex value like #1a1a1a.")
            return

        self.settings = {
            "font_size": font_size,
            "background_color": background,
            "text_color": text_color,
        }
        save_settings(self.settings)
        self._apply_appearance()
        self.status.set("Settings applied")

    def _reset_settings(self) -> None:
        self.settings = dict(DEFAULT_SETTINGS)
        self.settings_font_size.set(self.settings["font_size"])
        self.settings_bg_color.set(self.settings["background_color"])
        self.settings_text_color.set(self.settings["text_color"])
        save_settings(self.settings)
        self._apply_appearance()
        self.status.set("Settings reset to defaults")

    def _validate_source(self, path: str) -> Path | None:
        if not path:
            messagebox.showwarning("Missing image", "Please select an image first.")
            return None
        source = Path(path)
        if not source.is_file():
            messagebox.showerror("Invalid file", "The selected image could not be found.")
            return None
        return source

    def _run_convert(self) -> None:
        source = self._validate_source(self.convert_path.get())
        if not source:
            return
        try:
            output = convert_image(source, self.output_dir.get(), self.convert_format.get())
            self.status.set(f"Converted to {output.name}")
            messagebox.showinfo("Done", f"Saved to:\n{output}")
        except Exception as exc:
            messagebox.showerror("Convert failed", str(exc))

    def _run_crop(self) -> None:
        source = self._validate_source(self.crop_path.get())
        if not source:
            return
        try:
            output = crop_image(
                source,
                self.output_dir.get(),
                self.crop_x.get(),
                self.crop_y.get(),
                self.crop_w.get(),
                self.crop_h.get(),
            )
            self.status.set(f"Cropped to {output.name}")
            messagebox.showinfo("Done", f"Saved to:\n{output}")
        except Exception as exc:
            messagebox.showerror("Crop failed", str(exc))

    def _run_resize(self) -> None:
        source = self._validate_source(self.resize_path.get())
        if not source:
            return
        try:
            output = resize_image(
                source,
                self.output_dir.get(),
                self.resize_w.get(),
                self.resize_h.get(),
            )
            self.status.set(f"Resized to {output.name}")
            messagebox.showinfo("Done", f"Saved to:\n{output}")
        except Exception as exc:
            messagebox.showerror("Resize failed", str(exc))

    def _run_compress(self) -> None:
        source = self._validate_source(self.compress_path.get())
        if not source:
            return
        try:
            target = self.target_kb.get() if self.use_target_size.get() else None
            output, size = compress_image(source, self.output_dir.get(), target_kb=target)
            kb = size / 1024
            self.status.set(f"Compressed to {output.name} ({kb:.1f} KB)")
            messagebox.showinfo("Done", f"Saved to:\n{output}\n\nSize: {kb:.1f} KB")
        except Exception as exc:
            messagebox.showerror("Compress failed", str(exc))

    def _run_rotate(self) -> None:
        source = self._validate_source(self.rotate_path.get())
        if not source:
            return
        try:
            output = rotate_image(
                source,
                self.output_dir.get(),
                self.rotate_degrees.get(),
                self.rotate_direction.get(),
            )
            self.status.set(f"Rotated to {output.name}")
            messagebox.showinfo("Done", f"Saved to:\n{output}")
        except Exception as exc:
            messagebox.showerror("Rotate failed", str(exc))

    def _run_flip(self) -> None:
        source = self._validate_source(self.flip_path.get())
        if not source:
            return
        try:
            output = flip_image(source, self.output_dir.get(), self.flip_axis.get())
            self.status.set(f"Flipped to {output.name}")
            messagebox.showinfo("Done", f"Saved to:\n{output}")
        except Exception as exc:
            messagebox.showerror("Flip failed", str(exc))

    def _run_hue(self) -> None:
        source = self._validate_source(self.hue_path.get())
        if not source:
            return
        try:
            output = adjust_hue_image(source, self.output_dir.get(), self.hue_shift.get())
            self.status.set(f"Hue adjusted to {output.name}")
            messagebox.showinfo("Done", f"Saved to:\n{output}")
        except Exception as exc:
            messagebox.showerror("Hue adjust failed", str(exc))


def run() -> None:
    ensure_output_dir(Path.cwd() / "output")
    app = WindyImageTool()
    app.mainloop()
