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

import os
import xml.etree.ElementTree as ET

from gi.repository import Adw, GdkPixbuf, Gio, Gtk


@Gtk.Template(resource_path="/io/github/cleomenezesjr/aurea/window.ui")
class AureaWindow(Adw.ApplicationWindow):
    """

    Attributes: 
        __gtype_name__: 
        window_title: 
        main_card: 
        icon: 
        title: 
        description: 
    """
    __gtype_name__ = "AureaWindow"

    window_title: Adw.WindowTitle = Gtk.Template.Child()
    main_card: Gtk.Box = Gtk.Template.Child()
    icon: Gtk.Image = Gtk.Template.Child()
    title: Gtk.Label = Gtk.Template.Child()
    description: Gtk.Label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Gtk.Template.Callback()
    def open_file_dialog(self, action: Gtk.Button) -> None:
        """

        Args:
            action:
        """
        dialog = Gtk.FileDialog()
        dialog.open(self, None, self.on_file_opened)

    def on_file_opened(self, dialog: Gtk.FileDialog, result: Gio.Task) -> None:
        """

        Args:
            dialog:
            result:

        Returns:

        """
        file = dialog.open_finish(result)

        if not file:
            return None

        def open_file(file) -> Gio.File:
            return file.load_contents_async(None, self.open_file_complete)

        open_file(file)

    def open_file_complete(self, file, result: Gio.Task) -> None:
        """

        Args:
            file ():
            result:

        Returns:

        """
        info: Gio.Task = file.query_info(
            "standard::name",
            Gio.FileQueryInfoFlags.NONE,
            None,
        )

        contents = file.load_contents_finish(result)

        if not contents[0]:
            print(f"Unable to open {path}: {contents[1]}")
            return None

        path = file.peek_path()
        file_name = info.get_name()
        self.window_title.set_subtitle(file_name)

        icon_path = self.get_icon_file_path(
            metadata_path=path, metadata_file_name=file_name
        )
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            icon_path,
            width=-1,
            height=380,
            preserve_aspect_ratio=True,
        )
        self.icon.set_from_pixbuf(pixbuf)

        xml_tree = ET.parse(file.get_path())
        self.title.set_label(xml_tree.find("name").text)
        self.description.set_label(xml_tree.find("summary").text)

    def get_icon_file_path(
        self, metadata_path: str, metadata_file_name: str
    ) -> str:
        """

        Args:
            metadata_path: 
            metadata_file_name: 

        Returns:
            
        """
        metadata_path: str = metadata_path.replace(metadata_file_name, "")
        icon_name: str = metadata_file_name.replace("metainfo.xml.in", "svg")

        for root, dirs, files in os.walk(metadata_path):
            if icon_name in files:
                return os.path.join(root, icon_name)
