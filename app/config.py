from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'AdIntel x402 API'
    app_version: str = '0.5.0'
    public_base_url: str = 'http://127.0.0.1:8080'

    x402_enabled: bool = False
    x402_network: str = 'eip155:84532'
    x402_price_hooks: str = '$0.01'
    x402_price_angles: str = '$0.02'
    x402_price_storyboard: str = '$0.03'
    x402_price: str = '$0.05'
    x402_price_full_campaign: str = '$0.10'
    pay_to_address: str = ''
    facilitator_url: str = 'https://x402.org/facilitator'

    ai_provider: str = 'local'
    openrouter_api_key: str = ''
    openrouter_model: str = ''
    openrouter_base_url: str = 'https://openrouter.ai/api/v1'
    openrouter_timeout_seconds: float = 60.0
    app_url: str = ''
    app_title: str = 'AdIntel x402 API'

    admin_token: str = 'change-me-before-production'
    database_path: str = 'data/adintel.sqlite3'

    @field_validator('x402_network')
    @classmethod
    def validate_network(cls, value: str) -> str:
        allowed = {'eip155:84532', 'eip155:8453'}
        if value not in allowed:
            raise ValueError(f'x402_network must be one of {sorted(allowed)}')
        return value

    @field_validator('ai_provider')
    @classmethod
    def validate_provider(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in {'local', 'openrouter'}:
            raise ValueError('ai_provider must be local or openrouter')
        return value

    @property
    def endpoint_prices(self) -> dict[str, str]:
        return {
            '/v1/hooks': self.x402_price_hooks,
            '/v1/angles': self.x402_price_angles,
            '/v1/video-storyboard': self.x402_price_storyboard,
            '/v1/ad-intel': self.x402_price,
            '/v1/full-campaign': self.x402_price_full_campaign,
        }

    def validate_runtime(self) -> list[str]:
        warnings: list[str] = []
        if self.x402_enabled:
            if not self.pay_to_address.startswith('0x') or len(self.pay_to_address) != 42:
                warnings.append('PAY_TO_ADDRESS is missing or not a 42-character EVM address.')
            if self.public_base_url.startswith('http://127.') or 'localhost' in self.public_base_url:
                warnings.append('PUBLIC_BASE_URL is local; Bazaar discovery needs a public HTTPS URL.')
            elif not self.public_base_url.startswith('https://'):
                warnings.append('PUBLIC_BASE_URL should use HTTPS before public launch.')
        if self.ai_provider == 'openrouter':
            if not self.openrouter_api_key:
                warnings.append('OPENROUTER_API_KEY is empty; local fallback will be used.')
            if not self.openrouter_model:
                warnings.append('OPENROUTER_MODEL is empty; local fallback will be used.')
        insecure = {'change-me-before-production','change-this-to-a-long-random-string','replace-with-long-random-string'}
        if self.admin_token in insecure or len(self.admin_token) < 32:
            warnings.append('ADMIN_TOKEN should be a unique random secret of at least 32 characters.')
        return warnings

    @property
    def db_path(self) -> Path:
        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
