"""認証API"""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings

router = APIRouter()

# 暗号化コンテキスト（bcrypt互換性問題回避のためpbkdf2_sha256を使用）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# OAuth2スキーム
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


# Pydanticモデル
class UserCreate(BaseModel):
    """ユーザー作成リクエスト"""

    email: str
    password: str
    name: str = ""


class UserResponse(BaseModel):
    """ユーザーレスポンス"""

    email: str
    name: str


class TokenResponse(BaseModel):
    """トークンレスポンス"""

    access_token: str
    token_type: str = "bearer"


class UserInDB(UserResponse):
    """データベース内のユーザー（ハッシュ済みパスワード）"""

    hashed_password: str


# 擬似ユーザーデータベース（本番環境ではPostgreSQLを使用）
# 遅延初期化（bcrypt互換性問題対策）
def _create_fake_users_db():
    """擬似ユーザーデータベースの作成（遅延初期化）"""
    return {
        "admin@example.com": UserInDB(
            email="admin@example.com",
            name="管理者",
            hashed_password=pwd_context.hash("admin123"[:72]),
        )
    }

fake_users_db = _create_fake_users_db()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワードの確認"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """パスワードのハッシュ生成"""
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    """アクセストークンの生成"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    """アクセストークンのデコード"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserResponse:
    """現在のユーザーを取得"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証できませんでした",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    email: str | None = payload.get("sub")
    if email is None:
        raise credentials_exception
    user = fake_users_db.get(email)
    if user is None:
        raise credentials_exception
    return UserResponse(email=user.email, name=user.name)


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    """ユーザー登録"""
    if user.email in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています",
        )
    fake_users_db[user.email] = UserInDB(
        email=user.email,
        name=user.name,
        hashed_password=get_password_hash(user.password),
    )
    return UserResponse(email=user.email, name=user.name)


@router.post("/login", response_model=TokenResponse)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """ログイン"""
    user = fake_users_db.get(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )
    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: Annotated[UserResponse, Depends(get_current_user)]):
    """現在のユーザー情報を取得"""
    return user
