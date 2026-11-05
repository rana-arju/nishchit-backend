import enum


class AuthProvider(enum.StrEnum):
    LOCAL = "local"
    GOOGLE = "google"
    FACEBOOK = "facebook"
