"""
Account Manager untuk Twitter Scraper
Kelola akun Twitter untuk scraping
"""

import asyncio
import sys
from pathlib import Path
from twscrape import API
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm


console = Console()


async def add_account(api: API, username: str, password: str, email: str, email_password: str):
    """Add a Twitter account to the pool"""
    try:
        await api.pool.add_account(username, password, email, email_password)
        await api.pool.login_all()
        console.print(f"[green]✓[/green] Account @{username} added successfully!")
        return True
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to add account: {e}")
        return False


async def list_accounts(api: API):
    """List all accounts in the pool"""
    accounts = await api.pool.accounts_info()
    
    if not accounts:
        console.print("[yellow]No accounts found. Please add an account first.[/yellow]")
        return
    
    table = Table(title="Twitter Accounts")
    table.add_column("Username", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Total Requests", style="magenta")
    
    for acc in accounts:
        status = "✓ Active" if acc.active else "✗ Inactive"
        table.add_row(acc.username, status, str(acc.total_req or 0))
    
    console.print(table)


async def remove_account(api: API, username: str):
    """Remove an account from the pool"""
    try:
        await api.pool.delete_accounts([username])
        console.print(f"[green]✓[/green] Account @{username} removed!")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to remove account: {e}")


async def login_all(api: API):
    """Login all accounts"""
    try:
        await api.pool.login_all()
        console.print("[green]✓[/green] All accounts logged in!")
    except Exception as e:
        console.print(f"[red]✗[/red] Login failed: {e}")


async def interactive_add():
    """Interactive account addition"""
    console.print("\n[bold]Add Twitter Account[/bold]")
    console.print("Note: Use a secondary account for scraping, not your main account.\n")
    
    username = Prompt.ask("Twitter username (without @)")
    password = Prompt.ask("Twitter password", password=True)
    email = Prompt.ask("Email address for the account")
    email_password = Prompt.ask("Email password (for verification)", password=True)
    
    api = API()
    await add_account(api, username, password, email, email_password)


async def main():
    """Main menu"""
    api = API()
    
    while True:
        console.print("\n[bold]🐦 Twitter Account Manager[/bold]")
        console.print("1. Add account")
        console.print("2. List accounts")
        console.print("3. Login all accounts")
        console.print("4. Remove account")
        console.print("5. Exit")
        
        choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5"])
        
        if choice == "1":
            await interactive_add()
        elif choice == "2":
            await list_accounts(api)
        elif choice == "3":
            await login_all(api)
        elif choice == "4":
            username = Prompt.ask("Username to remove")
            if Confirm.ask(f"Remove @{username}?"):
                await remove_account(api, username)
        elif choice == "5":
            console.print("Bye! 👋")
            break


if __name__ == "__main__":
    # Handle Windows event loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
