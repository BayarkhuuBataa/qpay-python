import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(
    max_retries: int = 3, backoff_factor: float = 0.5
) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
