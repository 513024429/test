# from rest_framework import serializers
# from .models import *
# import re
# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model=User
#         fields='__all__'
#     def validate(self, attrs):
#         username=attrs.get('username')
#         password=attrs.get('password')
#         mobile=attrs.get('mobile')
#         if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
#             raise serializers.ValidationError('用户名格式不对')
#         if not re.match(r'^[0-9a-zA-Z]{8,22}$',password):
#             raise serializers.ValidationError('密码格式不对')
#         if not re.match('1[3-9]\d{9}$',mobile):
#             raise serializers.ValidationError('手机格式不对')