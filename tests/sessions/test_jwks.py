import time
import pytest
import logging

import threading

from typing import List, Any, Callable

from jwt import PyJWK

from supertokens_python import init, SupertokensConfig
from supertokens_python.recipe import session
from supertokens_python.recipe.jwt.interfaces import CreateJwtOkResult
from supertokens_python.recipe.session.asyncio import (
    create_new_session_without_request_response,
    get_session_without_request_response,
)
from supertokens_python.recipe.session.recipe_implementation import (
    get_combined_jwks,
    get_jwks,
)
from supertokens_python.utils import get_timestamp_ms
from tests.utils import (
    get_st_init_args,
    setup_function,
    start_st,
    teardown_function as default_teardown_function,
    set_key_value_in_config,
    st_init_common_args,
)

from supertokens_python.recipe.session.recipe_implementation import (
    reset_jwks_cache,
    JWKSConfig,
    get_jwks_from_cache_if_present,
)

from _pytest.logging import LogCaptureFixture

pytestmark = pytest.mark.asyncio
_ = setup_function  # type:ignore


def teardown_function(_: Any):
    reset_jwks_cache()
    default_teardown_function(_)


def get_log_occurence_count(
    caplog: LogCaptureFixture, msg: str = "Fetching jwk set from the configured uri"
):
    count = 0
    last_processed_index = -1

    while True:
        records = caplog.records[last_processed_index + 1 :]

        for r in records:
            if msg in r.message:
                count += 1

            last_processed_index += 1

        yield count


async def test_that_jwks_is_fetched_as_expected(caplog: LogCaptureFixture):
    """This test verifies that the SDK calls the well known API properly in the normal flow
    - Initialise the SDK and verify that the well known API was not called
    - Create and verify a session
    - Verify that the well known API was called to fetch the keys
    """
    caplog.set_level(logging.DEBUG)
    original_jwks_config = JWKSConfig.copy()
    JWKSConfig.update({"cache_max_age": 2000, "refresh_rate_limit": 100})

    well_known_count = get_log_occurence_count(caplog)
    init(**get_st_init_args(recipe_list=[session.init()]))
    start_st()

    assert next(well_known_count) == 0

    s = await create_new_session_without_request_response("userId", {}, {})
    time.sleep(JWKSConfig["cache_max_age"] / 1000)

    tokens = s.get_all_session_tokens_dangerously()
    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )

    time.sleep(JWKSConfig["cache_max_age"] / 1000)
    assert next(well_known_count) == 1

    JWKSConfig.update(original_jwks_config)


async def test_that_jwks_result_is_refreshed_properly(caplog: LogCaptureFixture):
    """This test verifies that the cache used to store the pointer to the JWKS result is updated properly when the
    cache expired and the keys need to be refetched.

    - Init
    - Call getJWKS to get the keys
    - Wait for access token signing key to change
    - Fetch the keys again
    - Verify that the KIDs inside the pointer have changed
    """
    caplog.set_level(logging.DEBUG)
    jwks_refresh_count = get_log_occurence_count(caplog)

    original_jwks_config = JWKSConfig.copy()
    JWKSConfig.update({"cache_max_age": 2000, "refresh_rate_limit": 100})

    init(**get_st_init_args(recipe_list=[session.init()]))
    set_key_value_in_config(
        "access_token_dynamic_signing_key_update_interval", "0.0004"
    )  # ~1.5 sec
    start_st()

    assert next(jwks_refresh_count) == 0

    jwks_before = get_jwks()
    kids_before: List[str] = [k.key_id for k in jwks_before]  # type: ignore

    assert next(jwks_refresh_count) == 1

    time.sleep(3)

    assert next(jwks_refresh_count) == 1

    jwks_after = get_jwks()
    kids_after: List[str] = [k.key_id for k in jwks_after]  # type: ignore

    assert next(jwks_refresh_count) == 2

    assert jwks_after != jwks_before
    assert kids_after != kids_before

    JWKSConfig.update(original_jwks_config)


async def test_that_jwks_are_refresh_if_kid_is_unknown(caplog: LogCaptureFixture):
    """This test verifies that the SDK tried to re-fetch the keys from the core if the KID for the access token
    does not exist in the cache

    - Init and verify no calls have been made
    - Create and verify a session
    - Verify that a call to the well known API was made
    - Wait for access_token_dynamic_signing_key_update_interval so that the core uses a new key
    - Create and verify another session
    - Verify that the call to the well known API was made
    - Create and verify another session
    - Verify that no call is made
    """
    caplog.set_level(logging.DEBUG)

    init(**get_st_init_args(recipe_list=[session.init()]))
    set_key_value_in_config(
        "access_token_dynamic_signing_key_update_interval", "0.0014"
    )  # ~5sec
    start_st()

    well_known_count = get_log_occurence_count(caplog)

    assert next(well_known_count) == 0

    s = await create_new_session_without_request_response("userId", {}, {})

    assert next(well_known_count) == 0

    tokens = s.get_all_session_tokens_dangerously()
    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )

    assert next(well_known_count) == 1

    time.sleep(10)  # sleep for 10 seconds to make sure that the kid is updated

    assert next(well_known_count) == 1

    s = await create_new_session_without_request_response("userId", {}, {})

    assert next(well_known_count) == 1

    tokens = s.get_all_session_tokens_dangerously()
    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )

    assert next(well_known_count) == 2

    tokens = s.get_all_session_tokens_dangerously()
    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )

    assert next(well_known_count) == 2  # no change


async def test_that_invalid_connection_uri_doesnot_throw_during_init_for_jwks():
    """This test makes sure that initialising SuperTokens and Session with an invalid connection uri does not
    result in an error during startup"""
    init(**{**st_init_common_args, "supertokens_config": SupertokensConfig("https://try.supertokens.io:3567"), "recipe_list": [session.init()]})  # type: ignore
    set_key_value_in_config(
        "access_token_dynamic_signing_key_update_interval", "0.0014"
    )  # ~5sec
    start_st()


async def test_jwks_cache_logic(caplog: LogCaptureFixture):
    """This test verifies the behaviour of the JWKS cache maintained by the SDK
    - Init
    - Make sure the cache is empty
    - Create and verify a session
    - Make sure the cache has one entry now
    - Wait for cache to expire
    - Verify the session again
    - Verify that an entry from the cache was deleted (because the SDK should try to re-fetch)
    - Verify that the cache has an entry
    """
    caplog.set_level(logging.DEBUG)
    original_jwks_config = JWKSConfig.copy()
    JWKSConfig.update({"cache_max_age": 2000, "refresh_rate_limit": 100})

    jwks_refresh_count = get_log_occurence_count(caplog)

    init(**get_st_init_args(recipe_list=[session.init()]))
    start_st()

    assert next(jwks_refresh_count) == 0

    s = await create_new_session_without_request_response("userId", {}, {})

    assert get_jwks_from_cache_if_present() is None
    assert next(jwks_refresh_count) == 0

    tokens = s.get_all_session_tokens_dangerously()
    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )

    assert get_jwks_from_cache_if_present() is not None
    assert next(jwks_refresh_count) == 1

    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )
    assert get_jwks_from_cache_if_present() is not None
    assert next(jwks_refresh_count) == 1  # used cache value

    time.sleep(3)  # Now it should expire and the next call should trigger a refresh
    assert get_jwks_from_cache_if_present() is None
    assert next(jwks_refresh_count) == 1

    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )
    assert get_jwks_from_cache_if_present() is not None
    assert next(jwks_refresh_count) == 2

    JWKSConfig.update(original_jwks_config)


async def test_that_combined_jwks_throws_for_invalid_connection(
    caplog: LogCaptureFixture,
):
    """This test ensures that calling get combines JWKS results in an error if the connection uri is invalid. Note that
    in this test we specifically expect a timeout but that does not mean that this is the only error the function can
    throw
    """
    caplog.set_level(logging.DEBUG)
    jwk_refresh_count = get_log_occurence_count(caplog)

    set_key_value_in_config(
        "access_token_dynamic_signing_key_update_interval", "0.0014"
    )  # ~5sec
    init(**{**st_init_common_args, "supertokens_config": SupertokensConfig("https://try.supertokens.io:3567"), "recipe_list": [session.init()]})  # type: ignore
    start_st()

    combined_jwks_res = get_combined_jwks()

    assert combined_jwks_res is None
    assert next(jwk_refresh_count) == 1


async def test_that_combined_jwks_doesnot_throw_if_atleast_one_core_url_is_valid(
    caplog: LogCaptureFixture,
):
    """
    This test makes sure that when multiple core urls are provided, the get combined JWKS function does not throw an
    error as long as one of the provided urls return a valid response
    - Init with multiple core urls
    - Call get combines jwks
    - verify that there is a response and that there are no errors
    """
    caplog.set_level(logging.DEBUG)
    jwk_refresh_count = get_log_occurence_count(caplog)

    init(**{**st_init_common_args, "supertokens_config": SupertokensConfig("http://localhost:3567;example.com:3567;localhost:90"), "recipe_list": [session.init()]})  # type: ignore
    start_st()

    combined_jwks_res = get_combined_jwks()
    assert combined_jwks_res is not None
    assert next(jwk_refresh_count) == 1


async def test_that_jwks_returns_from_cache_correctly(caplog: LogCaptureFixture):
    """This test ensures that the SDK's caching logic for fetching JWKs works fine
    - Init
    - Create and verify a session
    - Verify that the SDK did not use any cached values
    - Verify the session again
    - Verify that this time the SDK did return a cached value
    - Wait for cache to expire
    - Verify the session again
    - This time the SDK should try to re-fetch and not return a cached value
    """
    caplog.set_level(logging.DEBUG)
    jwk_refresh_count = get_log_occurence_count(caplog)
    returned_from_cache_count = get_log_occurence_count(
        caplog, "Returning JWKS from cache"
    )

    original_jwks_config = JWKSConfig.copy()
    JWKSConfig.update({"cache_max_age": 2000, "refresh_rate_limit": 100})

    init(**get_st_init_args(recipe_list=[session.init()]))
    start_st()

    s = await create_new_session_without_request_response("userId", {}, {})
    assert get_jwks_from_cache_if_present() is None
    assert next(jwk_refresh_count) == 0
    assert next(returned_from_cache_count) == 0

    tokens = s.get_all_session_tokens_dangerously()
    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )

    assert next(jwk_refresh_count) == 1
    assert next(returned_from_cache_count) == 0

    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )

    assert next(jwk_refresh_count) == 1
    assert next(returned_from_cache_count) == 1

    time.sleep(3)  # Now it should expire and the next call should trigger a refresh

    await get_session_without_request_response(
        tokens.get("accessToken"), tokens.get("antiCsrfToken")
    )

    assert next(jwk_refresh_count) == 2
    assert next(returned_from_cache_count) == 1

    JWKSConfig.update(original_jwks_config)


async def test_that_sdk_tries_fetching_jwks_for_all_core_hosts(
    caplog: LogCaptureFixture,
):
    """This test makes sure that the SDK tries to fetch for all core URLS if needed.
    This test uses multiple hosts with only the last one being valid to make sure all URLs are used

    - init with multiple core urls where only the last one is valid
    - Call get combined jwks
    - Make sure that the SDK tried fetching for all URLs (since only the last one would return a valid keyset)
    """
    caplog.set_level(logging.DEBUG)
    urls_attempted_count = get_log_occurence_count(caplog, "Attempting to fetch JWKS")
    get_combined_jwks_count = get_log_occurence_count(
        caplog, "Called get_combined_jwks"
    )

    init(**{**get_st_init_args(recipe_list=[session.init()]), "supertokens_config": SupertokensConfig("example.com;localhost:90;http://localhost:3567")})  # type: ignore
    start_st()

    assert next(urls_attempted_count) == 0
    assert next(get_combined_jwks_count) == 0

    get_combined_jwks()

    assert next(urls_attempted_count) == 3
    assert next(get_combined_jwks_count) == 1


async def test_that_sdk_fetches_jwks_from_core_hosts_until_a_valid_response(
    caplog: LogCaptureFixture,
):
    """This test makes sure that the SDK stop fetching JWKS from multiple cores as soon as it gets a valid response
    - init with multiple cores with the second one being valid (1st and 3rd invalid)
    - call get combines jwks
    - Verify that two urls were used to fetch and that the 3rd one was never used
    """
    caplog.set_level(logging.DEBUG)
    urls_attempted_count = get_log_occurence_count(caplog, "Attempting to fetch JWKS")

    init(
        **{
            **get_st_init_args(recipe_list=[session.init()]),
            "supertokens_config": SupertokensConfig(
                "example.com;http://localhost:3567;localhost:90"
            ),  # Note that the second one is valid
        }
    )
    start_st()

    assert next(urls_attempted_count) == 0

    get_combined_jwks()

    assert next(urls_attempted_count) == 2


from supertokens_python.recipe.session.asyncio import create_jwt


async def test_session_verification_of_jwt_based_on_session_payload(
    # _: LogCaptureFixture,
):
    init(**get_st_init_args(recipe_list=[session.init()]))
    start_st()

    s = await create_new_session_without_request_response("userId", {}, {})

    payload = s.get_access_token_payload()
    del payload["iat"]
    del payload["exp"]

    now = get_timestamp_ms()
    # expiry jwt after 10sec
    jwt_expiry = now + 10 * 1000
    jwt = await create_jwt(payload, jwt_expiry, use_static_signing_key=False)
    assert isinstance(jwt, CreateJwtOkResult)
    s_ = await get_session_without_request_response(jwt.jwt)

    assert s_ is not None
    assert s_.get_user_id() == "userId"


async def test_session_verification_of_jwt_based_on_session_payload_with_check_db():
    init(**get_st_init_args(recipe_list=[session.init()]))
    start_st()

    s = await create_new_session_without_request_response("userId", {}, {})

    payload = s.get_access_token_payload()
    del payload["iat"]
    del payload["exp"]
    payload["tId"] = "public"  # tenant id

    now = get_timestamp_ms()
    jwt_expiry = now + 10 * 1000  # expiry jwt after 10sec
    jwt = await create_jwt(payload, jwt_expiry, use_static_signing_key=False)
    assert isinstance(jwt, CreateJwtOkResult)
    s_ = await get_session_without_request_response(jwt.jwt, check_database=True)

    assert s_ is not None
    assert s_.get_user_id() == "userId"


async def test_that_locking_for_jwks_cache_works(caplog: LogCaptureFixture):
    caplog.set_level(logging.DEBUG)
    not_returned_from_cache_count = get_log_occurence_count(
        caplog, "Returning JWKS from fetch"
    )

    original_jwks_config = JWKSConfig.copy()
    JWKSConfig.update(
        {
            "refresh_rate_limit": 100,
            "cache_max_age": 2000,
        }
    )

    set_key_value_in_config(
        "access_token_dynamic_signing_key_update_interval", "0.0014"
    )  # ~5s
    init(**get_st_init_args(recipe_list=[session.init()]))
    start_st()

    state = {
        "should_stop": False,
        "different_key_found_count": 0,
    }

    jwks = get_combined_jwks() or []
    keys = [k.key_id for k in jwks]

    def stop_after_11s():
        time.sleep(11)
        state["should_stop"] = True

    stop_thread = threading.Thread(target=stop_after_11s)
    stop_thread.start()

    thread_count = 10
    wg = threading.Barrier(thread_count)

    def jwks_lock_test_routine(i: int, callback: Callable[[List[PyJWK]], None]):
        jwks = get_combined_jwks()

        callback(jwks)
        time.sleep(0.1)
        if state["should_stop"]:
            return
        else:
            jwks_lock_test_routine(i, callback)

    def callback(jwks: List[PyJWK]):
        nonlocal keys
        current_keys = [k.key_id for k in jwks]
        new_keys = [k for k in current_keys if k not in keys]
        if len(new_keys) > 0:
            state["different_key_found_count"] += 1
            keys = current_keys

    threads = []
    for i in range(thread_count):
        t = threading.Thread(target=jwks_lock_test_routine, args=(i, callback))
        threads.append(t)
        t.start()

    stop_thread.join()

    for t in threads:
        t.join()

    # We need to test for both:
    # - The keys changing
    # - The number of times the result is not returned from cache

    # Because even if the keys change only twice it could still mean that the SDK's cache locking
    # does not work correctly and that it tried to query the core more times than it should have

    # Checking for both the key change count and the cache miss count verifies the locking behaviour properly

    # With the signing key interval as 5 seconds, and the test making requests for 11 seconds
    # You expect the keys to change twice
    assert state["different_key_found_count"] == 2
    # With cache lifetime being 2s, we expect the cache to be missed 5 times
    assert next(not_returned_from_cache_count) == 1 + 5  # 1 original + 5 misses
    JWKSConfig.update(original_jwks_config)
