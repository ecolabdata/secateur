"""Feedback helper extracted from...utils.
Exports:
- update_feedback
- report_layer_metrics
"""

from qgis.core import QgsProcessingFeedback

from ..intersection.intersection_metrics import LayerMetrics


def update_feedback(feedback: QgsProcessingFeedback | None, progress: int, message: str) -> None:
    """Convenient helper to update ``feedback`` if it is provided."""
    if feedback:
        feedback.setProgress(progress)
        feedback.pushInfo(message)


def report_layer_metrics(
    feedback: QgsProcessingFeedback,
    layer_name: str,
    metrics: LayerMetrics,
) -> None:
    """Report layer metrics and warnings if the total time exceeds 10 seconds."""
    # Calculate total time
    layer_total = metrics.bbox_seconds + metrics.reproj_seconds + metrics.extract_seconds

    # Report metrics
    feedback.pushInfo(
        f"bbox={metrics.bbox_seconds:.2f}s reproj={metrics.reproj_seconds:.2f}s extract={metrics.extract_seconds:.2f}s"
    )

    # Warn if slow
    if layer_total > 10.0:
        feedback.pushWarning(f"Couche lente : {layer_name} ({layer_total:.1f}s)")
