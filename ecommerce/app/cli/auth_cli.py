from rich.panel import Panel
from sqlalchemy.orm import Session
from app.repositories import UserRepository
from app.models.user import User, UserRole
from app.cli.ui import (console, print_success, print_error, print_info,
                         prompt_input, section_header, tier_badge)

class AuthCLI:
    def __init__(self, db: Session):
        self.db        = db
        self.user_repo = UserRepository(db)

    def login(self) -> User | None:
        section_header("Login")
        username = prompt_input("Username")
        password = prompt_input("Password", password=True)
        user = self.user_repo.authenticate(username, password)
        if not user:
            print_error("Invalid credentials.")
            return None
        print_success(f"Welcome back, [bold]{user.full_name or user.username}[/bold]! "
                      f"Tier: {tier_badge(user.tier.value)}")
        return user

    def register(self) -> User | None:
        section_header("Create Account")
        username  = prompt_input("Choose a username")
        if self.user_repo.get_by_username(username):
            print_error("Username already taken.")
            return None
        email     = prompt_input("Email address")
        if self.user_repo.get_by_email(email):
            print_error("Email already registered.")
            return None
        full_name = prompt_input("Full name")
        password  = prompt_input("Password", password=True)
        confirm   = prompt_input("Confirm password", password=True)
        if password != confirm:
            print_error("Passwords do not match.")
            return None

        user = self.user_repo.create(
            username=username, email=email,
            password=password, full_name=full_name,
        )
        self.db.commit()
        print_success(f"Account created! Welcome, [bold]{full_name}[/bold].")
        return user

    def show_profile(self, user: User):
        section_header("My Profile")
        console.print(Panel(
            f"[bold white]{user.full_name or user.username}[/bold white]\n"
            f"[dim]@{user.username}  ·  {user.email}[/dim]\n\n"
            f"  Tier     : {tier_badge(user.tier.value)}\n"
            f"  Role     : [accent]{user.role.value}[/accent]\n"
            f"  Spent    : [price]₹{user.total_spent:,.2f}[/price]\n"
            f"  Discount : [success]{int(user.discount_rate*100)}% off[/success]",
            border_style="cyan", title="[cyan]Account[/cyan]"
        ))

    def auth_menu(self) -> User | None:
        while True:
            console.print("\n  [bold cyan]1.[/bold cyan] Login")
            console.print("  [bold cyan]2.[/bold cyan] Register")
            console.print("  [bold cyan]0.[/bold cyan] Exit")
            choice = prompt_input("Choice")
            if choice == "1":
                user = self.login()
                if user:
                    return user
            elif choice == "2":
                user = self.register()
                if user:
                    return user
            elif choice == "0":
                return None
            else:
                print_error("Invalid choice.")
