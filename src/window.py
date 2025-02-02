"""
window.py

Copyright 2024 Cleo Menezes Jr.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import io
import logging
import os
import xml.etree.ElementTree as ET
from gettext import gettext
from threading import Event, Thread

from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk, Soup
from PIL import Image


@Gtk.Template(resource_path="/io/github/cleomenezesjr/aurea/gtk/window.ui")
class AureaWindow(Adw.ApplicationWindow):
    __gtype_name__ = "AureaWindow"

    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    stack: Gtk.Stack = Gtk.Template.Child()
    window_title: Adw.WindowTitle = Gtk.Template.Child()
    main_card: Gtk.Box = Gtk.Template.Child()
    main_card_dark: Gtk.Box = Gtk.Template.Child()
    icon: Gtk.Image = Gtk.Template.Child()
    icon_dark: Gtk.Image = Gtk.Template.Child()
    title: Gtk.Label = Gtk.Template.Child()
    title_dark: Gtk.Label = Gtk.Template.Child()
    description: Gtk.Label = Gtk.Template.Child()
    description_dark: Gtk.Label = Gtk.Template.Child()
    screenshot: Gtk.Picture = Gtk.Template.Child()
    screenshot_dark: Gtk.Picture = Gtk.Template.Child()
    screenshot_stack: Gtk.Stack = Gtk.Template.Child()
    screenshot_stack_dark: Gtk.Stack = Gtk.Template.Child()
    bin: Adw.Bin = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.style_provider = Gtk.CssProvider()
        self.style_manager = Adw.StyleManager.get_default()

        _title_dark_label = self.title_dark.get_first_child().get_first_child()
        _title_dark_label.add_css_class("card_fg_dark_color")
        _description_dark_label = (
            self.description_dark.get_first_child().get_first_child()
        )
        _description_dark_label.add_css_class("card_fg_dark_color")

        _drop_target_content = Gdk.ContentFormats.new_for_gtype(Gio.File)
        _drop_target: Gtk.DropTarget = Gtk.DropTarget(
            formats=_drop_target_content, actions=Gdk.DragAction.COPY
        )

        self.add_controller(_drop_target)

        _drop_target.connect("drop", self.on_file_drop)
        _drop_target.connect(
            "enter",
            lambda target, y, x: self.bin.add_css_class(
                "overlay-drag-area-on-enter"
            ),
        )
        _drop_target.connect(
            "leave",
            lambda target: self.bin.remove_css_class(
                "overlay-drag-area-on-enter"
            ),
        )

        self.loaded_file: Gio.File = None
        self.monitor_for_file: Gio.FileMonitor = None

        self.reload_action = Gio.SimpleAction(
            name="reload", parameter_type=None
        )
        self.reload_action.connect("activate", lambda *_: self.refresh_data())
        self.get_application().set_accels_for_action("app.reload", ["F5"])

    def on_file_drop(
        self, widget: Gtk.DropTarget, file: Gio.File, x: float, y: float
    ) -> bool | None:
        try:
            if not isinstance(file, Gio.File):
                raise Exception("Unsupported file")

            content_type: str = file.query_info(
                "standard::content-type", 0, None
            ).get_content_type()

            if content_type != "application/xml":
                raise Exception(
                    "Unsupported file type. Must be application/xml"
                )

            info = file.query_info("standard::name", 0, None)

            path: str = file.peek_path()
            file_name: str = info.get_name()

            self.setup_monitor_for_file(file)
            self.handle_file_input(path, file_name)
        except (GLib.Error, Exception):
            logging.exception("Could not load file contents")
            self.toast_overlay.add_toast(
                Adw.Toast(title=gettext("Can't load appstream"))
            )
            self.stack.props.visible_child_name = "welcome_page"
            self.get_application().remove_action("reload")
            return None

        return None

    @Gtk.Template.Callback()
    def open_file_dialog(self, action: Gtk.Button) -> None:
        filter: Gtk.FileFilter = Gtk.FileFilter()
        filter.add_mime_type("application/xml")
        dialog = Gtk.FileDialog(default_filter=filter)
        dialog.open(self, None, self.on_file_selected)

    def on_file_selected(
        self, dialog: Gtk.FileDialog, result: Gio.Task
    ) -> None | GLib.GError:
        try:
            file = dialog.open_finish(result)
        except Exception as error:
            return error

        def open_file(file) -> Gio.File:
            return file.load_contents_async(None, self.open_file_complete)

        self.setup_monitor_for_file(file)

        return open_file(file)

    def open_file_complete(self, file, result: Gio.Task) -> None:
        info: Gio.Task = file.query_info(
            "standard::name",
            Gio.FileQueryInfoFlags.NONE,
            None,
        )

        try:
            content_type: str = file.query_info(
                "standard::content-type", 0, None
            ).get_content_type()

            if content_type != "application/xml":
                raise Exception(
                    "Unsupported file type. Must be application/xml"
                )

            contents: tuple = file.load_contents_finish(result)

            if not contents[0]:
                self.stack.props.visible_child_name = "welcome_page"
                self.get_application().remove_action("reload")
                raise Exception("File without content")

        except (GLib.Error, Exception):
            logging.exception("Could not load file contents")
            self.toast_overlay.add_toast(
                Adw.Toast(title=gettext("Can't load appstream"))
            )
            self.stack.props.visible_child_name = "welcome_page"
            self.get_application().remove_action("reload")
            return None

        path: str = file.peek_path()
        file_name: str = info.get_name()
        self.handle_file_input(path, file_name)

    def handle_file_input(self, path: str, file_name: str) -> None:
        self.get_application().add_action(self.reload_action)
        self.style_manager.props.color_scheme = Adw.ColorScheme.FORCE_LIGHT

        self.window_title.set_subtitle(file_name)

        self.icon.props.icon_name = "application-x-executable-symbolic"
        self.icon_dark.props.icon_name = "application-x-executable-symbolic"
        self.get_icon_file_path(
            metainfo_path=path,
            metainfo_file_name=file_name,
        )

        xml_tree: ET = ET.parse(path)
        name: ET.Element = xml_tree.find("name")
        self.title.set_text("No name" if name is None else name.text)
        self.title_dark.set_text("No name" if name is None else name.text)
        summary: ET.Element = xml_tree.find("summary")
        self.description.set_text(
            "No summary" if summary is None else summary.text
        )
        self.description_dark.set_text(
            "No summary" if summary is None else summary.text
        )

        self.main_card.remove_css_class("main-card")
        self.main_card_dark.remove_css_class("main-card-dark")
        self.branding_colors = self.get_branding_colors(xml_tree)
        if self.branding_colors:
            self.main_card.add_css_class("main-card")
            self.main_card_dark.add_css_class("main-card-dark")
            self.set_background_card_color(self.branding_colors)

        self.set_loading_screenshot_state(True)
        screenshots_tag: ET.Element = xml_tree.find("screenshots")
        self.screenshot.props.visible = bool(screenshots_tag)
        if not screenshots_tag:
            self.toast_overlay.add_toast(
                Adw.Toast(title=gettext("No screenshot"))
            )
            self.screenshot_stack.props.visible_child_name = "no_screenshot"
            self.screenshot_stack_dark.props.visible_child_name = (
                "no_screenshot"
            )
        else:
            screenshot_url = screenshots_tag.find("screenshot").find("image")
            self.fetch_screenshot_image_bytes(screenshot_url.text.strip())

        if self.stack.props.visible_child_name == "welcome_page":
            self.stack.props.visible_child_name = "content_page"

    def get_icon_file_path(
        self,
        metainfo_path: str,
        metainfo_file_name: str,
        try_again: bool = True,
        timeout: int = 5,
    ) -> None:
        metainfo_path: str = os.path.dirname(metainfo_path)
        metainfo_str_index: str = metainfo_file_name.rfind(".xml")
        icon_name: str = (
            metainfo_file_name[:metainfo_str_index].rsplit(".", 1)[0] + ".svg"
        )

        def navigate_directories(
            self,
            metainfo_file_name: str,
            metainfo_path: str,
            stop_event: Event,
        ) -> str | None:
            icon_path: str | None = None
            for root, dirs, files in os.walk(metainfo_path):
                if stop_event.is_set():
                    return None
                if icon_name in files:
                    icon_path = os.path.join(root, icon_name)
                    break

            # Workaround: If the icon is not found in the current directory,
            # attempt to locate it in the parent directory.
            if not icon_path:
                metainfo_path: str = os.path.dirname(
                    os.path.dirname(metainfo_path)
                )
                self.get_icon_file_path(
                    metainfo_path, metainfo_file_name, False
                )
                return None

            return self.set_icon(icon_path)

        stop_event = Event()
        thread = Thread(
            target=navigate_directories,
            args=(self, metainfo_file_name, metainfo_path, stop_event),
        )

        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            stop_event.set()
            return None

        return None

    def set_icon(self, icon_path: str) -> None:
        if not icon_path:
            self.toast_overlay.add_toast(
                Adw.Toast(title=gettext("No icon found"))
            )
            return None

        try:
            pixbuf: GdkPixbuf.Pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                icon_path,
                width=380,
                height=380,
                preserve_aspect_ratio=True,
            )
        except GLib.Error:
            logging.exception("Could not load exception")
        else:
            GLib.idle_add(self.icon.set_from_pixbuf, pixbuf)
            GLib.idle_add(self.icon_dark.set_from_pixbuf, pixbuf)

    def set_screenshot_image(self, image_bytes: bytes) -> None:
        self.screenshot.props.visible = bool(image_bytes)
        if not image_bytes:
            return None

        image: Image.Image = self.crop_screenshot_bottom(image_bytes)

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_array = buf.getbuffer()
        try:
            texture = Gdk.Texture.new_from_bytes(
                GLib.Bytes(image_array),
            )
        except GLib.Error:
            logging.exception("Could not read texture from bytes")
        else:
            GLib.idle_add(self.screenshot.set_paintable, texture)
            GLib.idle_add(self.screenshot_dark.set_paintable, texture)

        self.set_loading_screenshot_state(False)

        return None

    def fetch_screenshot_image_bytes(self, url: str) -> bytes | str:
        session = Soup.Session()
        message = Soup.Message(
            method="GET", uri=GLib.Uri.parse(url, GLib.UriFlags.NONE)
        )

        def on_receive_bytes(session, result, message):
            bytes = session.send_and_read_finish(result)
            if message.get_status() != Soup.Status.OK:
                self.toast_overlay.add_toast(
                    Adw.Toast(title=gettext("Can't load screenshot"))
                )
                self.screenshot_stack.props.visible_child_name = (
                    "no_screenshot"
                )
                self.screenshot_stack_dark.props.visible_child_name = (
                    "no_screenshot"
                )
                status_code = message.props.status_code
                reason_phrase = message.props.reason_phrase
                return f"{status_code} - {reason_phrase}"

            return self.set_screenshot_image(bytes.get_data())

        session.send_and_read_async(
            message, GLib.PRIORITY_DEFAULT, None, on_receive_bytes, message
        )

    def crop_screenshot_bottom(self, image_bytes: bytes) -> Image.Image:
        image: Image = Image.open(io.BytesIO(image_bytes))
        original_width, original_height = image.size

        self.screenshot.set_content_fit(
            Gtk.ContentFit.SCALE_DOWN
            if original_width <= 700
            else Gtk.ContentFit.CONTAIN
        )
        self.screenshot_dark.set_content_fit(
            Gtk.ContentFit.SCALE_DOWN
            if original_width <= 700
            else (
                Gtk.ContentFit.COINTAINWN
                if original_width <= 700
                else Gtk.ContentFit.CONTAIN
            )
        )
        if original_width <= 700:
            return image

        new_width: int = 924
        new_height = int(new_width / original_width * original_height)
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)

        box_height: int = 394
        box = (0, 0, new_width, int(box_height * 0.93))
        cropped_image = resized_image.crop(box)

        return cropped_image

    def set_background_card_color(self, colors: dict) -> str:
        self.style_provider.load_from_string(
            f"""
            .main-card {{ background-color: {colors['light']}; }}
            .main-card-dark {{ background-color: {colors['dark']}; }}
            """
        )

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def get_branding_colors(self, xml_tree: ET) -> dict | None:
        branding = xml_tree.find("./branding")
        if branding is None:
            self.toast_overlay.add_toast(
                Adw.Toast(title=gettext("No branding colors."))
            )
            return None

        dark_color = branding.find('./color[@scheme_preference="dark"]')
        light_color = branding.find('./color[@scheme_preference="light"]')

        if light_color is None and dark_color is None:
            self.toast_overlay.add_toast(
                Adw.Toast(
                    title=gettext(
                        "Light and dark brand color have not been defined"
                    )
                )
            )
            return None

        color_scheme: dict = {
            "light": "transparent",
            "dark": "transparent",
        }

        if light_color is not None:
            color_scheme["light"] = light_color.text
        else:
            self.toast_overlay.add_toast(
                Adw.Toast(
                    title=gettext("Light brand color have not been defined")
                )
            )
        if dark_color is not None:
            color_scheme["dark"] = dark_color.text
        else:
            self.toast_overlay.add_toast(
                Adw.Toast(
                    title=gettext("Dark brand color have not been defined")
                )
            )

        return color_scheme

    def set_loading_screenshot_state(self, is_loading: bool = False) -> None:
        self.screenshot_stack.props.visible_child_name = (
            "loading_screenshot" if is_loading else "screenshot"
        )
        self.screenshot_stack_dark.props.visible_child_name = (
            "loading_screenshot" if is_loading else "screenshot"
        )
        return None

    def refresh_data(self) -> None:
        if not self.loaded_file:
            return None

        self.loaded_file.load_contents_async(None, self.open_file_complete)
        self.toast_overlay.add_toast(
            Adw.Toast(title=gettext("Banner reloaded"), timeout=2)
        )

    def setup_monitor_for_file(self, file: Gio.File) -> None:
        self.loaded_file = file
        self.monitor_for_file = self.loaded_file.monitor_file(
            Gio.FileMonitorFlags.SEND_MOVED, None
        )
        self.monitor_for_file.connect("changed", self.on_file_changed)

    def on_file_changed(
        self,
        monitor: Gio.FileMonitor,
        file: Gio.File,
        other_file: Gio.File,
        event: Gio.FileMonitorEvent,
    ) -> None:

        if event != Gio.FileMonitorEvent.MOVED:
            return None

        self.refresh_data()
