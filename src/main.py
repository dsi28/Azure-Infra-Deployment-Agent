"""
Azure Infrastructure Agent - Main Entry Point
"""
import click
from .cli.chat import ChatManager


@click.command()
@click.version_option(version="1.0.0", prog_name="Azure Infrastructure Agent")
def main() -> None:
    """
    Azure Infrastructure Agent - Deploy Azure resources through natural language.

    An intelligent conversational agent that simplifies Azure infrastructure deployment
    through natural language interactions. Start a conversation and describe your
    infrastructure needs in plain English.

    Returns:
        None
    """
    try:
        chat_manager = ChatManager()
        chat_manager.start()
    except Exception as e:
        click.echo(f"Error starting Azure Infrastructure Agent: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()