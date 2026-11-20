"""Схемы запросов/ответов локального API: dataclass-ы с валидацией входов.

Приведение типов использует те же встроенные функции (str/int/float/bool), что и прежние ручные
ветки, поэтому неверные входы падают теми же исключениями и оборачиваются в те же коды ответов.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MISSING = object()

_COERCE = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "any": lambda v: v,
}


class SchemaError(ValueError):
    """Неверные входные данные: единая ошибка валидации схемы."""


@dataclass(frozen=True)
class Field:
    """Одно поле запроса: имя, приведение типа, значение при отсутствии ключа."""

    name: str
    kind: str = "any"
    default: Any = _MISSING


def fields(**kw: Any) -> tuple[Field, ...]:
    """fields(text="str", limit=("int", 100)) → (Field("text", "str"), Field("limit", "int", 100))."""
    out: list[Field] = []
    for name, spec in kw.items():
        kind, default = spec if isinstance(spec, tuple) else (spec, _MISSING)
        out.append(Field(name, kind, default))
    return tuple(out)


@dataclass(frozen=True)
class RequestSchema:
    """Декларация входов маршрута: query-поля и body-поля."""

    query: tuple[Field, ...] = ()
    body: tuple[Field, ...] = ()

    def validate(self, query: dict | None = None, body: Any = None) -> dict:
        """Валидирует и приводит входы. Отсутствующие поля получают default.

        Исключения не перехватываются: ValueError/TypeError от приведения уходят выше и
        превращаются в те же коды ответов, что и при прежних ручных приведениях.
        """
        out: dict[str, Any] = {}
        query = query if isinstance(query, dict) else {}
        body = body if isinstance(body, dict) else {}
        for fld in self.query:
            out[fld.name] = _coerce_field(fld, query)
        for fld in self.body:
            out[fld.name] = _coerce_field(fld, body)
        return out


def _coerce_field(fld: Field, source: dict) -> Any:
    if fld.name in source:
        return _COERCE[fld.kind](source[fld.name])
    if fld.default is not _MISSING:
        return fld.default
    return None


@dataclass(frozen=True)
class ResponseSchema:
    """Декларация контракта ответа. В рантайме ответы не перепроверяются (поведение 1:1);

    контракт проверяется в тестах через check().
    """

    kind: str = "object"  # object | array | any
    fields: tuple[str, ...] = ()

    def check(self, payload: Any) -> None:
        """Поднимает SchemaError, если ответ не соответствует объявленной форме."""
        if self.kind == "any":
            return
        if self.kind == "array" and not isinstance(payload, list):
            raise SchemaError("ответ должен быть списком")
        if self.kind == "object" and not isinstance(payload, dict):
            raise SchemaError("ответ должен быть объектом")
        if self.kind == "object":
            missing = [name for name in self.fields if name not in payload]
            if missing:
                raise SchemaError(f"в ответе нет полей: {', '.join(missing)}")
