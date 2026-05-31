"""Registry mapping framework identifiers to scorer instances."""

from __future__ import annotations

from lexara.models.scoring import FRAMEWORK_ALIASES
from lexara.scoring.base import ReadabilityFramework
from lexara.scoring.frameworks import BUILTIN_FRAMEWORKS


class FrameworkRegistry:
    def __init__(self, frameworks: list[ReadabilityFramework] | None = None) -> None:
        self._frameworks: dict[str, ReadabilityFramework] = {}
        for fw in frameworks if frameworks is not None else BUILTIN_FRAMEWORKS:
            self.register(fw)

    def register(self, framework: ReadabilityFramework) -> None:
        self._frameworks[framework.name] = framework

    def get(self, name: str) -> ReadabilityFramework:
        canonical = FRAMEWORK_ALIASES.get(name, name)
        try:
            return self._frameworks[canonical]
        except KeyError as exc:
            raise KeyError(name) from exc

    def names(self) -> list[str]:
        return list(self._frameworks)

    def resolve(self, names: list[str] | None) -> list[ReadabilityFramework]:
        if not names:
            return list(self._frameworks.values())

        resolved: list[ReadabilityFramework] = []
        unknown: list[str] = []
        seen: set[str] = set()

        for name in names:
            canonical = FRAMEWORK_ALIASES.get(name, name)
            if canonical not in self._frameworks:
                unknown.append(name)
                continue
            if canonical in seen:
                continue
            seen.add(canonical)
            resolved.append(self._frameworks[canonical])

        if unknown:
            raise KeyError(unknown)
        return resolved


_default_registry: FrameworkRegistry | None = None


def get_registry() -> FrameworkRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = FrameworkRegistry()
    return _default_registry
