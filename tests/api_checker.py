import datetime
import os
from functools import wraps

import pytest
from drf_api_checker.pytest import default_fixture_name
from drf_api_checker.recorder import BASE_DATADIR, Recorder
from rest_framework.response import Response
from rest_framework.test import APIClient

from tests.factories import UserFactory


def frozenfixture(fixture_name=default_fixture_name, is_fixture=True):
    def deco(func):
        from drf_api_checker.fs import mktree
        from drf_api_checker.utils import dump_fixtures, load_fixtures

        @wraps(func)
        def _inner(*args, **kwargs):
            if is_fixture and "request" not in kwargs:
                raise ValueError("frozenfixture must have `request` argument")
            request = kwargs.get("request", None)
            parts = [
                os.path.dirname(func.__code__.co_filename),
                BASE_DATADIR,
                func.__module__,
                func.__name__,
            ]
            seed = os.path.join(*parts)
            destination = fixture_name(seed, request)

            if not os.path.exists(destination) or os.environ.get("API_CHECKER_RESET"):
                mktree(os.path.dirname(destination))
                data = func(*args, **kwargs)
                dump_fixtures({func.__name__: data}, destination)
            return load_fixtures(destination)[func.__name__]

        if is_fixture:
            return pytest.fixture(_inner)
        return _inner

    return deco


@frozenfixture(is_fixture=False)
def get_user():
    return UserFactory(is_superuser=True, username="user999")


class LastModifiedRecorder(Recorder):
    @property
    def client(self):
        user = get_user()
        client = APIClient()
        client.force_authenticate(user)
        return client

    def assert_modified(self, response: Response, stored: Response, path: str):
        value = response["modified"]
        assert datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")

    def assert_created(self, response: Response, stored: Response, path: str):
        value = response["created"]
        assert datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")


class ExpectedErrorRecorder(Recorder):
    expect_errors = True
