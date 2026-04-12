"""
Serializers for the accounts app.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import CustomUser, Resident, SecurityGuard, Admin, PasswordResetOTP


# ─── JWT ──────────────────────────────────────────────────────────────────────

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extend JWT payload with user type and full name."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_type'] = user.user_type
        token['username'] = user.username
        token['full_name'] = user.get_full_name()
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_type'] = self.user.user_type
        data['username'] = self.user.username
        data['full_name'] = self.user.get_full_name()
        data['user_id'] = self.user.id
        return data


# ─── Profiles ─────────────────────────────────────────────────────────────────

class ResidentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resident
        fields = ['id', 'flat_number', 'building_name', 'phone_number', 'profile_photo', 'created_at']
        read_only_fields = ['id', 'created_at']


class SecurityGuardProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityGuard
        fields = ['id', 'employee_id', 'phone_number', 'shift', 'profile_photo', 'created_at']
        read_only_fields = ['id', 'employee_id', 'created_at']


class AdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = ['id', 'admin_id', 'phone_number', 'department', 'created_at']
        read_only_fields = ['id', 'admin_id', 'created_at']


# ─── User ─────────────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    resident_profile = ResidentProfileSerializer(source='resident', read_only=True)
    guard_profile = SecurityGuardProfileSerializer(source='securityguard', read_only=True)
    admin_profile = AdminProfileSerializer(source='admin', read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'phone_number', 'is_active',
            'created_at', 'updated_at',
            'resident_profile', 'guard_profile', 'admin_profile',
        ]
        read_only_fields = ['id', 'username', 'user_type', 'created_at', 'updated_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number']


# ─── Registration ─────────────────────────────────────────────────────────────

class ResidentRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=10)
    flat_number = serializers.CharField(max_length=20)
    building_name = serializers.CharField(max_length=100, default='Building A')
    profile_photo = serializers.ImageField(required=False, allow_null=True)

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already taken.')
        return value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already registered.')
        return value

    def validate_phone_number(self, value):
        digits = ''.join(filter(str.isdigit, value))
        if len(digits) != 10:
            raise serializers.ValidationError('Phone number must be exactly 10 digits.')
        return digits

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        photo = validated_data.pop('profile_photo', None)
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            user_type='resident',
            phone_number=validated_data['phone_number'],
        )
        resident_data = {
            'user': user,
            'flat_number': validated_data['flat_number'],
            'building_name': validated_data.get('building_name', 'Building A'),
            'phone_number': validated_data['phone_number'],
        }
        if photo:
            resident_data['profile_photo'] = photo
        Resident.objects.create(**resident_data)
        return user


class SecurityGuardRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=15)
    shift = serializers.ChoiceField(choices=['morning', 'evening', 'night'], default='morning')
    profile_photo = serializers.ImageField(required=False, allow_null=True)

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already taken.')
        return value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already registered.')
        return value

    def validate_phone_number(self, value):
        digits = ''.join(filter(str.isdigit, value))
        if len(digits) < 10:
            raise serializers.ValidationError('Phone number must be at least 10 digits.')
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def _generate_employee_id(self):
        import random
        import string
        for _ in range(10):
            eid = 'EMP' + ''.join(random.choices(string.digits, k=6))
            if not SecurityGuard.objects.filter(employee_id=eid).exists():
                return eid
        raise serializers.ValidationError('Could not generate unique employee ID. Try again.')

    def create(self, validated_data):
        photo = validated_data.pop('profile_photo', None)
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            user_type='security',
            phone_number=validated_data['phone_number'],
        )
        guard_data = {
            'user': user,
            'employee_id': self._generate_employee_id(),
            'phone_number': validated_data['phone_number'],
            'shift': validated_data.get('shift', 'morning'),
        }
        if photo:
            guard_data['profile_photo'] = photo
        guard = SecurityGuard.objects.create(**guard_data)
        user._employee_id = guard.employee_id  # attach for response
        return user


# ─── Password Reset ────────────────────────────────────────────────────────────

class ForgotPasswordSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)

    def validate_mobile_number(self, value):
        digits = ''.join(filter(str.isdigit, value))
        if len(digits) < 10:
            raise serializers.ValidationError('Enter a valid mobile number.')
        return digits


class ResetPasswordSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs


# ─── Profile Update ───────────────────────────────────────────────────────────

class ResidentProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = Resident
        fields = ['first_name', 'last_name', 'email', 'flat_number', 'building_name', 'phone_number', 'profile_photo']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class SecurityGuardProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = SecurityGuard
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'shift', 'profile_photo']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
