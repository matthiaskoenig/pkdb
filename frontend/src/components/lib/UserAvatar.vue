<template>
  <v-avatar left :size="32" color="grey lighten-3" :title="fullname">
    <img :src="src" :alt="fullname" style="object-fit:cover"/>
  </v-avatar>
</template>
<script>
import {apiBase} from '../../http';
export default {
  name: 'UserAvatar',
  props: {search: {type: String, default: ''}, user: Object, username: String},
  computed: {
    profile() {
      const own = this.$store.state.profile;
      return this.user || (own && own.username === this.username ? own : null);
    },
    fullname() { return this.profile ? (this.profile.display_name || [this.profile.first_name, this.profile.last_name].filter(Boolean).join(' ') || this.profile.username) : (this.username || 'Contributor'); },
    src() { return apiBase + (this.profile && this.profile.avatar_url || '/api/v1/avatars/default.svg'); }
  }
};
</script>
