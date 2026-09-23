"""Request-scoped correlation id.

Sættes af request-logging-middlewaren og læses af audit-loggen, så en
audit-række kan kobles til den HTTP-request, der udløste den, uden at
hvert endpoint skal tage et ekstra argument.
"""

from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    return request_id_var.get()
