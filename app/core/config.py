import os

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-pixel-crypt-secret-change-me-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
