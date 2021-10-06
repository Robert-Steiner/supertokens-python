"""
Copyright (c) 2020, VRAI Labs and/or its affiliates. All rights reserved.

This software is licensed under the Apache License, Version 2.0 (the
"License") as published by the Apache Software Foundation.

You may not use this file except in compliance with the License. You may
obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""
import json

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.testclient import TestClient
from pytest import fixture
from pytest import mark

from supertokens_python import init
from supertokens_python.recipe import session, emailpassword
from supertokens_python.recipe.emailpassword.interfaces import APIInterface
from supertokens_python.framework.fastapi import Middleware
from supertokens_python.recipe.session import create_new_session, refresh_session, get_session
from tests.utils import (
    reset, setup_st, clean_st, start_st, sign_up_request
)


def setup_function(f):
    reset()
    clean_st()
    setup_st()


def teardown_function(f):
    reset()
    clean_st()


@fixture(scope='function')
async def driver_config_client():
    app = FastAPI()
    app.add_middleware(Middleware)

    @app.get('/login')
    async def login(request: Request):
        user_id = 'userId'
        await create_new_session(request, user_id, {}, {})
        return {'userId': user_id}

    @app.post('/refresh')
    async def custom_refresh(request: Request):
        await refresh_session(request)
        return {}

    @app.get('/info')
    async def info_get(request: Request):
        await get_session(request, True)
        return {}

    @app.get('/custom/info')
    def custom_info(_):
        return {}

    @app.options('/custom/handle')
    def custom_handle_options(_):
        return {'method': 'option'}

    @app.get('/handle')
    async def handle_get(request: Request):
        session = await get_session(request, True)
        return {'s': session.get_handle()}

    @app.post('/logout')
    async def custom_logout(request: Request):
        session = await get_session(request, True)
        await session.revoke_session()
        return {}

    return TestClient(app)


def apis_override_email_password(param: APIInterface):
    param.disable_email_exists_get = True
    return param


@mark.asyncio
async def test_good_input_email_exists(driver_config_client: TestClient):
    init({
        'supertokens': {
            'connection_uri': "http://localhost:3567",
        },
        'framework': 'fastapi',
        'app_info': {
            'app_name': "SuperTokens Demo",
            'api_domain': "api.supertokens.io",
            'website_domain': "supertokens.io",
            'api_base_path': "/auth"
        },
        'recipe_list': [session.init(
            {
                'anti_csrf': 'VIA_TOKEN',
                'cookie_domain': 'supertokens.io'
            }
        ),

            emailpassword.init({})
        ],
    })
    start_st()

    response_1 = sign_up_request(
        driver_config_client,
        "random@gmail.com",
        "validPass123")

    assert response_1.status_code == 200
    dict_response = json.loads(response_1.text)
    assert dict_response["status"] == "OK"

    response_2 = driver_config_client.get(
        url='/auth/signup/email/exists',
        params={
            'email': 'random@gmail.com'})
    assert response_2.status_code == 200


@mark.asyncio
async def test_good_input_email_does_not_exists(driver_config_client: TestClient):
    init({
        'supertokens': {
            'connection_uri': "http://localhost:3567",
        },
        'framework': 'fastapi',
        'app_info': {
            'app_name': "SuperTokens Demo",
            'api_domain': "api.supertokens.io",
            'website_domain': "supertokens.io",
            'api_base_path': "/auth"
        },
        'recipe_list': [session.init(
            {
                'anti_csrf': 'VIA_TOKEN',
                'cookie_domain': 'supertokens.io'
            }
        ),
            emailpassword.init({})
        ],
    })
    start_st()

    response_1 = driver_config_client.get(
        url='/auth/signup/email/exists',
        params={
            'email': 'random@gmail.com'})

    assert response_1.status_code == 200
    dict_response = json.loads(response_1.text)
    assert dict_response["status"] == "OK"
    assert dict_response["exists"] is False


@mark.asyncio
async def test_that_if_disabling_api_the_default_email_exists_api_does_not_work(driver_config_client: TestClient):
    init({
        'supertokens': {
            'connection_uri': "http://localhost:3567",
        },
        'framework': 'fastapi',
        'app_info': {
            'app_name': "SuperTokens Demo",
            'api_domain': "api.supertokens.io",
            'website_domain': "supertokens.io",
            'api_base_path': "/auth"
        },
        'recipe_list': [session.init(
            {
                'anti_csrf': 'VIA_TOKEN',
                'cookie_domain': 'supertokens.io'
            }
        ),
            emailpassword.init({
                'override': {
                    'apis': apis_override_email_password
                },

            })
        ],
    })
    start_st()

    response_1 = driver_config_client.get(
        url='/auth/signup/email/exists',
        params={
            'email': 'random@gmail.com'})

    assert response_1.status_code == 404


@mark.asyncio
async def test_email_exists_a_syntactically_invalid_email(driver_config_client: TestClient):
    init({
        'supertokens': {
            'connection_uri': "http://localhost:3567",
        },
        'framework': 'fastapi',
        'app_info': {
            'app_name': "SuperTokens Demo",
            'api_domain': "api.supertokens.io",
            'website_domain': "supertokens.io",
            'api_base_path': "/auth"
        },
        'recipe_list': [session.init(
            {
                'anti_csrf': 'VIA_TOKEN',
                'cookie_domain': 'supertokens.io'
            }
        ),

            emailpassword.init({})
        ],
    })
    start_st()

    response_1 = sign_up_request(
        driver_config_client,
        "random@gmail.com",
        "validPass123")

    assert response_1.status_code == 200
    dict_response = json.loads(response_1.text)
    assert dict_response["status"] == "OK"

    response_2 = driver_config_client.get(
        url='/auth/signup/email/exists',
        params={
            'email': 'randomgmail.com'})
    assert response_2.status_code == 200
    dict_response = json.loads(response_2.text)
    assert dict_response["status"] == "OK"
    assert dict_response["exists"] is False


@mark.asyncio
async def test_sending_an_unnormalised_email_and_you_get_exists_is_true(driver_config_client: TestClient):
    init({
        'supertokens': {
            'connection_uri': "http://localhost:3567",
        },
        'framework': 'fastapi',
        'app_info': {
            'app_name': "SuperTokens Demo",
            'api_domain': "api.supertokens.io",
            'website_domain': "supertokens.io",
            'api_base_path': "/auth"
        },
        'recipe_list': [session.init(
            {
                'anti_csrf': 'VIA_TOKEN',
                'cookie_domain': 'supertokens.io'
            }
        ),

            emailpassword.init({})
        ],
    })
    start_st()

    response_1 = sign_up_request(
        driver_config_client,
        "random@gmail.com",
        "validPass123")

    assert response_1.status_code == 200
    dict_response = json.loads(response_1.text)
    assert dict_response["status"] == "OK"

    response_2 = driver_config_client.get(
        url='/auth/signup/email/exists',
        params={
            'email': 'rAndOM@gmAiL.COm'})
    assert response_2.status_code == 200
    dict_response = json.loads(response_2.text)
    assert dict_response["status"] == "OK"
    assert dict_response["exists"] is True


@mark.asyncio
async def test_bad_input_do_not_pass_email(driver_config_client: TestClient):
    init({
        'supertokens': {
            'connection_uri': "http://localhost:3567",
        },
        'framework': 'fastapi',
        'app_info': {
            'app_name': "SuperTokens Demo",
            'api_domain': "api.supertokens.io",
            'website_domain': "supertokens.io",
            'api_base_path': "/auth"
        },
        'recipe_list': [session.init(
            {
                'anti_csrf': 'VIA_TOKEN',
                'cookie_domain': 'supertokens.io'
            }
        ),

            emailpassword.init({})
        ],
    })
    start_st()

    response_1 = sign_up_request(
        driver_config_client,
        "random@gmail.com",
        "validPass123")

    assert response_1.status_code == 200
    dict_response = json.loads(response_1.text)
    assert dict_response["status"] == "OK"

    response_2 = driver_config_client.get(
        url='/auth/signup/email/exists', params={})
    assert response_2.status_code == 400
    assert "Please provide the email as a GET param" in response_2.text


@mark.asyncio
async def test_passing_an_array_instead_of_a_string_in_the_email(driver_config_client: TestClient):
    init({
        'supertokens': {
            'connection_uri': "http://localhost:3567",
        },
        'framework': 'fastapi',
        'app_info': {
            'app_name': "SuperTokens Demo",
            'api_domain': "api.supertokens.io",
            'website_domain': "supertokens.io",
            'api_base_path': "/auth"
        },
        'recipe_list': [session.init(
            {
                'anti_csrf': 'VIA_TOKEN',
                'cookie_domain': 'supertokens.io'
            }
        ),

            emailpassword.init({})
        ],
    })
    start_st()

    response_1 = sign_up_request(
        driver_config_client,
        "random@gmail.com",
        "validPass123")

    assert response_1.status_code == 200
    dict_response = json.loads(response_1.text)
    assert dict_response["status"] == "OK"

    response_2 = driver_config_client.get(
        url='/auth/signup/email/exists',
        params={
            'email': [
                'rAndOM@gmAiL.COm',
                'x@g.com']})
    assert response_2.status_code == 200
