import threading # Permite sincronizar el acceso concurrente a los contadores.
from collections import defaultdict # Diccionario que crea automáticamente valores por defecto.


class Metrics:
    """
    Contador en memoria, simple e intencionalmente mínimo (sin Prometheus ni
    otras dependencias) para exponer indicadores básicos de negocio y
    operación mientras el proyecto no justifique una solución de métricas
    más completa. Pensado para un solo proceso; en un despliegue con varias
    réplicas cada una tendría sus propios contadores.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock() # Bloqueo para acceso concurrente.
        self._counters: dict[str, int] = defaultdict(int) # Diccionario de contadores.

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock: # Garantiza acceso exclusivo.
            self._counters[name] += amount # Incrementa el contador.

    def snapshot(self) -> dict[str, int]:
        """
        Devuelve una copia del estado actual de todas las
        métricas registradas.

        Retorna:

            Diccionario con los nombres de los contadores y
            sus respectivos valores.

        Ejemplo:

            {
                "mensajes": 120,
                "ventas": 35,
                "errores": 2
            }

        Se devuelve una copia para evitar modificaciones
        externas sobre la estructura interna.
        """
        with self._lock:
            return dict(self._counters)


metrics = Metrics()
