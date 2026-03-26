from PySide6.QtCore import QSettings

from app.config.inspection_items import INSPECTION_ITEMS
from app.config.result_dashboard_config import (
    SESSION_DASHBOARD_WIDGETS,
    SESSION_TABLE_COLUMNS,
)


class AppSettings:
    def __init__(self):
        self.settings = QSettings("PPEGuard", "DesktopClient")

    def get_server_url(self, default="http://127.0.0.1:5000"):
        return self.settings.value("server_url", default)

    def save_server_url(self, url: str):
        self.settings.setValue("server_url", url)

    def get_selected_inspection_items(self):
        valid_keys = {item["key"] for item in INSPECTION_ITEMS}
        default_keys = [
            item["key"]
            for item in INSPECTION_ITEMS
            if item["implemented"] and item["default_selected"]
        ]
        selected = self.settings.value("selected_inspection_items", default_keys)
        if isinstance(selected, str):
            selected = [selected]
        selected_keys = list(selected or default_keys)
        filtered_keys = [key for key in selected_keys if key in valid_keys]
        return filtered_keys or default_keys

    def save_selected_inspection_items(self, item_keys: list[str]):
        valid_keys = {item["key"] for item in INSPECTION_ITEMS}
        filtered_keys = [key for key in item_keys if key in valid_keys]
        self.settings.setValue("selected_inspection_items", filtered_keys)

    def get_visible_dashboard_widgets(self):
        default_keys = [item["key"] for item in SESSION_DASHBOARD_WIDGETS]
        selected = self.settings.value("visible_dashboard_widgets", default_keys)
        if isinstance(selected, str):
            return [selected]
        return list(selected or default_keys)

    def save_visible_dashboard_widgets(self, widget_keys: list[str]):
        self.settings.setValue("visible_dashboard_widgets", widget_keys)

    def get_visible_result_columns(self):
        default_keys = [
            item["key"] for item in SESSION_TABLE_COLUMNS if item["default_visible"]
        ]
        selected = self.settings.value("visible_result_columns", default_keys)
        if isinstance(selected, str):
            return [selected]
        return list(selected or default_keys)

    def save_visible_result_columns(self, column_keys: list[str]):
        self.settings.setValue("visible_result_columns", column_keys)
