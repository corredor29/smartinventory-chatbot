import threading
from collections import defaultdict


class Metrics:
    """
    Contador en memoria, simple e intencionalmente mínimo (sin Prometheus ni
    otras dependencias) para exponer indicadores básicos de negocio y
    operación mientras el proyecto no justifique una solución de métricas
    más completa. Pensado para un solo proceso; en un despliegue con varias
    réplicas cada una tendría sus propios contadores.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = defaultdict(int)

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)


metrics = Metrics()
