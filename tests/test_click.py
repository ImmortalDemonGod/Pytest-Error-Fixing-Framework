import click

@click.command()
def main():
    choice = click.prompt(
        "Your choice",
        type=click.Choice(["y", "n", "q"], case_sensitive=False),
        default="y",
        show_default=True
    )
    click.echo(f"You typed: {choice}")

if __name__ == "__main__":
    main()