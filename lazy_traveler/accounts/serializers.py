from rest_framework import serializers
from django.contrib.auth import get_user_model


User = get_user_model()


# 회원가입 시리얼라이저
class SignupSerializer(serializers.ModelSerializer):
    # 회원가입 시 필요한 비밀번호와 비밀번호 확인 필드 추가
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['id','username', 'password', 'password2', 'tags']  # 시리얼라이즈할 필드

    def validate_username(self, value):
        """아이디 중복 체크"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("이미 존재하는 아이디입니다.")
        return value

    def validate(self, data):
        """패스워드 일치 체크"""
        if data['password'] != data['password2']:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        return data
    
    def validate_tags(self, value):
        # tags는 쉼표로 구분된 문자열로 처리
        if isinstance(value, list):
            # 리스트가 오면 쉼표로 구분된 문자열로 변환
            return ",".join(value)
        return value

    def create(self, validated_data):
        validated_data.pop("password2")  # password2 필드 제거
        tags = validated_data.pop('tags', "")
        user = User.objects.create_user(**validated_data)
        user.profile.tags = tags  # 유저 프로필에 태그 저장
        user.profile.save()
        return user