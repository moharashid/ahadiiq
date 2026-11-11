from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    POSTGRES_DB: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER:str
    S3_BUCKET_NAME: str 
    ANTHROPIC_API_KEY: str | None = None
    COGNITO_CLIENT_ID: str | None = None
    COGNITO_REDIRECT_URI: str | None = None
    COGNITO_DOMAIN: str | None = None
    COGNITO_REGION: str | None = None
    COGNITO_CLIENT_SECRET: str | None = None
    COGNITO_USER_POOL_ID: str | None = None
    @property
    def db_url(self):
       return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}" 
    @property
    def s3_bucket_name(self):
        return self.S3_BUCKET_NAME
  
    @property
    def anthropic_api_key(self):
        return self.ANTHROPIC_API_KEY
    @property
    def cognito_client_id(self):
        return self.COGNITO_CLIENT_ID
    @property
    def cognito_redirect_uri(self):
        return self.COGNITO_REDIRECT_URI
    @property
    def cognito_domain(self):
        return self.COGNITO_DOMAIN
    @property
    def cognito_region(self):
        return self.COGNITO_REGION
    @property
    def cognito_client_secret(self):
        return self.COGNITO_CLIENT_SECRET
    @property
    def cognito_user_pool_id(self):
        return self.COGNITO_USER_POOL_ID
settings = Settings()

