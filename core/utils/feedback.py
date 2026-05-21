"""Feedback helper extracted from...utils.
Exports:
- update_feedback
"""

from qgis.core import QgsProcessingFeedback


def update_feedback(feedback: QgsProcessingFeedback | None, progress: int, message: str) -> None:
    """Convenient helper to update ``feedback`` if it is provided."""
    if feedback:
        feedback.setProgress(progress)
        feedback.pushInfo(message)
