"""Shared output helpers; no command registration or application operations."""

import click

from mho_scpi import ExchangeAccepted, IdentityObservation


def toml_string(value: str) -> str:
    """Quote an external string without interpreting its contents as TOML."""
    parts: list[str] = []
    escapes = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
    for char in value:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise ValueError("TOML strings require Unicode scalar values")
        if char in escapes:
            parts.append(escapes[char])
        elif code < 32 or code == 127:
            parts.append(f"\\u{code:04x}")
        else:
            parts.append(char)
    return '"' + "".join(parts) + '"'


def render_observations(result: ExchangeAccepted, show_identity: bool) -> None:
    """Render typed observations; identity disclosure remains an explicit choice."""
    for index, pair in enumerate(result.pairs):
        observation = pair.reply.observation
        click.echo("\n[[observations]]")
        click.echo(f"index = {index}")
        click.echo(f'kind = "{observation.kind}"')
        if isinstance(observation, IdentityObservation):
            click.echo(f"identity_redacted = {str(not show_identity).lower()}")
            if show_identity:
                click.echo(f"manufacturer = {toml_string(observation.manufacturer)}")
                click.echo(f"model = {toml_string(observation.model)}")
                click.echo(f"serial_number = {toml_string(observation.serial_number)}")
                click.echo(f"software_revision = {toml_string(observation.software_revision)}")
        else:
            click.echo(f'selector = "{observation.selector.value}"')
            click.echo(f'state = "{observation.state.value}"')
