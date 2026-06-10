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
