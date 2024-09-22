"""
 main.py

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

import sys

import gi

gi.require_versions({"Gtk": "4.0", "Soup": "3.0", "Adw": "1"})

if gi:
    from gi.repository import Adw, Gio, Gtk

    from .window import AureaWindow


class AureaApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(
            application_id="io.github.cleomenezesjr.aurea",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.create_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self.create_action("about", self.on_about_action)

    def do_open(self, files: list[Gio.File], _n_files: int, hint: str) -> None:
        for file in files:
            self.do_activate(file)

    def do_activate(self, file=None):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = AureaWindow(application=self)
        win.present()

        if file:
            file_info = file.query_info("standard::name", 0, None)
            win.handle_file_input(
                path=file.peek_path(),
                file_name=file_info.get_name()
            )
            win.setup_monitor_for_file(file)

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(
            application_name="Aurea",
            application_icon="io.github.cleomenezesjr.aurea",
            comments="A banner previewer for Flatpak metainfo files",
            developer_name="Cleo Menezes Jr.",
            version="1.5",
            developers=["Cleo Menezes Jr. https://github.com/CleoMenezesJr"],
            copyright="© 2024 Cleo Menezes Jr.",
            support_url="https://matrix.to/#/%23aurea-app:matrix.org",
            issue_url="https://github.com/CleoMenezesJr/Aurea/issues/new",
            license_type=Gtk.License.GPL_3_0,
            designers=["Tobias Bernard https://github.com/bertob"],
        )
        about.present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    app = AureaApplication()
    return app.run(sys.argv)
