#!/usr/bin/env python3

import os
import sys
from collections import OrderedDict
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from lib.xml_parser import parse_wallpapoz_file, save_treeview_to_wallpapoz_file


APP_ID = "net.vajrasky.Wallpapoz"
STYLE_VALUES = ("centered", "stretched", "scaled", "zoom", "wallpaper")
IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".pbm",
    ".pgm",
    ".png",
    ".ppm",
    ".rast",
    ".rgb",
    ".tiff",
    ".xbm",
}


def config_path():
    return Path.home() / ".wallpapoz" / "wallpapoz.xml"


def project_root():
    return Path(__file__).resolve().parent.parent


def logo_path():
    return project_root() / "share" / "wallpapoz" / "images" / "wallpapoz.png"


def ensure_config_file(path):
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    save_treeview_to_wallpapoz_file(
        str(path),
        "workspace",
        OrderedDict(
            (
                ("Workspace 1", []),
                ("Workspace 2", []),
                ("Workspace 3", []),
                ("Workspace 4", []),
            )
        ),
        interval="5",
        random="0",
        style="2",
    )


class WallpapozWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Wallpapoz")
        self.set_default_size(980, 640)

        self.config_file = config_path()
        ensure_config_file(self.config_file)
        self.wallpapers, self.conf = parse_wallpapoz_file(str(self.config_file))
        self.wallpapoz_type = self.conf.get("type", "workspace")

        self.store = None
        self.treeview = None
        self.selection = None
        self.picture = None
        self.filename_label = None
        self.interval_spin = None
        self.random_check = None
        self.workspace_check = None
        self.style_combo = None
        self.main_paned = None

        self._install_actions()
        self.set_titlebar(self._build_headerbar())
        self.set_child(self._build_content())
        self._load_store()

    def _install_actions(self):
        actions = {
            "add-files": self.on_add_files,
            "add-folder": self.on_add_folder,
            "remove-selected": self.on_remove_selected,
            "save": self.on_save,
            "about": self.on_about,
            "quit": self.on_quit,
        }
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _action, _parameter, cb=callback: cb(None))
            self.add_action(action)

    def _build_headerbar(self):
        headerbar = Gtk.HeaderBar()

        add_files = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_files.set_tooltip_text("Add wallpaper files")
        add_files.connect("clicked", self.on_add_files)
        headerbar.pack_start(add_files)

        add_folder = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        add_folder.set_tooltip_text("Add wallpapers from folder")
        add_folder.connect("clicked", self.on_add_folder)
        headerbar.pack_start(add_folder)

        remove = Gtk.Button.new_from_icon_name("edit-delete-symbolic")
        remove.set_tooltip_text("Remove selected wallpapers")
        remove.connect("clicked", self.on_remove_selected)
        headerbar.pack_start(remove)

        save = Gtk.Button.new_from_icon_name("document-save-symbolic")
        save.set_tooltip_text("Save configuration")
        save.connect("clicked", self.on_save)
        headerbar.pack_end(save)

        about = Gtk.Button.new_from_icon_name("help-about-symbolic")
        about.set_tooltip_text("About Wallpapoz")
        about.connect("clicked", self.on_about)
        headerbar.pack_end(about)

        return headerbar

    def _build_content(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(self._build_menu_bar())

        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_wide_handle(True)
        self.main_paned.set_vexpand(True)
        self.main_paned.set_hexpand(True)
        self.main_paned.set_resize_start_child(True)
        self.main_paned.set_resize_end_child(True)
        self.main_paned.set_shrink_start_child(False)
        self.main_paned.set_shrink_end_child(False)
        self.main_paned.set_position(540)
        root.append(self.main_paned)

        self.treeview = Gtk.TreeView()
        self.treeview.set_headers_visible(True)
        self.treeview.set_vexpand(True)
        self.treeview.set_hexpand(True)

        index_renderer = Gtk.CellRendererText()
        index_column = Gtk.TreeViewColumn("Workspace", index_renderer, text=0)
        self.treeview.append_column(index_column)

        wallpaper_renderer = Gtk.CellRendererText()
        wallpaper_renderer.set_property("editable", True)
        wallpaper_renderer.connect("edited", self.on_wallpaper_edited)
        wallpaper_column = Gtk.TreeViewColumn("Wallpaper", wallpaper_renderer, text=1, editable=2)
        self.treeview.append_column(wallpaper_column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.treeview)
        scrolled.set_min_content_width(420)
        scrolled.set_min_content_height(360)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        self.main_paned.set_start_child(scrolled)

        preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        preview.set_margin_top(16)
        preview.set_margin_bottom(16)
        preview.set_margin_start(16)
        preview.set_margin_end(16)
        preview.set_size_request(320, 360)
        preview.set_vexpand(True)
        preview.set_hexpand(True)
        self.main_paned.set_end_child(preview)

        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(True)
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.set_size_request(280, 280)
        self.picture.set_vexpand(True)
        self.picture.set_hexpand(True)
        preview.append(self.picture)

        self.filename_label = Gtk.Label(label="")
        self.filename_label.set_wrap(True)
        self.filename_label.set_xalign(0)
        preview.append(self.filename_label)

        settings = Gtk.FlowBox()
        settings.set_selection_mode(Gtk.SelectionMode.NONE)
        settings.set_column_spacing(12)
        settings.set_row_spacing(8)
        settings.set_max_children_per_line(8)
        settings.set_margin_top(8)
        settings.set_margin_bottom(8)
        settings.set_margin_start(12)
        settings.set_margin_end(12)
        settings.set_vexpand(False)
        root.append(settings)

        self.interval_spin = Gtk.SpinButton.new_with_range(1, 1440, 1)
        self.interval_spin.set_value(float(self.conf.get("interval", "5")))
        settings.append(self._setting_pair("Minutes", self.interval_spin))

        self.random_check = Gtk.CheckButton(label="Random")
        self.random_check.set_active(self.conf.get("random", "0") == "1")
        settings.append(self.random_check)

        self.workspace_check = Gtk.CheckButton(label="Change by workspace")
        self.workspace_check.set_active(self.wallpapoz_type == "workspace")
        settings.append(self.workspace_check)

        self.style_combo = Gtk.ComboBoxText()
        for style in STYLE_VALUES:
            self.style_combo.append_text(style)
        self.style_combo.set_active(int(self.conf.get("style", "2")))
        settings.append(self._setting_pair("Style", self.style_combo))

        return root

    def _build_menu_bar(self):
        menubar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        menubar.append(
            self._menu_button(
                "File",
                "document-open-symbolic",
                (
                    ("Add Wallpaper Files", "list-add-symbolic", self.on_add_files),
                    ("Add Wallpaper Folder", "folder-open-symbolic", self.on_add_folder),
                    ("Save", "document-save-symbolic", self.on_save),
                    ("Quit", "application-exit-symbolic", self.on_quit),
                ),
            )
        )
        menubar.append(
            self._menu_button(
                "Edit",
                "document-edit-symbolic",
                (("Remove Selected", "edit-delete-symbolic", self.on_remove_selected),),
            )
        )
        menubar.append(
            self._menu_button(
                "Help",
                "help-about-symbolic",
                (("About Wallpapoz", "help-about-symbolic", self.on_about),),
            )
        )
        return menubar

    def _menu_button(self, label, icon_name, items):
        button = Gtk.MenuButton()
        button.add_css_class("flat")
        button.set_child(self._icon_label(icon_name, label))

        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        for item_label, item_icon_name, callback in items:
            row = Gtk.Button()
            row.add_css_class("flat")
            row.set_child(self._icon_label(item_icon_name, item_label))
            row.connect("clicked", self._on_menu_item_clicked, callback, popover)
            box.append(row)
        popover.set_child(box)
        button.set_popover(popover)
        return button

    def _icon_label(self, icon_name, label):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.append(Gtk.Image.new_from_icon_name(icon_name))
        text = Gtk.Label(label=label)
        text.set_xalign(0)
        box.append(text)
        return box

    def _on_menu_item_clicked(self, _button, callback, popover):
        popover.popdown()
        callback(None)

    def _setting_pair(self, label, widget):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.append(Gtk.Label(label=label))
        box.append(widget)
        return box

    def _load_store(self):
        if self.wallpapoz_type == "workspace":
            self.store = Gtk.TreeStore(int, str, bool)
            for index, (workspace_name, files) in enumerate(self.wallpapers, start=1):
                parent = self.store.append(None, [index, workspace_name, False])
                for file_index, filename in enumerate(files, start=1):
                    self.store.append(parent, [file_index, filename, True])
            self.treeview.get_column(0).set_title("Workspace")
        else:
            self.store = Gtk.ListStore(int, str, bool)
            for index, filename in enumerate(self.wallpapers, start=1):
                self.store.append([index, filename, True])
            self.treeview.get_column(0).set_title("No.")

        self.treeview.set_model(self.store)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.connect("cursor-changed", self.on_selection_changed)
        if len(self.store) > 0:
            self.selection.select_path(Gtk.TreePath.new_first())

    def _selected_parent_iter(self):
        model, paths = self.selection.get_selected_rows()
        if not paths:
            return self.store.get_iter_first()

        selected = self.store.get_iter(paths[-1])
        if self.wallpapoz_type != "workspace":
            return selected

        parent = self.store.iter_parent(selected)
        return parent if parent else selected

    def _add_file(self, filename):
        if self.wallpapoz_type == "workspace":
            parent = self._selected_parent_iter()
            if parent is None:
                parent = self.store.append(None, [1, "Workspace 1", False])
            next_index = self.store.iter_n_children(parent) + 1
            self.store.append(parent, [next_index, filename, True])
        else:
            self.store.append([len(self.store) + 1, filename, True])

    def _renumber(self):
        if self.wallpapoz_type == "workspace":
            parent = self.store.get_iter_first()
            workspace_index = 1
            while parent:
                self.store.set_value(parent, 0, workspace_index)
                child = self.store.iter_children(parent)
                file_index = 1
                while child:
                    self.store.set_value(child, 0, file_index)
                    file_index += 1
                    child = self.store.iter_next(child)
                workspace_index += 1
                parent = self.store.iter_next(parent)
        else:
            item = self.store.get_iter_first()
            index = 1
            while item:
                self.store.set_value(item, 0, index)
                index += 1
                item = self.store.iter_next(item)

    def _iter_is_wallpaper(self, item):
        return bool(self.store.get_value(item, 2))

    def _show_message(self, title, body):
        dialog = Gtk.AlertDialog(message=title, detail=body)
        dialog.show(self)

    def _is_dialog_cancelled(self, exc):
        message = str(exc).lower()
        return (
            (
                isinstance(exc, GLib.Error)
                and exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED)
            )
            or "dismissed by user" in message
            or "cancelled" in message
            or "canceled" in message
        )

    def on_add_files(self, _button):
        dialog = Gtk.FileDialog(title="Choose Wallpapers")
        dialog.open_multiple(self, None, self.on_add_files_done)

    def on_add_files_done(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
        except Exception as exc:
            if not self._is_dialog_cancelled(exc):
                self._show_message("Could not add files", str(exc))
            return

        for index in range(files.get_n_items()):
            self._add_file(files.get_item(index).get_path())
        self._renumber()

    def on_add_folder(self, _button):
        dialog = Gtk.FileDialog(title="Choose Wallpaper Folder")
        dialog.select_folder(self, None, self.on_add_folder_done)

    def on_add_folder_done(self, dialog, result):
        try:
            folder = Path(dialog.select_folder_finish(result).get_path())
        except Exception as exc:
            if not self._is_dialog_cancelled(exc):
                self._show_message("Could not add folder", str(exc))
            return

        for child in sorted(folder.iterdir()):
            if child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS:
                self._add_file(str(child))
        self._renumber()

    def on_remove_selected(self, _button):
        model, paths = self.selection.get_selected_rows()
        for path in reversed(paths):
            item = self.store.get_iter(path)
            if item and self._iter_is_wallpaper(item):
                self.store.remove(item)
        self._renumber()

    def on_wallpaper_edited(self, _renderer, path, new_text):
        item = self.store.get_iter(Gtk.TreePath.new_from_string(path))
        if self.wallpapoz_type == "workspace" and not self._iter_is_wallpaper(item):
            self.store.set_value(item, 1, new_text)
            return
        self.store.set_value(item, 1, new_text)

    def on_selection_changed(self, _treeview):
        if self.selection is None:
            return

        model, paths = self.selection.get_selected_rows()
        if not paths:
            return

        item = self.store.get_iter(paths[-1])
        if not self._iter_is_wallpaper(item):
            self.picture.set_paintable(None)
            self.filename_label.set_label(self.store.get_value(item, 1))
            return

        filename = self.store.get_value(item, 1)
        self.filename_label.set_label(filename)
        if os.path.exists(filename):
            self.picture.set_filename(filename)
        else:
            self.picture.set_paintable(None)

    def on_save(self, _button):
        interval = str(int(self.interval_spin.get_value()))
        random = "1" if self.random_check.get_active() else "0"
        style = str(self.style_combo.get_active())
        save_as_workspace = self.workspace_check.get_active()

        if save_as_workspace:
            elements = OrderedDict()
            if self.wallpapoz_type == "workspace":
                parent = self.store.get_iter_first()
                while parent:
                    workspace_name = self.store.get_value(parent, 1)
                    elements[workspace_name] = []
                    child = self.store.iter_children(parent)
                    while child:
                        elements[workspace_name].append(self.store.get_value(child, 1))
                        child = self.store.iter_next(child)
                    parent = self.store.iter_next(parent)
            else:
                elements["Workspace 1"] = []
                item = self.store.get_iter_first()
                while item:
                    elements["Workspace 1"].append(self.store.get_value(item, 1))
                    item = self.store.iter_next(item)
            config_type = "workspace"
        else:
            elements = []
            item = self.store.get_iter_first()
            while item:
                if self._iter_is_wallpaper(item):
                    elements.append(self.store.get_value(item, 1))
                child = self.store.iter_children(item) if self.wallpapoz_type == "workspace" else None
                while child:
                    elements.append(self.store.get_value(child, 1))
                    child = self.store.iter_next(child)
                item = self.store.iter_next(item)
            config_type = "desktop"

        save_treeview_to_wallpapoz_file(
            str(self.config_file),
            config_type,
            elements,
            interval=interval,
            random=random,
            style=style,
        )
        self._show_message("Configuration saved", str(self.config_file))

    def on_about(self, _button):
        dialog = Gtk.AboutDialog(
            transient_for=self,
            modal=True,
            program_name="Wallpapoz",
            comments="Wallpaper rotation by desktop or workspace.",
            license_type=Gtk.License.GPL_2_0,
        )
        logo_file = logo_path()
        if logo_file.exists():
            dialog.set_logo(Gdk.Texture.new_from_filename(str(logo_file)))
        dialog.present()

    def on_quit(self, _action):
        self.close()


class WallpapozApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        window = self.props.active_window
        if window is None:
            window = WallpapozWindow(self)
        window.present()


def main(argv=None):
    app = WallpapozApplication()
    return app.run(sys.argv if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
