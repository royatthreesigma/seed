"""
Send email using Resend service.
Resend is a third-party email service provider.
"""

import os
import resend


def send_email(recepient_email: str, from_email: str, subject: str, body: str) -> bool:
    resend.api_key = os.getenv("RESEND_API_KEY")
    """SendParams is the class that wraps the parameters for the send method.

    Attributes:
        from (str): The email address to send the email from.
        to (Union[str, List[str]]): List of email addresses to send the email to.
        subject (str): The subject of the email.
        bcc (NotRequired[Union[List[str], str]]): Bcc
        cc (NotRequired[Union[List[str], str]]): Cc
        reply_to (NotRequired[Union[List[str], str]]): Reply to
        html (NotRequired[str]): The HTML content of the email.
        text (NotRequired[str]): The text content of the email.
        headers (NotRequired[Dict[str, str]]): Custom headers to be added to the email.
        attachments (NotRequired[List[Union[Attachment, RemoteAttachment]]]): List of attachments to be added to the email.
        tags (NotRequired[List[Tag]]): List of tags to be added to the email.
    """
    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": recepient_email,
        "subject": subject,
        "html": f"""
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
            <tr>
                <td align="center" style="padding: 40px 16px;">
                <!-- Container -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width:600px; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
                    <!-- Header -->
                    <tr>
                    <td style="padding:24px;">
                        <h1 style="margin:0; font-size:18px; font-weight:500;">
                        {subject}
                        </h1>
                    </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                    <td style="padding:32px 24px; color:#1e293b; font-size:16px; line-height:1.5;">
                        <p style="margin:0 0 16px;">Hi there,</p>
                        {body}
                    </td>
                    </tr>
                </table>
                </td>
            </tr>
            </table>
        """,
    }
    try:
        resp = resend.Emails.send(params)
        return True
    except Exception as e:
        return False
