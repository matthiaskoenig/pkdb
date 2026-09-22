<template><div v-if="providers.length" class="mt-5"><v-divider class="mb-4"/><v-btn v-for="provider in providers" :key="provider" outlined block class="mt-2" :href="url(provider)">Continue with {{ provider === 'github' ? 'GitHub' : 'ORCID' }}</v-btn></div></template>
<script>
import axios from 'axios';
import {apiBase} from '../../http';
export default {name: 'ProviderLogin', data: () => ({providers: []}), async created() { try { this.providers = (await axios.get(apiBase + '/api/v1/auth/providers')).data.providers; } catch (_) { this.providers = []; } }, methods: {url(provider) { return apiBase + '/api/v1/auth/' + provider + '/start'; }}};
</script>
