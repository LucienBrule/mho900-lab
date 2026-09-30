"""Canonical identity/status queries only; no arbitrary SCPI command interface.

Encoders emit LF. Decoders accept LF or CRLF, retain original bytes and never
strip whitespace, abbreviate commands or infer a release from identity strings.
"""

from .models import (
    CodecIssue,
    CodecLimits,
    DecodedPair,
    ExchangeAccepted,
    ExchangeRejected,
    IdentityObservation,
    IdentityQuery,
    OptionSelector,
    OptionState,
    OptionStatusObservation,
    OptionStatusQuery,
    Query,
    ReplyAccepted,
    ReplyRejected,
)
from .validation import InvalidBoundary, checked_codec_limits, checked_query

STATUS_PREFIX = b":SYSTem:OPTion:STATus? "
DEFAULT_LIMITS = CodecLimits()


class CodecFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.issue = CodecIssue(code=code, message=message)
        super().__init__(message)


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise CodecFailure(code, message)


def encode_query(query: Query) -> bytes:
    """Encode one typed allowlisted query, always ending in LF."""
    query = checked_query(query)
    if isinstance(query, IdentityQuery):
        return b"*IDN?\n"
    if isinstance(query, OptionStatusQuery):
        return STATUS_PREFIX + query.selector.value.encode("ascii") + b"\n"
    raise TypeError("query is not an allowlisted query alternative")


def body(raw: bytes, limits: CodecLimits) -> bytes:
    require(
        0 < len(raw) <= limits.max_line_bytes, "line-limit", "line size outside configured bound"
    )
    require(
        raw.endswith(b"\n") and raw.count(b"\n") == 1,
        "line-framing",
        "one complete LF or CRLF line required",
    )
    value = raw[:-2] if raw.endswith(b"\r\n") else raw[:-1]
    require(
        all(32 <= byte <= 126 for byte in value),
        "non-printable-ascii",
        "line must contain only printable ASCII before its terminator",
    )
    return value


def decode_reply(
    query: Query, raw: bytes, limits: CodecLimits = DEFAULT_LIMITS
) -> ReplyAccepted | ReplyRejected:
    """Decode a complete bounded reply while retaining its exact terminator and fields."""
    if type(raw) is not bytes:
        raise TypeError("reply must be bytes")
    try:
        query = checked_query(query)
        limits = checked_codec_limits(limits)
    except InvalidBoundary:
        return ReplyRejected(
            CodecIssue("invalid-input", "query or limits violate the codec contract"), query, raw
        )
    try:
        value = body(raw, limits)
        if isinstance(query, IdentityQuery):
            fields = value.decode("ascii").split(",")
            require(
                len(fields) == 4 and all(field and not field.isspace() for field in fields),
                "identity-fields",
                "identity requires exactly four nonempty fields",
            )
            observation = IdentityObservation(
                manufacturer=fields[0],
                model=fields[1],
                serial_number=fields[2],
                software_revision=fields[3],
            )
            return ReplyAccepted(query=query, raw=raw, observation=observation)
        require(value in (b"0", b"1"), "option-state", "option reply must be exactly 0 or 1")
        state = OptionState(value.decode("ascii"))
        return ReplyAccepted(
            query=query,
            raw=raw,
            observation=OptionStatusObservation(selector=query.selector, state=state),
        )
    except CodecFailure as error:
        return ReplyRejected(issue=error.issue, query=query, raw=raw)


def decode_query(raw: bytes, limits: CodecLimits) -> Query:
    value = body(raw, limits)
    if value == b"*IDN?":
        return IdentityQuery()
    require(
        value.startswith(STATUS_PREFIX),
        "unknown-query",
        "request is outside the canonical read-only profile",
    )
    try:
        selector = OptionSelector(value[len(STATUS_PREFIX) :].decode("ascii"))
    except ValueError as error:
        raise CodecFailure("unknown-selector", "option selector is not allowlisted") from error
    return OptionStatusQuery(selector=selector)


def lines(raw: bytes, limits: CodecLimits) -> tuple[bytes, ...]:
    require(raw.endswith(b"\n"), "exchange-framing", "exchange must end with a complete line")
    count = raw.count(b"\n")
    require(count <= limits.max_queries, "query-limit", "query count exceeds configured bound")
    return tuple(part + b"\n" for part in raw.split(b"\n")[:-1])


def decode_exchange(
    request: bytes,
    response: bytes,
    limits: CodecLimits = DEFAULT_LIMITS,
) -> ExchangeAccepted | ExchangeRejected:
    """Pair complete canonical query/reply lines without normalizing either stream."""
    if type(request) is not bytes or type(response) is not bytes:
        raise TypeError("request and response must be bytes")
    try:
        limits = checked_codec_limits(limits)
    except InvalidBoundary:
        return ExchangeRejected(
            CodecIssue("invalid-limits", "limits violate the codec contract"), request, response
        )
    index: int | None = None
    try:
        require(
            len(request) + len(response) <= limits.max_exchange_bytes,
            "exchange-limit",
            "combined request/reply extent exceeds bound",
        )
        request_lines = lines(request, limits)
        response_lines = lines(response, limits)
        require(
            len(request_lines) == len(response_lines),
            "reply-count",
            "query and reply line counts differ",
        )
        pairs: list[DecodedPair] = []
        for index, wire in enumerate(request_lines):
            query = decode_query(wire, limits)
            reply = decode_reply(query, response_lines[index], limits)
            if isinstance(reply, ReplyRejected):
                return ExchangeRejected(
                    request=request,
                    response=response,
                    issue=CodecIssue(
                        code=reply.issue.code, message=reply.issue.message, query_index=index
                    ),
                )
            pairs.append(DecodedPair(query=query, request=wire, reply=reply))
        return ExchangeAccepted(request=request, response=response, pairs=tuple(pairs))
    except CodecFailure as error:
        return ExchangeRejected(
            request=request,
            response=response,
            issue=CodecIssue(code=error.issue.code, message=error.issue.message, query_index=index),
        )
