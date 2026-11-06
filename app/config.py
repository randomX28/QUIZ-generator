"""Central configuration for IIT (ISM) Dhanbad Exam Management System."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "IIT (ISM) Dhanbad - Exam Paper Generator")
    BASE_DIR: Path = BASE_DIR
    DB_PATH: Path = Path(os.getenv("DB_PATH", str(BASE_DIR / "quiz.db")))
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "generated_papers")))
    TEMPLATES_DIR: Path = BASE_DIR / "app" / "templates"
    STATIC_DIR: Path = BASE_DIR / "static"
    LOGO_FILENAME: str = "iit_logo.png"

    # Default Exam Metadata
    DEFAULT_SUBJECT_NAME: str = os.getenv("DEFAULT_SUBJECT_NAME", "Compiler Design")
    DEFAULT_COURSE_CODE: str = os.getenv("DEFAULT_COURSE_CODE", "NCSC302-CSC302")
    DEFAULT_DURATION: str = os.getenv("DEFAULT_DURATION", "30 Minutes")
    DEFAULT_MAX_MARKS: str = os.getenv("DEFAULT_MAX_MARKS", "10 (2 marks per question)")
    DEFAULT_BANK_NAME: str = "Compiler Design"
    DEFAULT_BANK_CODE: str = "CD"
    DEFAULT_BANK_COURSE: str = "NCSC302"
    DEFAULT_POOL_COUNT: int = 5

    # Server configuration (0.0.0.0 enables local Wi-Fi / mobile access)
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))

    def get_bank_output_dir(self, bank_id: int | None = None) -> Path:
        """Return partitioned directory for a bank, or base output directory."""
        if bank_id is not None:
            p = self.OUTPUT_DIR / f"bank_{bank_id}"
        else:
            p = self.OUTPUT_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

settings = Settings()

