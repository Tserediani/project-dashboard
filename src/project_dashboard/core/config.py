from pydantic import BaseModel, Secret
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresConfig(BaseModel):
    protocol: str
    host: str
    port: str
    user: Secret[str]
    password: Secret[str]
    db: Secret[str]

    def dsn_for(self, db_name: str) -> str:
        return (
            f"{self.protocol}://{self.user.get_secret_value()}:"
            f"{self.password.get_secret_value()}@{self.host}:"
            f"{self.port}/{db_name}"
        )

    @property
    def dsn(self) -> str:
        return self.dsn_for(self.db.get_secret_value())


class JWTConfig(BaseModel):
    secret_key: Secret[str]
    algorithm: str


class DocumentConfig(BaseModel):
    max_project_storage_bytes: int


class AWSConfig(BaseModel):
    access_key_id: str
    secret_access_key: str
    region: str
    s3_bucket: str


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    postgres: PostgresConfig
    jwt: JWTConfig
    document: DocumentConfig
    aws: AWSConfig


CONFIG = AppConfig()
