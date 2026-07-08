const nodemailer = require('nodemailer');

const mailer = nodemailer.createTransport({
    host: 'smtp.eu.sparkpostmail.com',
    port: 587,
    secure: false,
    auth: { user: 'SMTP_Injection', pass: 'd7849c32d13427e7a3d578e0cd6fbfc40878e3a1' },
    tls: { rejectUnauthorized: false }
});

module.exports = async function(context, req) {
    if (req.method !== 'POST') {
        context.res = { status: 405, body: 'Method not allowed' };
        return;
    }

    const { firstName, lastName, email, company, apSpend, pool } = req.body || {};

    if (!email || !firstName) {
        context.res = { status: 400, body: { error: 'Name and email are required.' } };
        return;
    }

    const html = `
<h2>New Recovery Estimator Lead</h2>
<table style="font-family:Arial;font-size:14px;border-collapse:collapse">
  <tr><td style="padding:6px 16px 6px 0;color:#555">Name</td><td><strong>${firstName} ${lastName || ''}</strong></td></tr>
  <tr><td style="padding:6px 16px 6px 0;color:#555">Email</td><td><strong>${email}</strong></td></tr>
  <tr><td style="padding:6px 16px 6px 0;color:#555">Company</td><td>${company || '—'}</td></tr>
  <tr><td style="padding:6px 16px 6px 0;color:#555">Est. Annual AP Spend</td><td>${apSpend || '—'}</td></tr>
  <tr><td style="padding:6px 16px 6px 0;color:#555">18-Month Auditable Pool</td><td>${pool || '—'}</td></tr>
</table>
<p style="margin-top:20px;font-size:12px;color:#999">Submitted via AP Recovery Estimator at apimpact.com</p>`;

    try {
        await mailer.sendMail({
            from: 'AP Impact Website <hello@apimpact.com>',
            to: 'hello@apimpact.com',
            replyTo: email,
            subject: `Recovery Estimator Lead: ${firstName} ${lastName || ''} — ${company || email}`,
            html
        });
        context.res = { status: 200, body: { success: true } };
    } catch (err) {
        context.log.error('Email send failed:', err.message);
        context.res = { status: 500, body: { error: 'Failed to send. Please try again.' } };
    }
};
