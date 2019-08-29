from django.conf import settings
from urllib.parse import urlencode, parse_qs
import json
import requests

class OAuthWB:
    def __init__(self, client_id, redirect_uri,client_secret,state):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.state = state
        self.client_key=client_secret
    def get_weibo_url(self):
        data_dict = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': self.state
        }
        weibo_url = 'https://api.weibo.com/oauth2/authorize?' + urlencode(data_dict)

        return weibo_url

    def get_access_token(self, code):  # 获取用户token和uid
        url = "https://api.weibo.com/oauth2/access_token"

        querystring = {
            "client_id": self.client_id,
            "client_secret": self.client_key,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            'state': self.state
        }

        response = requests.request("POST", url, params=querystring)

        return json.loads(response.text)

    def get_user_info(self, access_token_data):
        url = "https://api.weibo.com/2/users/show.json"

        querystring = {
            "uid": access_token_data['uid'],
            "access_token": access_token_data['access_token']
        }

        response = requests.request("GET", url, params=querystring)

        return json.loads(response.text)