"""Reconstruct boundary values without trusting unchecked model instances."""

from pydantic import ValidationError

from .models import CodecLimits, IdentityQuery, OptionSelector, OptionStatusQuery, Query


class InvalidBoundary(ValueError):
    """A typed input does not satisfy the closed public contract."""


def checked_query(query: Query) -> Query:
    try:
        if type(query) is IdentityQuery:
            return IdentityQuery(kind=query.kind)
        if type(query) is OptionStatusQuery and type(query.selector) is OptionSelector:
            return OptionStatusQuery(kind=query.kind, selector=query.selector)
    except (AttributeError, ValidationError):
        pass
    raise InvalidBoundary("query does not satisfy the supported read-only alternatives")


def checked_codec_limits(limits: CodecLimits) -> CodecLimits:
    try:
        if type(limits) is CodecLimits:
            return CodecLimits(
                max_line_bytes=limits.max_line_bytes,
                max_queries=limits.max_queries,
                max_exchange_bytes=limits.max_exchange_bytes,
            )
    except (AttributeError, ValidationError):
        pass
    raise InvalidBoundary("codec limits do not satisfy the bounded profile")
