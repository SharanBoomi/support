import requests
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
import boto3
from botocore.exceptions import ClientError
import datetime

# --- AWS SES Email Function ---
def awssesmail(recipientemail, subject, msg, cc_address_override="USE_DEFAULT_CC_UNLESS_NONE"):
    """
    Sends an email using AWS SES.
    If cc_address_override is None, no CC is sent.
    If cc_address_override is "USE_DEFAULT_CC_UNLESS_NONE" (default), it uses DEFAULT_CCADDRESS.
    Otherwise, it uses the provided cc_address_override.
    """
    # SENDER = "Big Support <donotreply@yourbigsupportdomain.com>" # IDEAL: Use a Big Support branded sender
    SENDER = "BIGFIX <donotreply@bignetwork.in>" # CURRENT: Using this as per previous context, MUST BE VERIFIED
    DEFAULT_CCADDRESS = "sales@bignetwork.in"    # Default CC for internal notifications if not overridden
    AWS_REGION = "eu-west-1"
    CHARSET = "UTF-8"

    client = boto3.client(
        'ses',
        region_name=AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

    destination = {'ToAddresses': [recipientemail]}
    actual_cc = None
    if cc_address_override == "USE_DEFAULT_CC_UNLESS_NONE":
        if DEFAULT_CCADDRESS:
            actual_cc = DEFAULT_CCADDRESS
    elif cc_address_override is not None:
        actual_cc = cc_address_override

    if actual_cc:
        destination['CcAddresses'] = [actual_cc]

    try:
        response = client.send_email(
            Destination=destination,
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': msg
                    }
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': subject
                }
            },
            Source=SENDER
        )
        print(f"Email sent to {recipientemail} (CC: {actual_cc if actual_cc else 'None'})! Message ID: {response['MessageId']}")
        return response
    except ClientError as e:
        print(f"Exception in awssesmail for recipient {recipientemail}: {e.response['Error']['Message']}")
        raise

# --- Main Index View (Handles Contact Form) ---
def index(request):
    if request.method == 'POST':
        print(f"POST data: {request.POST}")

        name = request.POST.get('name')
        email = request.POST.get('email') # Client's email
        phone = request.POST.get('phone', '') # Optional, but good to capture if provided
        subject_form = request.POST.get('subject') # Subject from the form
        message_content = request.POST.get('message')

        # Optional fields from previous form, not used in email body anymore
        # location = request.POST.get('location', '')
        # consultation_type = request.POST.get('consultation', '')

        # Updated server-side validation for core required fields
        if not all([name, email, subject_form, message_content]): # Phone is optional here
            messages.error(request, "Please fill out all required fields (Name, Email, Subject, Message).")
            return redirect(reverse('index') + '#contact')

        hcaptcha_token = request.POST.get('h-captcha-response')
        if not hcaptcha_token:
            messages.error(request, "Please complete the captcha.")
            return redirect(reverse('index') + '#contact')

        verification_url = "https://hcaptcha.com/siteverify"
        data = {
            'secret': settings.HCAPTCHA_SECRET_KEY,
            'response': hcaptcha_token
        }
        try:
            hcaptcha_response = requests.post(verification_url, data=data)
            hcaptcha_response.raise_for_status()
            result = hcaptcha_response.json()
        except requests.RequestException as e:
            print(f"Exception in hCaptcha verification: {str(e)}")
            messages.error(request, "Captcha verification failed due to a network error.")
            return redirect(reverse('index') + '#contact')

        if result.get('success'):
            current_year = datetime.date.today().year
            phone_html = f'<tr><td style="width:40%;font-size:14px;line-height:22px;padding:5px 0;">Contact Number:</td><td style="width:60%;font-size:14px;line-height:22px;font-weight:600;color:#000;">{phone}</td></tr>' if phone else ""

            # Internal team email (msg_to_team) - BRANDING CHANGED TO BIG SUPPORT
            msg_to_team = f"""<html>
                <head><meta charset="utf-8"></head>
                <body>
                <div style="padding:32px 2px 60px;background:#f3f5f7">
                    <table cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;min-width:600px;margin:0 auto;background:#f3f5f7;color:#14253f;font-family:Arial,Helvetica,sans-serif;">
                        <thead><tr style="text-align:center;">
                            <td><a href="https://support.bigfix.in/" target="_blank"> 
                                <img src="https://your-s3-bucket.s3.amazonaws.com/big-support-logo.png" alt="Big Support" title="Big Support" style="width:200px;height:auto;"></a> 
                        </tr></thead>
                        <tbody>
                            <tr><td>
                                <table style="width:100%;min-width:600px;padding:24px 40px 24px 20px;margin:32px auto;background:#fff;border-radius:6px">
                                    <tbody><tr><td>
                                        <table style="width:100%">
                                            <tbody>
                                                <tr><td style="padding:24px 0">Hi Team,</td></tr>
                                                <tr><td>We received a new contact inquiry via the Big Support website.</td></tr>
                                                <tr><td style="padding:18px 0">
                                                    <table style="width:100%;padding:8px 12px;background:#ffffff;">
                                                        <thead><tr style="text-align:left;"><th colspan="2" style="font-size:18px;line-height:24px;font-weight:500;color:#70829a;padding-bottom:10px;">Inquiry Details:</th></tr></thead>
                                                        <tbody>
                                                            <tr><td style="width:40%;font-size:14px;line-height:22px;padding:5px 0;">Name:</td><td style="width:60%;font-size:14px;line-height:22px;font-weight:600;color:#000;">{name}</td></tr>
                                                            <tr><td style="width:40%;font-size:14px;line-height:22px;padding:5px 0;">Email:</td><td style="width:60%;font-size:14px;line-height:22px;font-weight:600;color:#000;">{email}</td></tr>
                                                            {phone_html}
                                                            <tr><td style="width:40%;font-size:14px;line-height:22px;padding:5px 0;">Subject:</td><td style="width:60%;font-size:14px;line-height:22px;font-weight:600;color:#000;">{subject_form}</td></tr>
                                                            <tr><td style="width:40%;font-size:14px;line-height:22px;padding:5px 0;vertical-align:top;">Message:</td><td style="width:60%;font-size:14px;line-height:22px;font-weight:600;color:#000;">{message_content.replace(chr(10), '<br>')}</td></tr>
                                                        </tbody>
                                                    </table>
                                                </td></tr>
                                            </tbody>
                                        </table>
                                        <table>
                                            <tbody><tr>
                                                <td><p style="margin-top:24px;font-size:11px;line-height:16px;color:#70829a">© {current_year} Big Support. All rights reserved</p></td>
                                            </tr></tbody>
                                        </table>
                                    </td></tr></tbody>
                                </table>
                            </td></tr>
                        </tbody>
                    </table>
                </div>
                </body>
                </html>
            """

            # Client confirmation email (msg_to_client) - BRANDING CHANGED TO BIG SUPPORT
            msg_to_client = f"""<html>
                <head><meta charset="utf-8"></head>
                <body>
                <div style="padding:32px 2px 60px;background:#f3f5f7">
                    <table cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;min-width:600px;margin:0 auto;background:#f3f5f7;color:#14253f;font-family:Arial,Helvetica,sans-serif;">
                        <thead><tr style="text-align:center;">
                            <td><a href="https://support.bigfix.in/" target="_blank">
                                <img src="https://your-s3-bucket.s3.amazonaws.com/big-support-logo.png" alt="Big Support" title="Big Support" style="width:200px;height:auto;"></a> 
                        <tbody>
                            <tr><td>
                                <table style="width:100%;min-width:600px;padding:24px 40px 24px 20px;margin:32px auto;background:#fff;border-radius:6px">
                                    <tbody><tr><td>
                                        <table style="width:100%">
                                           <tbody>
                                                <tr><td style="padding:24px 0">Hi {{ name }},</td></tr>
                                                <tr><td>Thank you for contacting Big Support! We have received your inquiry regarding: "{{ subject_form }}".</td></tr>
                                                <tr><td style="padding:24px 0;">Our team will review your message and get back to you shortly.</td></tr>
                                                <tr style="text-align:center;">
                                                    <td>
                                                        <a href="https://www.yourbigsupportdomain.com/" target="_blank">
                                                            <img src="https://your-s3-bucket.s3.amazonaws.com/big-support-contact-image.png"
                                                                alt="Contact Big Support"
                                                                title="Big Support"
                                                                style="width:100%;max-width:400px;height:auto;">
                                                        </a>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                        <table>
                                            <tbody><tr>
                                                <td style="padding:24px 0;">Best regards,<br/><br/>The Big Support Team</td>
                                            </tr></tbody>
                                        </table>
                                    </td></tr></tbody>
                                </table>
                                <table>
                                    <tbody><tr>
                                        <td><p style="margin-top:24px;font-size:11px;line-height:16px;color:#70829a">© {current_year} Big Support. All rights reserved</p></td>
                                    </tr></tbody>
                                </table>
                            </td></tr>
                        </tbody>
                    </table>
                </div>
                </body>
                </html>
            """

            # --- Send Emails ---
            team_notification_recipient = "sales@bignetwork.in"
            internal_team_cc = None # Or None, or another address. This is the default from awssesmail now.

            email_sent_to_client = False
            email_sent_to_team = False

            try:
                awssesmail(email, f"Your Inquiry to Big Support - {subject_form}", msg_to_client, cc_address_override=None)
                email_sent_to_client = True
            except ClientError:
                messages.error(request, "Failed to send you a confirmation email. Our team will still review your inquiry.")

            try:
                awssesmail(team_notification_recipient, f"New Big Support Website Inquiry: {subject_form} from {name}", msg_to_team, cc_address_override=internal_team_cc)
                email_sent_to_team = True
            except ClientError:
                messages.error(request, "A critical error occurred while notifying our team. Please try contacting us through other means if this issue persists.")

            if email_sent_to_client and email_sent_to_team:
                messages.success(request, "Your message has been sent, and a confirmation has been emailed to you. Thank you!")
            elif email_sent_to_team:
                 messages.warning(request, "Your message has been sent to our team. However, we couldn't send you a confirmation email.")
            elif email_sent_to_client:
                 messages.warning(request, "Your confirmation email has been sent, but there was an issue fully processing your request for our team. We will investigate.")

            return redirect(reverse('index') + '#contact')
        else:
            error_codes = result.get('error-codes', [])
            print(f"hCaptcha verification failed. Error codes: {error_codes}")
            messages.error(request, f"Captcha verification failed. Please try again. ({', '.join(error_codes)})")
            return redirect(reverse('index') + '#contact')

    return render(request, 'bigsupport/index.html')




