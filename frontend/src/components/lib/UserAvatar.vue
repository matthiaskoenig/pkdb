<template>
    <span id="user-avatar">
          <v-avatar :title="username" :size="32">
            <img :src="src">
          </v-avatar>
    </span>
</template>

<script>
    import {lookup_icon} from "@/icons"
    export default {
        name: "UserAvatar",
        props: {
            search: {type:String, default:""},
            user: {
                type: Object,
                required: true,
            },
            comment: String,

        },
        computed: {
            username() {
                return this.user.first_name + ' ' + this.user.last_name;
            },
            initials() {
                return this.user.first_name[0] + this.user.last_name[0];
            },
            src() {
                var img_dir = '/assets/images/avatars/';
                if (this.initials === 'MK'){
                    return img_dir + 'koenig_128.png';
                } else if (this.initials === 'JG'){
                    return img_dir + 'grzegorzewski_128.png';
                } else if (this.initials === 'KG'){
                    return img_dir + 'kgreen_128.png';
                } else if (this.initials === 'DE'){
                    return img_dir + 'dimitra_128.png';
                }
                return img_dir + 'anonymous_128.png';
            },
        }
    }
</script>

<style scoped>
</style>