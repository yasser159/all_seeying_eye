from __future__ import annotations

from typing import Callable

from .log_types import LogEntry
from .logger import emit
from .notifier import Notifier

try:
    import objc  # type: ignore
    from Foundation import NSObject
    from UserNotifications import (
        UNAuthorizationOptionAlert,
        UNAuthorizationOptionSound,
        UNMutableNotificationContent,
        UNNotificationAction,
        UNNotificationCategory,
        UNNotificationRequest,
        UNNotificationResponse,
        UNUserNotificationCenter,
    )

    HAS_MACOS = True
except Exception:  # pragma: no cover
    HAS_MACOS = False
    NSObject = object  # type: ignore


ACTION_OPEN = "OPEN_DIAGNOSTICS"
CATEGORY_ID = "ALL_SEEING_EYE"


if HAS_MACOS:
    class NotificationDelegate(NSObject):
        def initWithCallback_(self, callback):
            self = objc.super(NotificationDelegate, self).init()
            if self is None:
                return None
            self._callback = callback
            return self

        def userNotificationCenter_didReceiveNotificationResponse_withCompletionHandler_(
            self, center, response, completionHandler
        ):
            action_id = response.actionIdentifier()
            if action_id == ACTION_OPEN:
                self._callback("open_diagnostics")
            completionHandler()


class MacOSNotifier(Notifier):
    def __init__(self, on_action: Callable[[str], None]) -> None:
        super().__init__(on_action)
        self._enabled = False
        self._delegate = None
        if HAS_MACOS:
            center = UNUserNotificationCenter.currentNotificationCenter()
            center.requestAuthorizationWithOptions_completionHandler_(
                UNAuthorizationOptionAlert | UNAuthorizationOptionSound, lambda granted, error: None
            )
            action = UNNotificationAction.actionWithIdentifier_title_options_(
                ACTION_OPEN, "Open Diagnostics", 0
            )
            category = UNNotificationCategory.categoryWithIdentifier_actions_intentIdentifiers_options_(
                CATEGORY_ID, [action], [], 0
            )
            center.setNotificationCategories_({category})
            self._delegate = NotificationDelegate.alloc().initWithCallback_(self.handle_action)
            center.setDelegate_(self._delegate)
            self._enabled = True
            emit("info", "MacOSNotifierReady", {})
        else:
            emit("warn", "MacOSNotifierUnavailable", {})

    def notify(self, entry: LogEntry) -> None:
        super().notify(entry)
        if not self._enabled:
            return
        content = UNMutableNotificationContent.alloc().init()
        content.setTitle_(f"{entry.level.upper()} Error")
        content.setBody_(entry.message)
        content.setCategoryIdentifier_(CATEGORY_ID)
        request = UNNotificationRequest.requestWithIdentifier_content_trigger_(
            entry.id, content, None
        )
        center = UNUserNotificationCenter.currentNotificationCenter()
        center.addNotificationRequest_withCompletionHandler_(request, lambda error: None)
