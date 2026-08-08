from pydantic import BaseModel, Secret
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresConfig(BaseModel):
    protocol: str
    host: str
    port: str
    user: Secret[str]
    password: Secret[str]
    db: Secret[str]

    @property
    def dsn(self) -> str:
        return (
            f"{self.protocol}://{self.user.get_secret_value()}:"
            f"{self.password.get_secret_value()}@{self.host}:"
            f"{self.port}/{self.db.get_secret_value()}"
        )


class JWTConfig(BaseModel):
    secret_key: Secret[str]
    algorithm: str


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    postgres: PostgresConfig
    jwt: JWTConfig


CONFIG = AppConfig()
