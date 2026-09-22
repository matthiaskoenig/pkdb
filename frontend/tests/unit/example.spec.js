import {expect} from 'chai';
import UserLogin from '@/components/auth/UserLogin.vue';
import MfaChallenge from '@/components/auth/MfaChallenge.vue';
import {errorMessage} from '@/http';

describe('Browser account authentication', () => {
    it('clears password after login and retains the MFA challenge', async () => {
        const calls = [];
        const context = {
            busy: false, error: '', username: 'mkoenig', password: 'temporary-test',
            user: {mfa_required: true},
            $store: {dispatch: async (action, payload) => { calls.push({action, payload}); }},
            $emit: event => calls.push({event})
        };
        await UserLogin.methods.login.call(context);
        expect(context.password).to.equal('');
        expect(context.busy).to.equal(false);
        expect(calls).to.have.length(1);
        expect(calls[0].action).to.equal('login');
    });
    it('does not pretend logout succeeded after a network failure', async () => {
        const context = {
            busy: false, error: '',
            $store: {dispatch: async () => { throw new Error('Offline'); }},
            $emit: () => { throw new Error('Must not close dialog'); }
        };
        await UserLogin.methods.logout.call(context);
        expect(context.error).to.include('could not be completed');
        expect(context.busy).to.equal(false);
    });
    it('clears MFA enrollment secrets and recovery codes on destruction', () => {
        const context = {enrollment: {secret: 'sensitive'}, recovery: ['one-time'], code: '123456'};
        MfaChallenge.beforeDestroy.call(context);
        expect(context.enrollment).to.equal(null);
        expect(context.recovery).to.deep.equal([]);
        expect(context.code).to.equal('');
    });
    it('shows validation messages without exposing full request details', () => {
        expect(errorMessage({response: {data: {detail: [{msg: 'Invalid ORCID checksum'}]}}})).to.equal('Invalid ORCID checksum');
    });
});
