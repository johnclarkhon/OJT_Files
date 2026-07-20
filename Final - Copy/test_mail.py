from mail import send_email

success = send_email(

    "CHECKLIST NOTIFICATION SYSTEM",

    """

This is a test email.

Congratulations!

Your notification system is working.

"""

)

print(success)