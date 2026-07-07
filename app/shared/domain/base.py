from dataclasses import dataclass, field


class ValueObject:
    """Marcador para value objects (frozen dataclasses, iguais por valor)."""


@dataclass(eq=False)
class Entity:
    """Entidade com identidade estável: igualdade e hash por id."""
    id: str

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Entity) and type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id))


@dataclass(eq=False)
class AggregateRoot(Entity):
    """Raiz de agregado — ponto de entrada transacional do contexto."""
