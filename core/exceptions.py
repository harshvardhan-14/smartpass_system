"""
Custom exception handler for consistent API error responses.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Return a consistent JSON error envelope:
    {
        "success": false,
        "message": "<human readable>",
        "errors": { ... }   # only present when there are field errors
    }
    """
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {'success': False, 'message': 'An unexpected error occurred.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = response.data

    # Build a clean message from DRF error data
    if isinstance(data, dict):
        non_field = data.get('non_field_errors') or data.get('detail')
        if non_field:
            if isinstance(non_field, list):
                message = str(non_field[0])
            else:
                message = str(non_field)
        else:
            # Pull first field error as the headline message
            first_key = next(iter(data), None)
            first_val = data.get(first_key, '')
            if isinstance(first_val, list):
                message = f"{first_key}: {first_val[0]}"
            else:
                message = str(first_val)
    elif isinstance(data, list):
        message = str(data[0]) if data else 'Validation error.'
    else:
        message = str(data)

    response.data = {
        'success': False,
        'message': message,
    }

    # Include field-level errors when present (useful for form validation)
    if isinstance(data, dict) and 'detail' not in data and 'non_field_errors' not in data:
        response.data['errors'] = data

    return response
