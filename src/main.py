"""
Azure Infrastructure Agent - Main Entry Point
"""
import click
from .cli.chat import ChatManager
from .cli.agent_chat import create_agent_chat


@click.command()
@click.option(
    "--agent", 
    is_flag=True, 
    help="Enable agent mode with local LLM (requires Ollama)"
)
@click.version_option(version="1.0.0", prog_name="Azure Infrastructure Agent")
def main(agent: bool) -> None:
    """
    Azure Infrastructure Agent - Deploy Azure resources through natural language.

    An intelligent conversational agent that simplifies Azure infrastructure deployment
    through natural language interactions. Start a conversation and describe your
    infrastructure needs in plain English.

    Args:
        agent (bool): Enable agent mode with local LLM capabilities.

    Returns:
        None
    """
    try:
        if agent:
            # Use new agent mode with local LLM
            click.echo("🤖 Starting Azure Storage Agent (Agent Mode)")
            click.echo("💡 Requires Ollama with llama3.2:3b model installed")
            click.echo("🔄 Fallback to workflow mode available if needed")
            click.echo("-" * 60)
            
            agent_chat = create_agent_chat()
            agent_chat.start()
        else:
            # Use existing workflow mode
            click.echo("📋 Starting Azure Infrastructure Agent (Workflow Mode)")
            click.echo("💡 Use --agent flag to try the new agent mode")
            click.echo("-" * 60)
            
            chat_manager = ChatManager()
            chat_manager.start()
            
    except Exception as e:
        click.echo(f"Error starting Azure Infrastructure Agent: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()