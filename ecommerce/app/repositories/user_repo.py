from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.utils.auth import hash_password, verify_password

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, username: str, email: str, password: str,
                full_name: str = "", role: UserRole = UserRole.customer) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_by_username(username)
        if user and verify_password(password, user.hashed_password):
            return user
        return None

    def list_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def update_spent(self, user: User, amount: float) -> User:
        user.total_spent += amount
        user.upgrade_tier()
        self.db.flush()
        return user
