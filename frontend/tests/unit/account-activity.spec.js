import {expect} from 'chai';
import axios from 'axios';
import Account from '@/components/auth/Account.vue';

function account() {
    const context = Object.assign(Account.data(), {profile: {id: 17, role: 'curator', mfa_required: false}});
    context.resetActivity = () => Account.methods.resetActivity.call(context);
    return context;
}

describe('Account assignments and security history', () => {
    let originalGet;
    beforeEach(() => { originalGet = axios.get; });
    afterEach(() => { axios.get = originalGet; });

    it('loads the signed-in account assignments and independently paginates security events', async () => {
        const calls = [];
        const study = {sid: 'PKDB00001', name: 'Assigned private study'};
        const event = {id: 80, action: 'key.revoke', target: 'key:7'};
        axios.get = async (url, options) => {
            calls.push({url, options});
            return {data: url.endsWith('/studies') ? [study] : [event]};
        };
        const context = account();
        await Account.methods.loadActivity.call(context, 'studies', 0);
        await Account.methods.loadActivity.call(context, 'events', 50);
        expect(calls[0].url).to.match(/\/api\/v1\/me\/studies$/);
        expect(calls[1].url).to.match(/\/api\/v1\/me\/security-events$/);
        expect(calls[1].options.params).to.deep.equal({offset: 50, limit: 50});
        expect(context.studies).to.deep.equal([study]);
        expect(context.events).to.deep.equal([event]);
        expect(context.studiesOffset).to.equal(0);
        expect(context.eventsOffset).to.equal(50);
    });

    it('retains the current page when the next page fails so retry does not skip results', async () => {
        axios.get = async () => { throw new Error('Offline'); };
        const context = account();
        context.studies = [{sid: 'PKDB00001'}];
        await Account.methods.loadActivity.call(context, 'studies', 50);
        expect(context.studiesOffset).to.equal(0);
        expect(context.studies).to.deep.equal([{sid: 'PKDB00001'}]);
        expect(context.studiesError).to.not.equal('');
        expect(context.studiesLoading).to.equal(false);
        expect(context.eventsError).to.equal('');
    });

    it('discards private results arriving after logout or an account change', async () => {
        let finish;
        axios.get = () => new Promise(resolve => { finish = resolve; });
        const context = account();
        const loading = Account.methods.loadActivity.call(context, 'studies', 50);
        context.profile = null;
        context.resetActivity();
        finish({data: [{sid: 'PRIVATE'}]});
        await loading;
        expect(context.studies).to.deep.equal([]);
        expect(context.events).to.deep.equal([]);
        expect(context.studiesOffset).to.equal(0);
        expect(context.studiesLoading).to.equal(false);
    });

    it('does not request account data before administrator MFA completion', async () => {
        axios.get = async () => { throw new Error('Unexpected request'); };
        const context = account();
        context.profile.mfa_required = true;
        await Account.methods.loadActivity.call(context, 'studies', 0);
        expect(context.studiesError).to.equal('');
        expect(context.studiesLoading).to.equal(false);
    });
});

describe('Public provider reference privacy', () => {
    it('saves visibility choices without replacing authenticated sign-in references', async () => {
        const originalPatch = axios.patch;
        const calls = [];
        axios.patch = async (url, data) => { calls.push({url, data}); };
        const context = {
            form: {github: 'scientist', orcid: '0000-0002-1825-0097', github_visible: false, orcid_visible: false},
            profile: {github_provenance: 'authenticated', orcid_provenance: 'authenticated'},
            run: action => action(),
            $store: {dispatch: async () => {}}
        };
        try {
            await Account.methods.saveProfile.call(context);
            expect(calls[0].data).to.deep.equal({github_visible: false, orcid_visible: false});
        } finally { axios.patch = originalPatch; }
    });
});
