from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import auth
from app.auth import verify_access_token
from app.config import Settings
from app.models import Base
from app.repositories import ProjectRepository
from app.schemas import Platform, ProjectCreate


class SigningKey:
    def __init__(self, key: object) -> None:
        self.key = key


class FakeJwksClient:
    def __init__(self, key: object) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, _token: str) -> SigningKey:
        return SigningKey(self.key)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    Base.metadata.drop_all(engine)


def project_payload(name: str) -> ProjectCreate:
    return ProjectCreate(
        name=name,
        brief="Turn this idea into a clear creator script.",
        target_platforms=[Platform.INSTAGRAM],
    )


def test_project_repository_keeps_projects_owner_scoped(session: Session) -> None:
    repository = ProjectRepository(session)
    created = repository.create("creator-a", project_payload("Creator A project"))
    repository.create("creator-b", project_payload("Creator B project"))

    owned = repository.list_owned("creator-a")

    assert [project.id for project in owned] == [created.id]
    assert repository.get_owned("creator-b", created.id) is None


def test_jwt_verifier_requires_complete_configuration() -> None:
    with pytest.raises(HTTPException) as error:
        verify_access_token("not-a-token", Settings())

    assert error.value.status_code == 503


def test_jwt_verifier_accepts_valid_owner_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65_537, key_size=2_048)
    public_key = private_key.public_key()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "creator-a",
            "aud": "creatorai-api",
            "iss": "https://issuer.example",
            "exp": now + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
    )
    monkeypatch.setattr(auth, "get_jwks_client", lambda _url: FakeJwksClient(public_key))

    creator = verify_access_token(
        token,
        Settings(
            auth_jwks_url="https://issuer.example/.well-known/jwks.json",
            auth_audience="creatorai-api",
            auth_issuer="https://issuer.example",
        ),
    )

    assert creator.id == "creator-a"


def test_jwt_verifier_rejects_unapproved_algorithm() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "creator-a",
            "aud": "creatorai-api",
            "iss": "https://issuer.example",
            "exp": now + timedelta(minutes=5),
        },
        "not-a-production-key",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        verify_access_token(
            token,
            Settings(
                auth_jwks_url="https://issuer.example/.well-known/jwks.json",
                auth_audience="creatorai-api",
                auth_issuer="https://issuer.example",
            ),
        )

    assert error.value.status_code == 401
