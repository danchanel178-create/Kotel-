"""Загрузка логотипа для заголовка приложения."""

from __future__ import annotations

from pathlib import Path
from tkinter import Label, PhotoImage

import customtkinter as ctk

# Фон шапки — для встраивания tk.Label
from .theme import BG_HEADER

_HEADER_BG = BG_HEADER


def attach_logo(parent: ctk.CTkFrame, logo_path: Path, size: tuple[int, int] = (40, 40)) -> object | None:
    """Показать логотип в заголовке. Возвращает ссылку на объект изображения."""
    if not logo_path.is_file():
        return None

    try:
        from PIL import Image, ImageTk

        with Image.open(logo_path) as src:
            img = src.convert("RGBA")
            img.thumbnail(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

        holder = ctk.CTkFrame(parent, fg_color="transparent", width=size[0], height=size[1])
        holder.pack(side="left", padx=(0, 12))
        holder.pack_propagate(False)

        lbl = Label(holder, image=photo, borderwidth=0, bg=_HEADER_BG, highlightthickness=0)
        lbl.image = photo  # type: ignore[attr-defined]
        lbl.place(relx=0.5, rely=0.5, anchor="center")
        return photo
    except ImportError:
        pass
    except Exception:
        pass

    try:
        photo = PhotoImage(file=str(logo_path))
        w, h = photo.width(), photo.height()
        tw, th = size
        if w > tw or h > th:
            factor = max(1, round(max(w / tw, h / th)))
            photo = photo.subsample(factor, factor)
        lbl = ctk.CTkLabel(parent, image=photo, text="")
        lbl.image = photo  # type: ignore[attr-defined]
        lbl.pack(side="left", padx=(0, 12))
        return photo
    except Exception:
        return None
