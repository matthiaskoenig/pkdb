import {expect} from 'chai';
import axios from 'axios';
import AdminSettings from '@/components/auth/AdminSettings.vue';
import ProviderOnboarding from '@/components/auth/ProviderOnboarding.vue';

describe('Existing account invitations', () => {
    let originalPost;
    beforeEach(() => { originalPost = axios.post; });
    afterEach(() => { axios.post = originalPost; });
    it('sends an invitation only to the reviewed account contact', async () => {
        const calls = [];
        axios.post = async (url, body) => { calls.push({url, body}); return {data: {delivery: 'sent'}}; };
        const context = {busy: false, notice: '', invitationError: '', invitationUser: {id: 42, invitation_email_id: 73, email: 'reviewed@example.org'}};
        const user = context.invitationUser;
        await AdminSettings.methods.sendInvitation.call(context);
        expect(user.status).to.equal('pending');
        expect(calls).to.deep.equal([{url: '/api/v1/admin/users/42/invitations', body: {email_id: 73}}]);
        expect(context.invitationUser).to.equal(null);
        expect(context.notice).to.include('reviewed@example.org');
        expect(context.busy).to.equal(false);
    });
    it('keeps the invitation dialog open for retry after mail failure', async () => {
        axios.post = async () => { throw {response: {data: {detail: 'Invitation delivery unavailable; retry'}}}; };
        const context = {busy: false, notice: '', invitationError: '', invitationUser: {id: 42, invitation_email_id: 73}};
        await AdminSettings.methods.sendInvitation.call(context);
        expect(context.invitationUser.id).to.equal(42);
        expect(context.invitationError).to.include('retry');
        expect(context.notice).to.equal('');
    });
    it('claims an invited identity without sending a new username or password', async () => {
        const calls = [];
        axios.post = async (url, body) => { calls.push({url, body}); return {data: {status: 'authenticated'}}; };
        const context = {busy: false, error: '', token: ' one-use-invitation ', complete: false};
        await ProviderOnboarding.methods.claimInvitation.call(context);
        expect(calls).to.deep.equal([{url: '/api/v1/auth/onboarding/invitation', body: {token: 'one-use-invitation'}}]);
        expect(context.token).to.equal('');
        expect(context.complete).to.equal(true);
    });
    it('does not report a provider claim successful when ownership proof fails', async () => {
        axios.post = async () => { throw {response: {data: {detail: 'Invalid or expired invitation'}}}; };
        const context = {busy: false, error: '', token: 'expired', complete: false};
        await ProviderOnboarding.methods.claimInvitation.call(context);
        expect(context.complete).to.equal(false);
        expect(context.error).to.equal('Invalid or expired invitation');
        expect(context.busy).to.equal(false);
    });
});
