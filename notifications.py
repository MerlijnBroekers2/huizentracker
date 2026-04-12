import os
import resend


def send_new_listings_email(new_houses: list[dict], source: str):
    """Send an email summary of newly inserted listings.

    new_houses: list of house_data dicts (as inserted into Supabase)
    source: 'Funda' or 'Pararius'
    """
    if not new_houses:
        return

    resend.api_key = os.getenv("RESEND_API_KEY")
    email_to = [e.strip() for e in os.getenv("EMAIL_TO", "").split(",") if e.strip()]

    if not resend.api_key or not email_to:
        print("Resend credentials not set, skipping notification.")
        return

    subject = f"{len(new_houses)} new listing(s) found on {source}"

    rows = ""
    for h in new_houses:
        rows += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #eee;">
                <a href="{h['url']}" style="font-weight:600; color:#111;">{h['address']}</a><br>
                <span style="color:#555; font-size:13px;">{h.get('neighbourhood') or ''} · {h.get('city') or ''}</span>
            </td>
            <td style="padding:10px; border-bottom:1px solid #eee;">€ {h['price']} / mo</td>
            <td style="padding:10px; border-bottom:1px solid #eee;">{h.get('surface_m2') or '?'} m²</td>
            <td style="padding:10px; border-bottom:1px solid #eee;">{h.get('bedrooms') or '?'} bd</td>
            <td style="padding:10px; border-bottom:1px solid #eee;">
                <a href="{h['url']}" style="background:#111; color:#fff; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:13px;">View</a>
            </td>
        </tr>
        """

    html = f"""
    <html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; color:#111; max-width:700px; margin:auto; padding:24px;">
        <h2 style="margin-bottom:4px;">New listings on {source}</h2>
        <p style="color:#555; margin-top:0;">{len(new_houses)} new listing(s) found matching your criteria.</p>
        <table style="width:100%; border-collapse:collapse; margin-top:16px;">
            <thead>
                <tr style="background:#f3f4f6; text-align:left; font-size:13px; color:#555;">
                    <th style="padding:10px;">Address</th>
                    <th style="padding:10px;">Price</th>
                    <th style="padding:10px;">Size</th>
                    <th style="padding:10px;">Bedrooms</th>
                    <th style="padding:10px;"></th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p style="margin-top:24px; font-size:12px; color:#aaa;">Rental Tracker — automated notification</p>
    </body></html>
    """

    resend.Emails.send({
        "from": "Rental Tracker <onboarding@resend.dev>",
        "to": email_to,
        "subject": subject,
        "html": html,
    })

    print(f"Email sent to {email_to} with {len(new_houses)} new listing(s).")
