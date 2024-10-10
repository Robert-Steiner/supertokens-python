from flask import Flask, request, jsonify
from supertokens_python.recipe.thirdparty.types import ThirdPartyInfo
from supertokens_python.types import AccountInfo
from supertokens_python.syncio import (
    get_user,
    delete_user,
    list_users_by_account_info,
    get_users_newest_first,
    get_users_oldest_first,
)


def add_supertokens_routes(app: Flask):
    @app.route("/test/supertokens/getuser", methods=["POST"])  # type: ignore
    def get_user_api():  # type: ignore
        assert request.json is not None
        response = get_user(request.json["userId"], request.json.get("userContext"))
        return jsonify(None if response is None else response.to_json())

    @app.route("/test/supertokens/deleteuser", methods=["POST"])  # type: ignore
    def delete_user_api():  # type: ignore
        assert request.json is not None
        delete_user(
            request.json["userId"],
            request.json["removeAllLinkedAccounts"],
            request.json.get("userContext"),
        )
        return jsonify({"status": "OK"})

    @app.route("/test/supertokens/listusersbyaccountinfo", methods=["POST"])  # type: ignore
    def list_users_by_account_info_api():  # type: ignore
        assert request.json is not None
        response = list_users_by_account_info(
            request.json["tenantId"],
            AccountInfo(
                email=request.json["accountInfo"].get("email", None),
                phone_number=request.json["accountInfo"].get("phoneNumber", None),
                third_party=(
                    None
                    if "thirdParty" not in request.json["accountInfo"]
                    else ThirdPartyInfo(
                        third_party_id=request.json["accountInfo"]["thirdParty"][
                            "thirdPartyId"
                        ],
                        third_party_user_id=request.json["accountInfo"]["thirdParty"][
                            "id"
                        ],
                    )
                ),
            ),
            request.json["doUnionOfAccountInfo"],
            request.json.get("userContext"),
        )

        return jsonify([r.to_json() for r in response])

    @app.route("/test/supertokens/getusersnewestfirst", methods=["POST"])  # type: ignore
    def get_users_newest_first_api():  # type: ignore
        assert request.json is not None
        response = get_users_newest_first(
            include_recipe_ids=request.json["includeRecipeIds"],
            limit=request.json["limit"],
            pagination_token=request.json["paginationToken"],
            tenant_id=request.json["tenantId"],
            user_context=request.json.get("userContext"),
        )
        return jsonify(
            {
                "nextPaginationToken": response.next_pagination_token,
                "users": [r.to_json() for r in response.users],
            }
        )

    @app.route("/test/supertokens/getusersoldestfirst", methods=["POST"])  # type: ignore
    def get_users_oldest_first_api():  # type: ignore
        assert request.json is not None
        response = get_users_oldest_first(
            include_recipe_ids=request.json["includeRecipeIds"],
            limit=request.json["limit"],
            pagination_token=request.json["paginationToken"],
            tenant_id=request.json["tenantId"],
            user_context=request.json.get("userContext"),
        )
        return jsonify(
            {
                "nextPaginationToken": response.next_pagination_token,
                "users": [r.to_json() for r in response.users],
            }
        )
