from dotenv import load_dotenv
import os
from typing import Any, Dict, List, Union

from supertokens_python import (InputAppInfo, Supertokens, SupertokensConfig,
                                init)
from supertokens_python.recipe import (emailpassword, passwordless, session,
                                       thirdparty, thirdpartyemailpassword,
                                       thirdpartypasswordless)
from supertokens_python.recipe.emailpassword import EmailPasswordRecipe
from supertokens_python.recipe.emailpassword.types import InputFormField, User
from supertokens_python.recipe.emailverification import EmailVerificationRecipe
from supertokens_python.recipe.jwt import JWTRecipe
from supertokens_python.recipe.passwordless import (
    ContactEmailOnlyConfig, ContactEmailOrPhoneConfig, ContactPhoneOnlyConfig,
    CreateAndSendCustomEmailParameters,
    CreateAndSendCustomTextMessageParameters, PasswordlessRecipe)
from supertokens_python.recipe.session import SessionRecipe
from supertokens_python.recipe.thirdparty import ThirdPartyRecipe
from supertokens_python.recipe.thirdparty.provider import Provider
from supertokens_python.recipe.thirdparty.types import (
    AccessTokenAPI, AuthorisationRedirectAPI, UserInfo, UserInfoEmail)
from supertokens_python.recipe.thirdpartyemailpassword import (
    Facebook, Github, Google, ThirdPartyEmailPasswordRecipe)
from supertokens_python.recipe.thirdpartypasswordless import \
    ThirdPartyPasswordlessRecipe
from typing_extensions import Literal

from.store import save_url_with_token, save_code

load_dotenv()


def get_api_port():
    return '8083'


def get_website_port():
    return '3031'


def get_website_domain():
    return 'http://localhost:' + get_website_port()


async def save_code_email(param: CreateAndSendCustomEmailParameters, _: Dict[str, Any]):
    save_code(param.pre_auth_session_id, param.url_with_link_code, param.user_input_code)


async def save_code_text(param: CreateAndSendCustomTextMessageParameters, _: Dict[str, Any]):
    save_code(param.pre_auth_session_id, param.url_with_link_code, param.user_input_code)


async def create_and_send_custom_email(_: User, url_with_token: str, __: Dict[str, Any]):
    save_url_with_token(url_with_token)


async def validate_age(value: Any):
    try:
        if int(value) < 18:
            return "You must be over 18 to register"
    except Exception:
        pass

    return None


form_fields = [
    InputFormField('name'),
    InputFormField('age', validate=validate_age),
    InputFormField('country', optional=True)
]


class CustomAuth0Provider(Provider):
    def __init__(self, client_id: str, client_secret: str, domain: str):
        super().__init__('auth0', False)
        self.domain = domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorisation_redirect_url = "https://" + self.domain + "/authorize"
        self.access_token_api_url = "https://" + self.domain + "/oauth/token"

    async def get_profile_info(self, auth_code_response: Dict[str, Any], user_context: Dict[str, Any]) -> UserInfo:
        # we do not query auth0 here cause it reaches their rate limit.
        return UserInfo("test-user-id-1", UserInfoEmail(
            "auth0email@example.com", True))

    def get_authorisation_redirect_api_info(self, user_context: Dict[str, Any]) -> AuthorisationRedirectAPI:
        params: Dict[str, Any] = {
            'scope': 'openid profile',
            'response_type': 'code',
            'client_id': self.client_id,
        }
        return AuthorisationRedirectAPI(
            self.authorisation_redirect_url, params)

    def get_access_token_api_info(
            self, redirect_uri: str, auth_code_from_request: str, user_context: Dict[str, Any]) -> AccessTokenAPI:
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': auth_code_from_request,
            'redirect_uri': redirect_uri
        }
        return AccessTokenAPI(self.access_token_api_url, params)

    def get_redirect_uri(self, user_context: Dict[str, Any]) -> Union[None, str]:
        return None

    def get_client_id(self, user_context: Dict[str, Any]) -> str:
        return self.client_id


providers_list: List[Provider] = [
    Google(
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),  # type: ignore
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')  # type: ignore
    ), Facebook(
        client_id=os.environ.get('FACEBOOK_CLIENT_ID'),  # type: ignore
        client_secret=os.environ.get('FACEBOOK_CLIENT_SECRET')  # type: ignore
    ), Github(
        client_id=os.environ.get('GITHUB_CLIENT_ID'),  # type: ignore
        client_secret=os.environ.get('GITHUB_CLIENT_SECRET')  # type: ignore
    ), CustomAuth0Provider(
        client_id=os.environ.get('AUTH0_CLIENT_ID'),  # type: ignore
        domain=os.environ.get('AUTH0_DOMAIN', 'auth0.supertokens.com'),  # type: ignore
        client_secret=os.environ.get('AUTH0_CLIENT_SECRET')  # type: ignore
    )
]


def custom_init(contact_method: Union[None, Literal['PHONE', 'EMAIL', 'EMAIL_OR_PHONE']] = None,
                flow_type: Union[None, Literal['USER_INPUT_CODE', 'MAGIC_LINK', 'USER_INPUT_CODE_AND_MAGIC_LINK']] = None):
    PasswordlessRecipe.reset()
    ThirdPartyPasswordlessRecipe.reset()
    JWTRecipe.reset()
    EmailVerificationRecipe.reset()
    SessionRecipe.reset()
    ThirdPartyRecipe.reset()
    EmailPasswordRecipe.reset()
    ThirdPartyEmailPasswordRecipe.reset()
    Supertokens.reset()

    if contact_method is not None and flow_type is not None:
        if contact_method == 'PHONE':
            passwordless_init = passwordless.init(
                contact_config=ContactPhoneOnlyConfig(
                    create_and_send_custom_text_message=save_code_text
                ),
                flow_type=flow_type
            )
            thirdpartypasswordless_init = thirdpartypasswordless.init(
                contact_config=ContactPhoneOnlyConfig(
                    create_and_send_custom_text_message=save_code_text
                ),
                flow_type=flow_type,
                providers=providers_list
            )
        elif contact_method == 'EMAIL':
            passwordless_init = passwordless.init(
                contact_config=ContactEmailOnlyConfig(
                    create_and_send_custom_email=save_code_email
                ),
                flow_type=flow_type
            )
            thirdpartypasswordless_init = thirdpartypasswordless.init(
                contact_config=ContactEmailOnlyConfig(
                    create_and_send_custom_email=save_code_email
                ),
                flow_type=flow_type,
                providers=providers_list
            )
        else:
            passwordless_init = passwordless.init(
                contact_config=ContactEmailOrPhoneConfig(
                    create_and_send_custom_email=save_code_email,
                    create_and_send_custom_text_message=save_code_text
                ),
                flow_type=flow_type
            )
            thirdpartypasswordless_init = thirdpartypasswordless.init(
                contact_config=ContactEmailOrPhoneConfig(
                    create_and_send_custom_email=save_code_email,
                    create_and_send_custom_text_message=save_code_text
                ),
                flow_type=flow_type,
                providers=providers_list
            )
    else:
        passwordless_init = passwordless.init(
            contact_config=ContactPhoneOnlyConfig(
                create_and_send_custom_text_message=save_code_text
            ),
            flow_type='USER_INPUT_CODE_AND_MAGIC_LINK'
        )
        thirdpartypasswordless_init = thirdpartypasswordless.init(
            contact_config=ContactPhoneOnlyConfig(create_and_send_custom_text_message=save_code_text),
            flow_type='USER_INPUT_CODE_AND_MAGIC_LINK',
            providers=providers_list
        )

    recipe_list = [
        session.init(),
        emailpassword.init(
            sign_up_feature=emailpassword.InputSignUpFeature(form_fields),
            reset_password_using_token_feature=emailpassword.InputResetPasswordUsingTokenFeature(
                create_and_send_custom_email=create_and_send_custom_email
            ),
            email_verification_feature=emailpassword.InputEmailVerificationConfig(
                create_and_send_custom_email=create_and_send_custom_email
            )
        ),
        thirdparty.init(
            sign_in_and_up_feature=thirdparty.SignInAndUpFeature(providers_list)
        ),
        thirdpartyemailpassword.init(
            sign_up_feature=thirdpartyemailpassword.InputSignUpFeature(
                form_fields),
            providers=providers_list
        ),
        passwordless_init,
        thirdpartypasswordless_init
    ]
    init(
        supertokens_config=SupertokensConfig('http://localhost:9000'),
        app_info=InputAppInfo(
            app_name="SuperTokens Demo",
            api_domain="0.0.0.0:" + get_api_port(),
            website_domain=get_website_domain()
        ),
        framework='django',
        mode=os.environ.get('APP_MODE', 'asgi'),  # type: ignore
        recipe_list=recipe_list,
        telemetry=False
    )
