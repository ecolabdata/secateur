from dataclasses import dataclass, field


@dataclass(slots=True)
class LayerMetrics:
    bbox_seconds: float = 0.0
    reproj_seconds: float = 0.0
    extract_seconds: float = 0.0


@dataclass(slots=True)
class IntersectionMetrics:
    layers: dict[str, LayerMetrics] = field(default_factory=dict)

    def get_layer_metrics(
        self,
        layer_name: str,
    ) -> LayerMetrics:
        return self.layers.setdefault(
            layer_name,
            LayerMetrics(),
        )


def _format_metrics_summary(metrics: IntersectionMetrics) -> str:
    """Format a summary of performance metrics."""
    if not metrics.layers:
        return ""

    # Format per-layer metrics
    layer_lines = []
    total_bbox = 0.0
    total_reproj = 0.0
    total_extract = 0.0

    for layer_name, layer_metrics in metrics.layers.items():
        total_bbox += layer_metrics.bbox_seconds
        total_reproj += layer_metrics.reproj_seconds
        total_extract += layer_metrics.extract_seconds

        layer_lines.append(
            f"  {layer_name}: "
            f"bbox={layer_metrics.bbox_seconds:.2f}s, "
            f"reproj={layer_metrics.reproj_seconds:.2f}s, "
            f"extract={layer_metrics.extract_seconds:.2f}s"
        )

    # Format totals
    total_time = total_bbox + total_reproj + total_extract
    summary_lines = [
        f"Performance totale: {total_time:.2f}s",
        f"  bbox: {total_bbox:.2f}s",
        f"  reproj: {total_reproj:.2f}s",
        f"  extract: {total_extract:.2f}s",
    ]

    if layer_lines:
        summary_lines.append("")
        summary_lines.append("Détails par couche:")
        summary_lines.extend(layer_lines)

    return "\n".join(summary_lines)
