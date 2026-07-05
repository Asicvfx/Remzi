from django.contrib.auth import get_user_model


User = get_user_model()


class RegisterUserService:
    @staticmethod
    def execute(*, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password_confirm", None)
        user = User(**validated_data)
        user.email = user.email.lower()
        user.set_password(password)
        user.save()
        return user
