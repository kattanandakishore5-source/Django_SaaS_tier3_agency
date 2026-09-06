from datetime import timedelta

from django.utils import timezone
from django.db import transaction

import apps.core.utils as core_utils
from .models import CustomUser, PasswordReset, MagicLinkToken
from django.conf import settings


class AccountServiceError(Exception):
    pass


class UserAlreadyExistsError(AccountServiceError):
    pass


class InvalidCredentialsError(AccountServiceError):
    pass


class InvalidTokenError(AccountServiceError):
    pass


class TokenExpiredError(AccountServiceError):
    pass


def create_user_account(email, password, first_name='', last_name=''):
    if CustomUser.objects.filter(email=email).exists():
        raise UserAlreadyExistsError('Email already registered')

    user = CustomUser.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    # Dispatch email task only after DB transaction commits to avoid race conditions.
    # workspace_id=None here because account creation is user-centric (pre-workspace).
    # In Part 2 this can be wired to the user's default workspace.
    if getattr(settings, 'TESTING', False):
        # In test environments, execute dispatch immediately so unit tests can assert calls
        core_utils.send_email_async.delay(
            subject='Welcome to Django Starter!',
            message=f'Thank you for signing up, {first_name}!',
            recipient_list=[email],
            template='welcome',
            workspace_id=None,
        )
    else:
        transaction.on_commit(lambda: core_utils.send_email_async.delay(
            subject='Welcome to Django Starter!',
            message=f'Thank you for signing up, {first_name}!',
            recipient_list=[email],
            template='welcome',
            workspace_id=None,
        ))
    return user


def initiate_password_reset(email, base_url):
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return False

    PasswordReset.objects.filter(user=user).delete()
    token = PasswordReset.generate_token()
    PasswordReset.objects.create(
        user=user,
        token=token,
        expires_at=timezone.now() + timedelta(hours=24),
    )

    reset_url = f"{base_url}{token}/"
    if getattr(settings, 'TESTING', False):
        core_utils.send_email_async.delay(
            subject='Reset Your Password',
            message=f'Click here to reset: {reset_url}',
            recipient_list=[email],
            workspace_id=None,
        )
    else:
        transaction.on_commit(lambda: core_utils.send_email_async.delay(
            subject='Reset Your Password',
            message=f'Click here to reset: {reset_url}',
            recipient_list=[email],
            workspace_id=None,
        ))
    return True


def reset_password_with_token(token, new_password):
    try:
        reset = PasswordReset.objects.get(token=token)
    except PasswordReset.DoesNotExist:
        raise InvalidTokenError('Invalid or expired link')

    if not reset.is_valid():
        raise TokenExpiredError('Link has expired')

    reset.used = True
    reset.save()

    user = reset.user
    user.set_password(new_password)
    user.save()
    return user


def initiate_magic_link(email, base_url):
    """
    Generate single-use, time-limited magic link token and dispatch email asynchronously.
    Returns True regardless of user existence to prevent user enumeration attacks.
    """
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        # Uniform response to prevent email enumeration
        return True

    # Invalidate previous tokens
    MagicLinkToken.objects.filter(user=user).delete()

    token = MagicLinkToken.generate_token()
    expiry_minutes = getattr(settings, 'MAGIC_LINK_EXPIRY_MINUTES', 15)
    MagicLinkToken.objects.create(
        user=user,
        token=token,
        expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
    )

    magic_url = f"{base_url.rstrip('/')}/{token}/"

    if getattr(settings, 'TESTING', False):
        core_utils.send_email_async.delay(
            subject='Your Secure Magic Login Link',
            message=f'Click the link to log in: {magic_url}',
            recipient_list=[email],
            workspace_id=None,
        )
    else:
        transaction.on_commit(lambda: core_utils.send_email_async.delay(
            subject='Your Secure Magic Login Link',
            message=f'Click the link to log in: {magic_url}',
            recipient_list=[email],
            workspace_id=None,
        ))
    return True


def verify_magic_link_token(token):
    """
    Validate magic link token, ensure single-use, and return user.
    """
    try:
        magic_token = MagicLinkToken.objects.get(token=token)
    except MagicLinkToken.DoesNotExist:
        raise InvalidTokenError('Invalid or expired magic link')

    if magic_token.used:
        raise InvalidTokenError('Magic link has already been used')

    if timezone.now() >= magic_token.expires_at:
        raise TokenExpiredError('Magic link has expired')

    magic_token.used = True
    magic_token.save()
    return magic_token.user

