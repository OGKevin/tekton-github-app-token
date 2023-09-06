#!/usr/bin/env python3
import json
import os
import time

import requests
from jwcrypto import jwk, jwt

EXPIRE_MINUTES_AS_SECONDS = int(os.environ.get('GITHUBAPP_TOKEN_EXPIRATION_MINUTES', 10)) * 60
GITHUB_API_URL = os.environ.get('GITHUB_API_URL')


class GitHub():
    token = None

    def __init__(self, private_key, app_id=None, installation_id=None):
        if not isinstance(private_key, bytes):
            raise ValueError(f'"{private_key}" parameter must be byte-string')
        self._private_key = private_key
        self.app_id = app_id
        self.token = self._get_token(installation_id)

    def _load_private_key(self, pem_key_bytes):
        return jwk.JWK.from_pem(pem_key_bytes)

    def _app_token(self, expire_in=EXPIRE_MINUTES_AS_SECONDS):
        key = self._load_private_key(self._private_key)
        now = int(time.time())
        token = jwt.JWT(
            header={"alg": "RS256"},
            claims={
                "iat": now,
                "exp": now + expire_in,
                "iss": self.app_id
            },
            algs=["RS256"],
        )
        token.make_signed_token(key)
        return token.serialize()

    def _get_token(self, installation_id=None):
        app_token = self._app_token()
        if not installation_id:
            return app_token

        req = self._request(
            "POST",
            f"/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/vnd.github.machine-man-preview+json"
            })

        ret = req.json()
        if 'token' not in ret:
            raise Exception(f"Authentication errors: {ret}")

        return ret['token']

    def _request(self, method, url, headers={}, data={}):
        if self.token and 'Authorization' not in headers:
            headers.update({"Authorization": "Bearer " + self.token})
        if not url.startswith("http"):
            url = f"{GITHUB_API_URL}{url}"
        return requests.request(method,
                                url,
                                headers=headers,
                                data=json.dumps(data))

def main():
    with open(os.environ['GITHUBAPP_KEY_PATH'], 'rb') as key_file:
        key = key_file.read()

    if os.path.exists(os.environ['GITHUBAPP_APP_ID_PATH']):
        app_id = open(os.environ['GITHUBAPP_APP_ID_PATH']).read()
    elif os.environ.get('GITHUBAPP_APP_ID'):
        app_id = os.environ['GITHUBAPP_APP_ID']
    else:
        raise Exception("application id is not set")

    print(f"Getting user token for application_id: {app_id}")
    github_app = GitHub(
        key,
        app_id=app_id,
        installation_id=os.environ.get('GITHUBAPP_INSTALLATION_ID'))
    open(os.environ.get('GITHUBAPP_RESULT_PATH'), 'w').write(github_app.token)

if __name__ == '__main__':
    main()
