"""FastAPI dependency functions."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from ayeneh.container import Container

_container: Container | None = None


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    assert _container is not None, "Container not initialized"
    return _container


async def get_db() -> None:
    """Placeholder — returns database session when wired."""
    return None


ContainerDep = Annotated[Container, Depends(get_container)]
