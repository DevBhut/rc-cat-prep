import { Resend } from 'resend';

const resend = new Resend(process.env.RESEND_API_KEY);

export async function sendOTP(email: string, code: string) {
  await resend.emails.send({
    from: process.env.RESEND_FROM_EMAIL!,
    to: email,
    subject: 'Your RC Prep Login Code',
    html: `<p>Your verification code is: <strong>${code}</strong></p><p>Valid for 10 minutes.</p>`,
  });
}
