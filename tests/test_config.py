from katana import config


def test_env_loaded():
    assert config.SECRET_KEY is not None
