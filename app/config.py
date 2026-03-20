from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Clinova"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # MongoDB Config
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "clinic_saas_db"
    
    # Auth Config
    SECRET_KEY: str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" # Replace in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Cloudinary Config
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    # Email Config
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

settings = Settings()
