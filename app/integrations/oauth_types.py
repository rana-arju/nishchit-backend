from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OAuthUserInfo:
    email: str
    name: str
    provider_user_id: str
